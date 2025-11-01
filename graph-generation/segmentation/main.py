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
        "previous_transcript": "transcript used to build previous graph (recommended)",
        "new_transcript": "new transcript to process (recommended)",
        "previous_graph": { /* graph object or null */ }
    }

    Legacy format (still supported):
    {
        "session_id": "session-123",
        "new_text": "transcript chunk text",
        "full_transcript": "complete transcript so far (optional)",
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
        previous_graph = data.get('previous_graph')

        # Support new format (previous_transcript + new_transcript)
        previous_transcript = data.get('previous_transcript')
        new_transcript = data.get('new_transcript')

        # Backward compatibility: support old format (full_transcript + new_text)
        if previous_transcript is None and new_transcript is None:
            # Old format
            new_text = data.get('new_text', '')
            full_transcript = data.get('full_transcript')

            if not new_text:
                return jsonify({'error': 'new_text or new_transcript is required'}), 400

            # Convert to new format
            previous_transcript = full_transcript if full_transcript else ''
            new_transcript = new_text
        else:
            # New format - validate
            if not new_transcript:
                return jsonify({'error': 'new_transcript is required'}), 400

        # Generate graph
        graph = generator.generate(
            previous_transcript=previous_transcript,
            new_transcript=new_transcript,
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


@app.route('/expand-node', methods=['POST'])
def expand_node():
    """
    Expand a node by generating 4 subtopic nodes.
    
    Request body:
    {
        "session_id": "session-123",
        "node_id": "node-5",
        "current_graph": { /* full graph object */ }
    }
    
    Returns:
    {
        "session_id": "session-123",
        "version": 3,
        "timestamp": "ISO-8601",
        "nodes": [...],  // includes 4 new subtopic nodes
        "edges": [...],  // includes 4 new edges to subtopics
        "metadata": {...}
    }
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        node_id = data.get('node_id')
        current_graph = data.get('current_graph')
        session_id = data.get('session_id')
        
        if not node_id:
            return jsonify({'error': 'node_id is required'}), 400
        
        if not current_graph:
            return jsonify({'error': 'current_graph is required'}), 400
        
        # Expand the node
        graph = generator.expand_node(
            node_id=node_id,
            current_graph=current_graph,
            session_id=session_id
        )
        
        return jsonify(graph), 200
        
    except ValueError as e:
        return jsonify({'error': f'Invalid request: {str(e)}'}), 400
    except GraphValidationError as e:
        return jsonify({'error': f'Graph validation failed: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8002))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    print(f"Starting Graph Generation API server on port {port}")
    print(f"Debug mode: {debug}")
    print(f"Environment: {os.getenv('LLM_MODEL', 'claude-sonnet-4-5-20250929')}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

