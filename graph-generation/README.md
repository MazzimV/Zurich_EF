# Graph Generation Component

Transforms transcript text into knowledge graphs using LLM-based analysis.

## Responsibility

- Receive new transcript chunks and previous graph state
- Use LLM to analyze and update the graph
- Output complete graph with rich UI metadata
- Maintain node ID stability across updates

## Input/Output

### Input
```json
{
  "session_id": "session-123",
  "new_text": "So I think we should focus on the user experience",
  "previous_graph": {
    "nodes": [...],
    "edges": [...],
    "metadata": {...}
  }
}
```

### Output
```json
{
  "session_id": "session-123",
  "version": 2,
  "timestamp": "2025-11-01T10:30:47Z",
  "nodes": [
    {
      "id": "node-1",
      "label": "User Experience",
      "type": "topic",
      "importance": 0.9,
      "color": "#8B5CF6",
      ...
    }
  ],
  "edges": [...],
  "metadata": {...}
}
```

See `../docs/graph-schema.md` for complete schema documentation.

## Setup

### Prerequisites

- Python 3.8+
- Anthropic API key (Claude)

### Installation

```bash
cd graph-generation
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:

```env
# Choose your LLM provider

# Anthropic Claude
ANTHROPIC_API_KEY=your-claude-api-key
LLM_MODEL=claude-3-5-haiku-20241022  # Fast and cheap (default)
# LLM_MODEL=claude-3-5-sonnet-20241022  # Better quality, slower

# Server config
PORT=8002
MAX_GRAPH_NODES=50  # Limit graph complexity
```

## Development

### Project Structure

```
graph-generation/
├── README.md
├── requirements.txt
├── .env
├── prompts/
│   └── system-prompt.md     # LLM prompt template
└── src/
    ├── main.py              # API server
    ├── graph_generator.py   # Core graph generation logic
    ├── llm_client.py        # LLM API wrapper
    ├── graph_validator.py   # Schema validation
    └── test_generation.py   # Testing script
```

### Running the Service

```bash
python src/main.py
```

This starts an API server on `http://localhost:8002`

### API Endpoints

#### Generate Graph

```
POST /generate-graph
Content-Type: application/json

{
  "session_id": "session-123",
  "new_text": "transcript chunk",
  "previous_graph": { /* graph or null */ }
}
```

Returns:
```json
{
  "session_id": "session-123",
  "version": 2,
  "nodes": [...],
  "edges": [...],
  "metadata": {...}
}
```

### Testing

Test with sample data:

```bash
python src/test_generation.py
```

This should:
1. Load sample transcript from `../shared/examples/`
2. Generate graph
3. Validate against schema
4. Save output to `../shared/examples/test-graph.json`

## Implementation Guide

### Step 1: LLM Client

Create a wrapper for LLM API calls:

```python
import anthropic
import os

class LLMClient:
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.getenv('ANTHROPIC_API_KEY')
        )
        self.model = os.getenv('LLM_MODEL', 'claude-3-haiku-20240307')

    def generate_graph(self, prompt: str) -> str:
        """Call LLM and return JSON response"""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        return message.content[0].text
```

### Step 2: Prompt Engineering

The system prompt in `prompts/system-prompt.md` is critical. It should:

1. Explain the task (update graph from transcript)
2. Describe the graph schema
3. Emphasize ID stability
4. Give examples
5. Encourage creative freedom for visualization

Example prompt structure:

```markdown
You are a knowledge graph generator. You will receive:
1. A new chunk of transcript text
2. The previous graph state (or null if first chunk)

Your task: Output a complete updated graph as JSON.

Key rules:
- REUSE node IDs from previous graph when concepts persist
- Merge similar concepts instead of creating duplicates
- Increase importance for repeated mentions
- Create meaningful edges between related concepts
- Include rich UI metadata (colors, types, descriptions)
- Keep graph focused (max 50 nodes)

Graph schema:
{
  "nodes": [
    {
      "id": "stable-unique-id",
      "label": "User Experience",
      "type": "topic|concept|decision|question|action|person",
      "importance": 0.0-1.0,
      ...
    }
  ],
  "edges": [...]
}

Previous graph: {previous_graph}
New text: {new_text}

Output ONLY valid JSON, no explanation.
```

### Step 3: Graph Generation Logic

```python
def generate_graph(new_text: str, previous_graph: dict) -> dict:
    """Generate updated graph from new text and previous state"""

    # Load system prompt template
    with open('prompts/system-prompt.md', 'r') as f:
        template = f.read()

    # Build prompt
    prompt = template.format(
        previous_graph=json.dumps(previous_graph) if previous_graph else "null",
        new_text=new_text
    )

    # Call LLM
    llm = LLMClient()
    response = llm.generate_graph(prompt)

    # Parse JSON (handle markdown code blocks)
    graph_json = extract_json(response)
    graph = json.loads(graph_json)

    # Validate schema
    validate_graph(graph)

    # Add metadata
    graph['timestamp'] = datetime.utcnow().isoformat() + 'Z'
    graph['version'] = (previous_graph.get('version', 0) + 1) if previous_graph else 1

    return graph
```

### Step 4: Schema Validation

```python
def validate_graph(graph: dict) -> None:
    """Validate graph against schema, raise if invalid"""

    # Check required fields
    assert 'nodes' in graph, "Missing 'nodes' field"
    assert 'edges' in graph, "Missing 'edges' field"

    # Check node IDs are unique
    node_ids = [n['id'] for n in graph['nodes']]
    assert len(node_ids) == len(set(node_ids)), "Duplicate node IDs"

    # Check edges reference existing nodes
    for edge in graph['edges']:
        assert edge['source'] in node_ids, f"Edge source {edge['source']} not found"
        assert edge['target'] in node_ids, f"Edge target {edge['target']} not found"

    # Check numeric ranges
    for node in graph['nodes']:
        if 'importance' in node:
            assert 0 <= node['importance'] <= 1, "Importance out of range"

    # More validation...
```

### Step 5: API Server

```python
from flask import Flask, request, jsonify
from graph_generator import generate_graph

app = Flask(__name__)

@app.route('/generate-graph', methods=['POST'])
def generate():
    data = request.json

    session_id = data['session_id']
    new_text = data['new_text']
    previous_graph = data.get('previous_graph')

    try:
        # Generate graph
        graph = generate_graph(new_text, previous_graph)
        graph['session_id'] = session_id

        return jsonify(graph), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=8002)
```

## Optimization Strategies

### Speed Optimization

1. **Use fast models**: Claude 3.5 Haiku (default)
2. **Limit context**: Only send recent transcript (last 500 words)
3. **Compress previous graph**: Summarize old nodes
4. **Streaming**: Use LLM streaming API for faster perceived response

### Cost Optimization

1. **Batching**: Accumulate 2-3 chunks before updating
2. **Caching**: Cache graph for identical inputs
3. **Smart updates**: Only call LLM if new text is meaningful

### Quality Optimization

1. **Better prompts**: Iterate on system prompt with examples
2. **Post-processing**: Merge similar nodes after LLM output
3. **Feedback loop**: Use UI interactions to refine future graphs

## Prompt Engineering Tips

The quality of your graph depends heavily on the prompt. Key elements:

### 1. Clear Instructions
```
Task: Update the knowledge graph based on new discussion text.
```

### 2. Schema Definition
```
Output must follow this exact JSON schema: {...}
```

### 3. Examples
```
Example input:
  Previous graph: {simple example}
  New text: "We should add authentication"

Example output:
  {expected graph JSON}
```

### 4. ID Stability Rules
```
CRITICAL: When updating the graph:
- If a node from previous_graph is still relevant, KEEP its ID
- Example: If node "node-5" was "User Auth", and new text mentions auth,
  update that node instead of creating a new one
```

### 5. Creative Freedom
```
You have freedom to:
- Choose colors that make semantic sense
- Decide node types and importance
- Create edges that show relationships
- Use descriptions to add context
```

See `prompts/system-prompt.md` for the full prompt template.

## Testing Strategy

### Unit Tests

```bash
# Test LLM client
python src/test_llm_client.py

# Test schema validation
python src/test_validator.py
```

### Integration Tests

```bash
# Test full pipeline with sample data
python src/test_generation.py

# Should output to ../shared/examples/test-graph.json
```

### Prompt Testing

Test prompt quality:

```python
# Test with increasingly complex transcripts
test_cases = [
    "Simple topic",
    "Topic with multiple concepts",
    "Complex discussion with relationships",
    "Returning to earlier topics"
]

for text in test_cases:
    graph = generate_graph(text, None)
    print(f"Nodes: {len(graph['nodes'])}, Edges: {len(graph['edges'])}")
```

## Common Issues

**Issue**: LLM creates duplicate nodes
- **Solution**: Emphasize ID reuse in prompt
- **Solution**: Add post-processing to merge similar nodes

**Issue**: Response is too slow (>3 seconds)
- **Solution**: Use Claude 3.5 Haiku (default model)
- **Solution**: Reduce previous_graph size

**Issue**: Invalid JSON output
- **Solution**: Add JSON parsing with error handling
- **Solution**: Use LLM's JSON mode if available

**Issue**: Graph gets too complex
- **Solution**: Add node limit in prompt (max 50 nodes)
- **Solution**: Prune low-importance nodes

**Issue**: Nodes change IDs unnecessarily
- **Solution**: Improve ID stability instructions in prompt
- **Solution**: Add deterministic ID generation based on content

## Claude Model Options

| Model | Speed | Cost (per call) | Quality |
|-------|-------|-----------------|---------|
| Claude 3.5 Haiku | Fast (~1s) | ~$0.001 | Excellent |
| Claude 3.5 Sonnet | Medium (~2s) | ~$0.005 | Excellent |

**Recommendation**: Claude 3.5 Haiku (default, fast, cheap, great quality)

## Next Steps

1. Set up LLM API key
2. Create system prompt in `prompts/system-prompt.md`
3. Implement basic graph generation
4. Test with sample transcript data
5. Iterate on prompt quality
6. Build API server
7. Test integration with frontend

## Resources

- [Anthropic Claude API Docs](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)
- [JSON Schema Validation](https://json-schema.org/)
- Graph schema: `../docs/graph-schema.md`

## Support

Questions? Check:
- `../docs/integration.md` for how this connects to other components
- `../docs/graph-schema.md` for detailed schema documentation
- `../shared/examples/` for sample data
- `../CLAUDE.md` for project context
