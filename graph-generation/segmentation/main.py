"""
Graph Generation API Server

Flask API server for generating knowledge graphs from transcript text.
"""

import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from graph_generator import GraphGenerator, generate_graph
from graph_validator import GraphValidationError

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Initialize graph generator
generator = GraphGenerator()


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'graph-generation'}), 200


@app.route('/generate-graph', methods=['POST'])
def generate():
    """
    Generate or update a knowledge graph from transcript text.
    
    Request body:
    {
        "session_id": "session-123",
        "new_text": "transcript chunk text",
        "previous_graph": { /* graph object or null */ }
    }
    
    Returns:
    {
        "session_id": "session-123",
        "version": 2,
        "timestamp": "ISO-8601",
        "nodes": [...],
        "edges": [...],
        "metadata": {...}
    }
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        session_id = data.get('session_id')
        new_text = data.get('new_text', '')
        previous_graph = data.get('previous_graph')
        
        if not new_text:
            return jsonify({'error': 'new_text is required'}), 400
        
        # Generate graph
        graph = generator.generate(
            new_text=new_text,
            previous_graph=previous_graph,
            session_id=session_id
        )
        
        return jsonify(graph), 200
        
    except GraphValidationError as e:
        return jsonify({'error': f'Graph validation failed: {str(e)}'}), 400
    except ValueError as e:
        return jsonify({'error': f'Invalid request: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8002))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    print(f"Starting Graph Generation API server on port {port}")
    print(f"Debug mode: {debug}")
    print(f"Environment: {os.getenv('LLM_MODEL', 'claude-sonnet-4-5-20250929')}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

