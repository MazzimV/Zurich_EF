"""
Orchestrator Service - Main API Server

Bridges speech-to-text and graph-generation/segmentation services.
Provides unified API for frontend integration.
"""

import os
import sys
import logging
import json
import time
from datetime import datetime
from typing import Generator, Optional

import requests
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv

from session_orchestrator import SessionOrchestrator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Configuration
STT_SERVICE_URL = os.getenv('STT_SERVICE_URL', 'http://localhost:8005')
GRAPH_SERVICE_URL = os.getenv('GRAPH_SERVICE_URL', 'http://localhost:8002')
PORT = int(os.getenv('PORT', 8003))
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
MAX_SESSIONS = int(os.getenv('MAX_SESSIONS', 10))
SAVE_DIRECTORY = os.getenv('SAVE_DIRECTORY', './sessions')

# Initialize orchestrator
orchestrator = SessionOrchestrator(max_sessions=MAX_SESSIONS, save_directory=SAVE_DIRECTORY)

# Service health status cache
_service_health_cache = {
    'stt': {'healthy': False, 'last_check': 0},
    'graph': {'healthy': False, 'last_check': 0}
}
HEALTH_CHECK_INTERVAL = 30  # seconds


def check_service_health(service_name: str, url: str) -> bool:
    """
    Check if a service is healthy.

    Args:
        service_name: 'stt' or 'graph'
        url: Service base URL

    Returns:
        bool: True if healthy
    """
    global _service_health_cache

    # Use cached result if recent
    cache = _service_health_cache[service_name]
    if time.time() - cache['last_check'] < HEALTH_CHECK_INTERVAL:
        return cache['healthy']

    # Check health
    try:
        response = requests.get(f"{url}/health", timeout=2)
        healthy = response.status_code == 200
    except Exception as e:
        logger.warning(f"{service_name} health check failed: {e}")
        healthy = False

    # Update cache
    cache['healthy'] = healthy
    cache['last_check'] = time.time()

    return healthy


@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint.

    Returns service status and dependency health.
    """
    stt_healthy = check_service_health('stt', STT_SERVICE_URL)
    graph_healthy = check_service_health('graph', GRAPH_SERVICE_URL)

    status = {
        'status': 'healthy' if (stt_healthy and graph_healthy) else 'degraded',
        'service': 'orchestrator',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'dependencies': {
            'speech_to_text': {
                'url': STT_SERVICE_URL,
                'healthy': stt_healthy
            },
            'graph_generation': {
                'url': GRAPH_SERVICE_URL,
                'healthy': graph_healthy
            }
        },
        'stats': orchestrator.get_stats()
    }

    status_code = 200 if (stt_healthy and graph_healthy) else 503

    return jsonify(status), status_code


@app.route('/sessions', methods=['GET'])
def list_sessions():
    """
    List all sessions.

    Returns summary of all sessions.
    """
    try:
        sessions = orchestrator.get_all_sessions()

        return jsonify({
            'sessions': list(sessions.values()),
            'count': len(sessions)
        }), 200

    except Exception as e:
        logger.error(f"Error listing sessions: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/sessions/start', methods=['POST'])
def start_session():
    """
    Start a new orchestrated session.

    Creates session, starts STT recording, initializes graph state.

    Request body (optional):
    {
        "session_id": "custom-session-id"  // Optional
    }

    Returns:
        201: Session created
        400: Invalid request
        500: Internal error
        503: STT service unavailable
    """
    try:
        data = request.json or {}
        custom_session_id = data.get('session_id')

        # Check STT service health
        if not check_service_health('stt', STT_SERVICE_URL):
            return jsonify({
                'error': 'Speech-to-text service is not available',
                'stt_url': STT_SERVICE_URL
            }), 503

        # Create orchestrator session
        session_info = orchestrator.create_session(session_id=custom_session_id)
        session_id = session_info['session_id']

        logger.info(f"Starting session: {session_id}")

        # Start STT session
        try:
            stt_response = requests.post(
                f"{STT_SERVICE_URL}/sessions/start",
                json={'session_id': session_id},
                headers={'Content-Type': 'application/json'},
                timeout=5
            )

            if stt_response.status_code not in [200, 201]:
                logger.error(f"STT session start failed: {stt_response.status_code} - {stt_response.text}")
                orchestrator.delete_session(session_id)
                return jsonify({
                    'error': 'Failed to start speech-to-text session',
                    'details': stt_response.text
                }), 500

            stt_data = stt_response.json()
            stt_session_id = stt_data.get('session_id', session_id)

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to STT service: {e}")
            orchestrator.delete_session(session_id)
            return jsonify({
                'error': 'Failed to connect to speech-to-text service',
                'details': str(e)
            }), 503

        # Mark orchestrator session as started
        orchestrator.start_session(session_id, stt_session_id=stt_session_id)

        logger.info(f"Session started successfully: {session_id}")

        return jsonify({
            'session_id': session_id,
            'stt_session_id': stt_session_id,
            'status': 'active',
            'started_at': session_info['created_at'],
            'endpoints': {
                'stream': f'/sessions/{session_id}/stream',
                'state': f'/sessions/{session_id}/state',
                'stop': f'/sessions/{session_id}/stop'
            }
        }), 201

    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        return jsonify({'error': str(e)}), 400

    except Exception as e:
        logger.error(f"Error starting session: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/sessions/<session_id>/stream', methods=['GET'])
def stream_session(session_id: str):
    """
    Stream unified transcript + graph updates for a session.

    Server-Sent Events stream that combines:
    - Transcript chunks from STT
    - Updated graphs from graph-generation

    Args:
        session_id: Session ID

    Returns:
        SSE stream with events:
        {
            "event_type": "update",
            "chunk_id": 0,
            "transcript": {...},
            "graph": {...},
            "session_id": "..."
        }
    """
    # Check session exists
    session = orchestrator.get_session(session_id)
    if not session:
        return jsonify({'error': f'Session {session_id} not found'}), 404

    if session['status'] != 'active':
        return jsonify({'error': f'Session {session_id} is not active'}), 400

    def generate():
        """Generator function for SSE stream."""
        try:
            # Subscribe to STT stream
            stt_url = f"{STT_SERVICE_URL}/sessions/{session_id}/stream"
            logger.info(f"Subscribing to STT stream: {stt_url}")

            with requests.get(stt_url, stream=True, timeout=None) as response:
                if response.status_code != 200:
                    error_msg = f"STT stream failed: {response.status_code}"
                    logger.error(error_msg)
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
                    return

                # Read SSE stream line by line
                for line in response.iter_lines():
                    if not line:
                        continue

                    line = line.decode('utf-8')

                    # Parse SSE data
                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove 'data: ' prefix

                        try:
                            chunk_data = json.loads(data_str)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in STT stream: {data_str}")
                            continue

                        # Add chunk to session
                        orchestrator.add_transcript_chunk(session_id, chunk_data)

                        # Call graph-generation service
                        session_state = orchestrator.get_session(session_id)
                        previous_graph = session_state.get('graph')

                        try:
                            graph_response = requests.post(
                                f"{GRAPH_SERVICE_URL}/generate-graph",
                                json={
                                    'session_id': session_id,
                                    'new_text': chunk_data.get('text', ''),
                                    'previous_graph': previous_graph
                                },
                                headers={'Content-Type': 'application/json'},
                                timeout=30
                            )

                            if graph_response.status_code == 200:
                                new_graph = graph_response.json()

                                # Update graph in session
                                orchestrator.update_graph(session_id, new_graph, chunk_info=chunk_data)

                                # Emit unified event
                                unified_event = {
                                    'event_type': 'update',
                                    'chunk_id': chunk_data.get('chunk_id'),
                                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                                    'session_id': session_id,
                                    'transcript': chunk_data,
                                    'graph': new_graph
                                }

                                yield f"data: {json.dumps(unified_event)}\n\n"

                            else:
                                logger.error(
                                    f"Graph generation failed: {graph_response.status_code} - "
                                    f"{graph_response.text}"
                                )
                                # Emit transcript without graph update
                                error_event = {
                                    'event_type': 'transcript_only',
                                    'chunk_id': chunk_data.get('chunk_id'),
                                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                                    'session_id': session_id,
                                    'transcript': chunk_data,
                                    'error': 'Graph generation failed'
                                }
                                yield f"data: {json.dumps(error_event)}\n\n"

                        except requests.exceptions.Timeout:
                            logger.error("Graph generation timeout")
                            error_event = {
                                'event_type': 'transcript_only',
                                'chunk_id': chunk_data.get('chunk_id'),
                                'timestamp': datetime.utcnow().isoformat() + 'Z',
                                'session_id': session_id,
                                'transcript': chunk_data,
                                'error': 'Graph generation timeout'
                            }
                            yield f"data: {json.dumps(error_event)}\n\n"

                        except Exception as e:
                            logger.error(f"Graph generation error: {e}", exc_info=True)
                            error_event = {
                                'event_type': 'transcript_only',
                                'chunk_id': chunk_data.get('chunk_id'),
                                'timestamp': datetime.utcnow().isoformat() + 'Z',
                                'session_id': session_id,
                                'transcript': chunk_data,
                                'error': str(e)
                            }
                            yield f"data: {json.dumps(error_event)}\n\n"

        except requests.exceptions.RequestException as e:
            logger.error(f"STT stream connection error: {e}")
            yield f"data: {json.dumps({'error': 'STT stream connection failed', 'details': str(e)})}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/sessions/<session_id>/state', methods=['GET'])
def get_session_state(session_id: str):
    """
    Get current session state.

    Returns complete session state including graph and transcript.

    Args:
        session_id: Session ID

    Returns:
        200: Session state
        404: Session not found
    """
    session = orchestrator.get_session(session_id)

    if not session:
        return jsonify({'error': f'Session {session_id} not found'}), 404

    return jsonify(session), 200


@app.route('/sessions/<session_id>/stop', methods=['POST'])
def stop_session(session_id: str):
    """
    Stop a session.

    Stops STT recording and returns final state.

    Args:
        session_id: Session ID

    Returns:
        200: Session stopped
        404: Session not found
        500: Error stopping session
    """
    try:
        # Check session exists
        session = orchestrator.get_session(session_id)
        if not session:
            return jsonify({'error': f'Session {session_id} not found'}), 404

        # Stop STT session
        try:
            stt_response = requests.post(
                f"{STT_SERVICE_URL}/sessions/{session_id}/stop",
                json={},
                headers={'Content-Type': 'application/json'},
                timeout=5
            )

            if stt_response.status_code not in [200, 404]:
                logger.warning(f"STT stop failed: {stt_response.status_code}")

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to stop STT session: {e}")

        # Stop orchestrator session
        result = orchestrator.stop_session(session_id)

        # Get final state
        final_session = orchestrator.get_session(session_id)

        return jsonify({
            **result,
            'final_graph': final_session.get('graph'),
            'full_transcript': final_session.get('full_transcript')
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 404

    except Exception as e:
        logger.error(f"Error stopping session: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id: str):
    """
    Delete a session from memory.

    Args:
        session_id: Session ID

    Returns:
        204: Session deleted
        404: Session not found
    """
    deleted = orchestrator.delete_session(session_id)

    if deleted:
        return '', 204
    else:
        return jsonify({'error': f'Session {session_id} not found'}), 404


def print_banner():
    """Print startup banner."""
    print("\n" + "=" * 60)
    print("ORCHESTRATOR SERVICE")
    print("=" * 60)
    print(f"Port: {PORT}")
    print(f"Debug: {DEBUG}")
    print(f"Max Sessions: {MAX_SESSIONS}")
    print()
    print(f"Speech-to-Text:    {STT_SERVICE_URL}")
    print(f"Graph Generation:  {GRAPH_SERVICE_URL}")
    print()
    print("Endpoints:")
    print("  GET  /health                      - Health check")
    print("  GET  /sessions                    - List sessions")
    print("  POST /sessions/start              - Start new session")
    print("  GET  /sessions/<id>/stream        - Stream updates (SSE)")
    print("  GET  /sessions/<id>/state         - Get session state")
    print("  POST /sessions/<id>/stop          - Stop session")
    print("  DEL  /sessions/<id>               - Delete session")
    print("=" * 60)
    print()


if __name__ == '__main__':
    print_banner()

    # Check service availability on startup
    stt_ok = check_service_health('stt', STT_SERVICE_URL)
    graph_ok = check_service_health('graph', GRAPH_SERVICE_URL)

    if not stt_ok:
        logger.warning(f"⚠️  Speech-to-text service not responding at {STT_SERVICE_URL}")
    else:
        logger.info(f"✅ Speech-to-text service healthy at {STT_SERVICE_URL}")

    if not graph_ok:
        logger.warning(f"⚠️  Graph generation service not responding at {GRAPH_SERVICE_URL}")
    else:
        logger.info(f"✅ Graph generation service healthy at {GRAPH_SERVICE_URL}")

    # Start server
    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=DEBUG,
        threaded=True
    )
