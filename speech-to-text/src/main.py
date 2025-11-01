"""
Flask API server for the speech-to-text component.

Provides RESTful API endpoints for audio transcription with real-time streaming.
"""

import os
import json
import time
import threading
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import logging

from utils import validate_session_id, get_utc_timestamp, AudioConfig, logger
from transcription_service import get_transcription_service, TranscriptionError
from audio_capture import AudioCapture
from audio_buffer import AudioBuffer
from session_manager import get_session_manager

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure CORS
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3005').split(',')
CORS(app, origins=cors_origins)

# Get service instances
transcription_service = get_transcription_service()
session_manager = get_session_manager()

# Configure logging
app.logger.setLevel(logging.INFO)

# Active recording sessions (session_id -> {capture, buffer, thread})
active_recordings = {}
recordings_lock = threading.Lock()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'speech-to-text',
        'timestamp': get_utc_timestamp()
    })


@app.route('/sessions/start', methods=['POST'])
def start_session():
    """
    Start a new transcription session.

    Request body (optional):
    {
        "session_id": "custom-session-id"  // optional
    }

    Returns:
        JSON with session details
    """
    try:
        data = request.get_json() or {}
        custom_session_id = data.get('session_id')

        # Create session
        session = session_manager.create_session(custom_session_id)

        # Initialize audio capture and buffer
        audio_buffer = AudioBuffer(
            chunk_duration=AudioConfig.CHUNK_DURATION,
            overlap_duration=AudioConfig.OVERLAP_DURATION,
            silence_threshold_seconds=AudioConfig.SILENCE_THRESHOLD
        )

        audio_capture = AudioCapture(
            sample_rate=AudioConfig.SAMPLE_RATE,
            channels=AudioConfig.CHANNELS,
            callback=lambda audio: audio_buffer.add_audio(audio)
        )

        # Start capturing
        audio_capture.start()

        # Store in active recordings
        with recordings_lock:
            active_recordings[session.session_id] = {
                'capture': audio_capture,
                'buffer': audio_buffer,
                'session': session,
                'is_streaming': False
            }

        app.logger.info(f"Started session: {session.session_id}")

        return jsonify({
            'session_id': session.session_id,
            'status': 'started',
            'started_at': session.started_at,
            'config': {
                'chunk_duration': AudioConfig.CHUNK_DURATION,
                'overlap_duration': AudioConfig.OVERLAP_DURATION,
                'sample_rate': AudioConfig.SAMPLE_RATE,
                'channels': AudioConfig.CHANNELS
            }
        }), 201

    except ValueError as e:
        app.logger.error(f"Error starting session: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        app.logger.error(f"Unexpected error starting session: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/sessions/<session_id>/stream', methods=['GET'])
def stream_transcription(session_id):
    """
    Stream transcript chunks for a session using Server-Sent Events (SSE).

    Args:
        session_id: Session identifier

    Returns:
        SSE stream of transcript chunks
    """
    # Validate session
    if not validate_session_id(session_id):
        return jsonify({'error': 'Invalid session ID'}), 400

    with recordings_lock:
        recording = active_recordings.get(session_id)

    if not recording:
        return jsonify({'error': 'Session not found or not active'}), 404

    # Mark as streaming
    with recordings_lock:
        recording['is_streaming'] = True

    app.logger.info(f"Starting stream for session: {session_id}")

    def generate():
        """Generator function for SSE stream."""
        audio_buffer = recording['buffer']
        session = recording['session']
        last_chunk_id = -1

        try:
            # Loop while session is active or paused (keep connection open)
            while session.status in ['active', 'paused']:
                # Only process audio when active
                if session.status == 'active':
                    # Check if buffer should emit
                    if audio_buffer.should_emit():
                        # Get audio chunk
                        audio_bytes = audio_buffer.get_chunk()

                        if audio_bytes:
                            # Re-check status before transcribing (prevent race condition)
                            if session.status != 'active':
                                app.logger.debug(f"Skipping transcription - session {session_id} no longer active")
                                continue

                            try:
                                # Transcribe
                                app.logger.debug(f"Transcribing chunk for session {session_id}")
                                text = transcription_service.transcribe_audio(audio_bytes)

                                if text and text.strip():
                                    # Add to session
                                    session_manager.add_transcript_chunk(session_id, text)

                                    # Get the latest chunk
                                    latest_chunk = session.get_latest_chunk()

                                    if latest_chunk and latest_chunk.chunk_id > last_chunk_id:
                                        # Emit SSE event
                                        chunk_data = {
                                            'chunk_id': latest_chunk.chunk_id,
                                            'text': latest_chunk.text,
                                            'timestamp': latest_chunk.timestamp,
                                            'session_id': session_id,
                                            'confidence': latest_chunk.confidence
                                        }

                                        yield f"data: {json.dumps(chunk_data)}\n\n"
                                        last_chunk_id = latest_chunk.chunk_id

                                        app.logger.info(
                                            f"Session {session_id}: Emitted chunk #{latest_chunk.chunk_id}"
                                        )

                            except TranscriptionError as e:
                                # Log error but continue streaming
                                app.logger.error(f"Transcription error: {str(e)}")
                                error_data = {
                                    'error': 'transcription_failed',
                                    'message': str(e),
                                    'timestamp': get_utc_timestamp()
                                }
                                yield f"data: {json.dumps(error_data)}\n\n"

                    # Small sleep to prevent busy-waiting
                    time.sleep(0.1)

                elif session.status == 'paused':
                    # When paused, just wait without processing
                    # Keep connection alive with longer sleep
                    time.sleep(0.5)

            # Session ended
            app.logger.info(f"Stream ended for session: {session_id}")

        except GeneratorExit:
            app.logger.info(f"Client disconnected from stream: {session_id}")
        except Exception as e:
            app.logger.error(f"Error in stream generator: {str(e)}", exc_info=True)

    return Response(generate(), mimetype='text/event-stream')


@app.route('/sessions/<session_id>/stop', methods=['POST'])
def stop_session(session_id):
    """
    Stop a transcription session.

    Args:
        session_id: Session identifier

    Returns:
        JSON with final session details
    """
    if not validate_session_id(session_id):
        return jsonify({'error': 'Invalid session ID'}), 400

    with recordings_lock:
        recording = active_recordings.get(session_id)

    if not recording:
        return jsonify({'error': 'Session not found'}), 404

    try:
        # Stop audio capture
        recording['capture'].stop()

        # Process any remaining audio in buffer
        audio_buffer = recording['buffer']
        remaining_audio = audio_buffer.get_chunk()

        if remaining_audio:
            try:
                text = transcription_service.transcribe_audio(remaining_audio)
                if text and text.strip():
                    session_manager.add_transcript_chunk(session_id, text)
            except TranscriptionError as e:
                app.logger.error(f"Error transcribing final chunk: {str(e)}")

        # Stop session
        session = session_manager.stop_session(session_id)

        # Remove from active recordings
        with recordings_lock:
            del active_recordings[session_id]

        app.logger.info(f"Stopped session: {session_id}")

        # Return final session data
        return jsonify({
            'session_id': session.session_id,
            'status': 'stopped',
            'started_at': session.started_at,
            'total_duration': session.total_duration,
            'chunk_count': session.chunk_count,
            'full_transcript': session.full_transcript,
            'chunks': session.get_chunks_dict()
        })

    except Exception as e:
        app.logger.error(f"Error stopping session: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/sessions/<session_id>/pause', methods=['POST'])
def pause_session(session_id):
    """
    Pause a transcription session - stops audio capture but keeps state.

    Args:
        session_id: Session identifier

    Returns:
        JSON with session status
    """
    if not validate_session_id(session_id):
        return jsonify({'error': 'Invalid session ID'}), 400

    with recordings_lock:
        recording = active_recordings.get(session_id)

    if not recording:
        return jsonify({'error': 'Session not found'}), 404

    try:
        # Stop audio capture
        recording['capture'].stop()
        app.logger.info(f"Stopped audio capture for session: {session_id}")

        # Clear audio buffer (discard any buffered audio)
        recording['buffer'].reset()
        app.logger.info(f"Cleared audio buffer for session: {session_id}")

        # Pause the session in session manager
        session = session_manager.pause_session(session_id)

        if not session:
            return jsonify({'error': 'Session not found'}), 404

        app.logger.info(f"Paused session: {session_id}")

        # Return session data
        return jsonify({
            'session_id': session.session_id,
            'status': 'paused',
            'paused_at': session.paused_at,
            'pause_count': session.pause_count,
            'chunk_count': session.chunk_count
        })

    except ValueError as e:
        app.logger.warning(f"Cannot pause session {session_id}: {str(e)}")
        return jsonify({'error': str(e)}), 400

    except Exception as e:
        app.logger.error(f"Error pausing session: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/sessions/<session_id>/resume', methods=['POST'])
def resume_session(session_id):
    """
    Resume a paused transcription session - continues from current state.

    Args:
        session_id: Session identifier

    Returns:
        JSON with session status
    """
    if not validate_session_id(session_id):
        return jsonify({'error': 'Invalid session ID'}), 400

    with recordings_lock:
        recording = active_recordings.get(session_id)

    if not recording:
        return jsonify({'error': 'Session not found'}), 404

    try:
        # Resume the session in session manager
        session = session_manager.resume_session(session_id)

        if not session:
            return jsonify({'error': 'Session not found'}), 404

        # Restart audio capture
        recording['capture'].start()
        app.logger.info(f"Restarted audio capture for session: {session_id}")

        app.logger.info(f"Resumed session: {session_id}")

        # Return session data
        return jsonify({
            'session_id': session.session_id,
            'status': 'active',
            'resumed_at': session.resumed_at,
            'pause_count': session.pause_count,
            'total_paused_duration': session.total_paused_duration,
            'chunk_count': session.chunk_count
        })

    except ValueError as e:
        app.logger.warning(f"Cannot resume session {session_id}: {str(e)}")
        return jsonify({'error': str(e)}), 400

    except Exception as e:
        app.logger.error(f"Error resuming session: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/sessions/<session_id>', methods=['GET'])
def get_session_info(session_id):
    """
    Get session information.

    Args:
        session_id: Session identifier

    Returns:
        JSON with session details
    """
    if not validate_session_id(session_id):
        return jsonify({'error': 'Invalid session ID'}), 400

    session = session_manager.get_session(session_id)

    if not session:
        return jsonify({'error': 'Session not found'}), 404

    return jsonify(session.to_dict())


@app.route('/sessions', methods=['GET'])
def list_sessions():
    """
    List all sessions.

    Returns:
        JSON with list of sessions
    """
    sessions = session_manager.get_all_sessions()
    return jsonify({
        'sessions': [s.to_dict() for s in sessions],
        'total': len(sessions)
    })


@app.route('/transcribe/upload', methods=['POST'])
def transcribe_file():
    """
    Transcribe an uploaded audio file.

    Useful for testing and non-real-time transcription.

    Request:
        multipart/form-data with 'audio' file

    Returns:
        JSON with transcribed text
    """
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    audio_file = request.files['audio']

    if audio_file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    try:
        # Read file
        audio_data = audio_file.read()

        app.logger.info(f"Transcribing uploaded file: {audio_file.filename} ({len(audio_data)} bytes)")

        # Transcribe
        text = transcription_service.transcribe_audio(
            audio_data,
            filename=audio_file.filename
        )

        return jsonify({
            'text': text,
            'filename': audio_file.filename,
            'size_bytes': len(audio_data),
            'timestamp': get_utc_timestamp()
        })

    except TranscriptionError as e:
        app.logger.error(f"Transcription error: {str(e)}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    """
    Get service statistics.

    Returns:
        JSON with statistics
    """
    transcription_stats = transcription_service.get_stats()
    session_stats = session_manager.get_stats()

    with recordings_lock:
        active_count = len(active_recordings)

    return jsonify({
        'transcription': transcription_stats,
        'sessions': session_stats,
        'active_recordings': active_count,
        'timestamp': get_utc_timestamp()
    })


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    app.logger.error(f"Internal error: {str(error)}", exc_info=True)
    return jsonify({'error': 'Internal server error'}), 500


def main():
    """Run the Flask application."""
    port = int(os.getenv('PORT', 8005))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    app.logger.info("=" * 60)
    app.logger.info("Speech-to-Text API Server")
    app.logger.info("=" * 60)
    app.logger.info(f"Port: {port}")
    app.logger.info(f"Debug: {debug}")
    app.logger.info(f"CORS Origins: {cors_origins}")
    app.logger.info(f"Chunk Duration: {AudioConfig.CHUNK_DURATION}s")
    app.logger.info(f"Overlap Duration: {AudioConfig.OVERLAP_DURATION}s")
    app.logger.info("=" * 60)

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        threaded=True
    )


if __name__ == '__main__':
    main()
