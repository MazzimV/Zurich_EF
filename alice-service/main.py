"""Jessica Service - Flask API for answering meeting questions."""

import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from jessica_responder import JessicaResponder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize Jessica responder
responder = JessicaResponder()

logger.info("Jessica Service initialized")


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'jessica-service'
    }), 200


@app.route('/answer-question', methods=['POST'])
def answer_question():
    """
    Answer a question about the meeting.

    Request JSON:
        {
            "question": "The question to answer",
            "session_id": "unique-session-id",
            "transcript": "Full meeting transcript",
            "graph": {...}  // Optional knowledge graph
        }

    Response JSON:
        {
            "answer": "Jessica's answer",
            "audio_base64": "base64-encoded MP3 audio",
            "timestamp": "ISO-8601 timestamp",
            "error": "error message if any"
        }
    """
    try:
        # Parse request
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        question = data.get('question')
        if not question:
            return jsonify({'error': 'Missing required field: question'}), 400

        session_id = data.get('session_id')
        transcript = data.get('transcript', '')
        graph = data.get('graph')

        logger.info(f"Received question for session {session_id}: {question[:100]}...")

        # Generate answer
        response = responder.answer(
            question=question,
            transcript=transcript,
            graph=graph,
            session_id=session_id
        )

        logger.info("Successfully generated response")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


if __name__ == '__main__':
    import os

    # Get port from environment or default to 8004
    port = int(os.getenv('PORT', 8004))

    logger.info(f"Starting Jessica Service on port {port}")

    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    )
