# Integration Guide

## How Components Connect

This guide explains how the three components work together and how to test integration.

## Integration Architecture

```
┌──────────────────────────────────────────────────────────┐
│                        Frontend                          │
│  - Manages session state                                 │
│  - Orchestrates components                               │
│  - Renders visualization                                 │
└───────┬────────────────────────────────┬─────────────────┘
        │                                │
        │ HTTP/WebSocket                 │ HTTP
        │                                │
        ▼                                ▼
┌──────────────────┐           ┌───────────────────────┐
│  STT Service     │           │  Graph Gen Service    │
│  Port: 8001      │           │  Port: 8002           │
└──────────────────┘           └───────────────────────┘
```

## API Contracts

### Speech-to-Text API

**Endpoint**: `POST /transcribe/stream`

**Request** (start streaming):
```json
{
  "session_id": "session-123",
  "action": "start"
}
```

**Response** (WebSocket or SSE stream):
```json
{
  "timestamp": "2025-11-01T10:30:45Z",
  "text": "So I think we should focus on the user experience",
  "session_id": "session-123",
  "chunk_id": 42
}
```

**Alternative**: Simple polling endpoint
```
GET /transcribe/latest?session_id=session-123
```

### Graph Generation API

**Endpoint**: `POST /generate-graph`

**Request**:
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

For first request, `previous_graph` can be `null` or empty graph.

**Response**:
```json
{
  "session_id": "session-123",
  "version": 2,
  "timestamp": "2025-11-01T10:30:47Z",
  "nodes": [...],
  "edges": [...],
  "metadata": {...}
}
```

**Headers**:
- `Content-Type: application/json`
- Processing should complete in <3 seconds

## Integration Flow

### Step 1: Session Initialization

**Frontend**:
```javascript
const sessionId = generateSessionId();
const state = {
  sessionId,
  transcript: "",
  currentGraph: null,
  isRecording: false
};
```

### Step 2: Start Recording

**Frontend → STT**:
```javascript
// Start recording
await fetch('http://localhost:8001/transcribe/stream', {
  method: 'POST',
  body: JSON.stringify({
    session_id: sessionId,
    action: 'start'
  })
});

// Listen for chunks (WebSocket or polling)
const eventSource = new EventSource(
  `http://localhost:8001/transcribe/stream?session_id=${sessionId}`
);

eventSource.onmessage = (event) => {
  const chunk = JSON.parse(event.data);
  handleNewTranscript(chunk);
};
```

### Step 3: Process Transcript Chunks

**Frontend → Graph Generation**:
```javascript
async function handleNewTranscript(chunk) {
  // Accumulate transcript
  state.transcript += chunk.text;

  // Send to graph generator
  const response = await fetch('http://localhost:8002/generate-graph', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: state.sessionId,
      new_text: chunk.text,
      previous_graph: state.currentGraph
    })
  });

  const newGraph = await response.json();
  updateVisualization(newGraph);
  state.currentGraph = newGraph;
}
```

### Step 4: Update Visualization

**Frontend**:
```javascript
function updateVisualization(newGraph) {
  // Smooth transition from old graph to new graph
  // Maintain node positions for existing nodes
  // Animate new nodes and edges
  graphRenderer.update(newGraph);
}
```

## Testing Integration

### Level 1: Component Testing

Each component should work independently:

**STT Component**:
```bash
cd speech-to-text
python src/test_stt.py
# Should output transcript chunks
```

**Graph Generation**:
```bash
cd graph-generation
python src/test_generation.py
# Should output valid graph JSON
```

### Level 2: API Testing

Use sample data to test APIs:

**Test STT API**:
```bash
curl -X POST http://localhost:8001/transcribe/stream \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-123", "action": "start"}'
```

**Test Graph API**:
```bash
curl -X POST http://localhost:8002/generate-graph \
  -H "Content-Type: application/json" \
  -d @shared/examples/sample-request.json
```

### Level 3: End-to-End Testing

1. Start all services
2. Open frontend
3. Start a recording
4. Speak or play audio
5. Verify graph updates in real-time

## Development Workflow

### Parallel Development

1. **STT Team**:
   - Build API that outputs to `shared/examples/test-transcript.json`
   - Follow schema in `shared/schemas/transcript.json`

2. **Graph Team**:
   - Read from `shared/examples/test-transcript.json`
   - Output to `shared/examples/test-graph.json`
   - Follow schema in `shared/schemas/graph.json`

3. **Frontend Team**:
   - Read from `shared/examples/test-graph.json`
   - Mock API responses initially
   - Integrate with real APIs when ready

### Using Mock Data

Create test files in `shared/examples/`:

**mock-transcript-stream.json**:
```json
[
  {"text": "First chunk", "timestamp": "..."},
  {"text": "Second chunk", "timestamp": "..."},
  {"text": "Third chunk", "timestamp": "..."}
]
```

**mock-graph-evolution.json**:
```json
[
  {"version": 1, "nodes": [...]},
  {"version": 2, "nodes": [...]},
  {"version": 3, "nodes": [...]}
]
```

## Error Handling

### STT Service Down

```javascript
try {
  await fetch(sttEndpoint, ...);
} catch (error) {
  // Show error in UI
  showError("Transcription service unavailable");
  // Stop recording
  stopRecording();
}
```

### Graph Generation Timeout

```javascript
const response = await fetch(graphEndpoint, {
  signal: AbortSignal.timeout(5000) // 5 second timeout
});

if (!response.ok) {
  // Keep previous graph
  console.error("Graph generation failed");
  showWarning("Using previous graph state");
}
```

### Invalid Graph Response

```javascript
const newGraph = await response.json();

if (!validateGraphSchema(newGraph)) {
  console.error("Invalid graph schema");
  // Keep previous graph
  return;
}
```

## Environment Configuration

### STT Service

`.env`:
```
STT_API_KEY=your-api-key
STT_MODEL=whisper-1
PORT=8001
```

### Graph Generation Service

`.env`:
```
ANTHROPIC_API_KEY=your-claude-key
# or
OPENAI_API_KEY=your-openai-key
MODEL=claude-3-haiku-20240307
PORT=8002
```

### Frontend

`.env.local`:
```
NEXT_PUBLIC_STT_URL=http://localhost:8001
NEXT_PUBLIC_GRAPH_URL=http://localhost:8002
```

## Deployment

### Local Development
```bash
# Terminal 1
cd speech-to-text && python src/main.py

# Terminal 2
cd graph-generation && python src/main.py

# Terminal 3
cd frontend && npm run dev
```

### Production (Future)

- Deploy STT and Graph Gen as separate services (Railway, Render, AWS Lambda)
- Deploy Frontend to Vercel
- Use environment variables for service URLs
- Add authentication and rate limiting

## Common Integration Issues

**Issue**: Graph updates are slow
- **Solution**: Use faster LLM model (Haiku instead of Opus)
- **Solution**: Reduce graph size sent to LLM

**Issue**: Node positions jump around
- **Solution**: Frontend should maintain positions for existing nodes
- **Solution**: Only animate new nodes

**Issue**: Duplicate nodes created
- **Solution**: LLM prompt needs better ID stability instructions
- **Solution**: Add post-processing to merge similar nodes

**Issue**: Transcript chunks too small/large
- **Solution**: Adjust STT chunk size (aim for 1-2 sentences)
- **Solution**: Add debouncing in frontend

## Next Steps

1. Each team: implement basic API following contracts above
2. Use `shared/examples/` for cross-team testing
3. Validate against schemas before integration
4. Schedule integration session when all APIs are ready
5. Test end-to-end with real audio
