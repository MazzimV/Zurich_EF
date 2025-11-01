# Orchestrator Service

The **Orchestrator** bridges the speech-to-text and graph-generation/segmentation services, providing a unified API for real-time brainstorming visualization.

## Purpose

This service coordinates the flow between:
1. **Speech-to-Text** (port 8005) - Captures and transcribes audio
2. **Graph-Generation** (port 8002) - Generates knowledge graphs from text
3. **Frontend** (your choice) - Visualizes the unified stream

```
┌─────────────┐
│ Speech-to-  │ SSE Stream
│    Text     │──────────┐
│  Port 8005  │          │
└─────────────┘          ▼
                  ┌──────────────┐
                  │ ORCHESTRATOR │ ← You are here
                  │  Port 8003   │
                  └──────────────┘
                         │
                         │ HTTP POST
                         ▼
                  ┌─────────────┐
                  │   Graph     │
                  │ Generation  │
                  │  Port 8002  │
                  └─────────────┘
                         │
                         ▼
                  Unified SSE Stream:
                  { transcript + graph }
                         │
                         ▼
                    Frontend
```

## Features

✅ **Unified API** - Single endpoint for transcript + graph stream
✅ **Session Management** - Handles multiple concurrent sessions
✅ **State Storage** - Maintains graph history and full transcript
✅ **Error Handling** - Graceful fallbacks if services fail
✅ **Health Monitoring** - Checks dependencies automatically
✅ **SSE Streaming** - Real-time updates via Server-Sent Events
✅ **No Code Changes** - Works with existing services as-is

## Quick Start

### 1. Prerequisites

Make sure both services are running:

```bash
# Terminal 1: Speech-to-Text
cd speech-to-text/src
python main.py
# Running on port 8005

# Terminal 2: Graph Generation
cd graph-generation/segmentation
python main.py
# Running on port 8002
```

### 2. Setup Orchestrator

```bash
cd orchestrator

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure (optional - defaults work out of the box)
cp .env.example .env
```

### 3. Start the Service

```bash
cd src
python main.py
```

You should see:

```
============================================================
ORCHESTRATOR SERVICE
============================================================
Port: 8003
Debug: False
Max Sessions: 10

Speech-to-Text:    http://localhost:8005
Graph Generation:  http://localhost:8002

Endpoints:
  GET  /health                      - Health check
  GET  /sessions                    - List sessions
  POST /sessions/start              - Start new session
  GET  /sessions/<id>/stream        - Stream updates (SSE)
  GET  /sessions/<id>/state         - Get session state
  POST /sessions/<id>/stop          - Stop session
  DEL  /sessions/<id>               - Delete session
============================================================

✅ Speech-to-text service healthy at http://localhost:8005
✅ Graph generation service healthy at http://localhost:8002
```

## API Reference

### Base URL
```
http://localhost:8003
```

---

### 1. Health Check

```http
GET /health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "orchestrator",
  "timestamp": "2025-11-01T16:00:00Z",
  "dependencies": {
    "speech_to_text": {
      "url": "http://localhost:8005",
      "healthy": true
    },
    "graph_generation": {
      "url": "http://localhost:8002",
      "healthy": true
    }
  },
  "stats": {
    "total_sessions": 2,
    "active_sessions": 1,
    "stopped_sessions": 1,
    "max_sessions": 10
  }
}
```

---

### 2. List Sessions

```http
GET /sessions
```

**Response (200 OK):**
```json
{
  "sessions": [
    {
      "session_id": "session-abc123",
      "status": "active",
      "created_at": "2025-11-01T16:00:00Z",
      "started_at": "2025-11-01T16:00:01Z",
      "stopped_at": null,
      "chunk_count": 5,
      "graph_version": 5
    }
  ],
  "count": 1
}
```

---

### 3. Start Session

```http
POST /sessions/start
Content-Type: application/json
```

**Request Body (optional):**
```json
{
  "session_id": "my-custom-id"  // Optional: auto-generated if not provided
}
```

**Response (201 Created):**
```json
{
  "session_id": "session-abc123",
  "stt_session_id": "session-abc123",
  "status": "active",
  "started_at": "2025-11-01T16:00:00Z",
  "endpoints": {
    "stream": "/sessions/session-abc123/stream",
    "state": "/sessions/session-abc123/state",
    "stop": "/sessions/session-abc123/stop"
  }
}
```

**Error Responses:**
- `400` - Invalid request (max sessions reached)
- `503` - STT service unavailable
- `500` - Internal error

---

### 4. Stream Unified Updates (SSE)

```http
GET /sessions/{session_id}/stream
```

**Response:** Server-Sent Events stream

**Event Format:**
```
data: {"event_type":"update","chunk_id":0,"timestamp":"2025-11-01T16:00:08Z","session_id":"session-abc123","transcript":{"chunk_id":0,"text":"A: Let's discuss the mobile app","timestamp":"2025-11-01T16:00:08Z","session_id":"session-abc123"},"graph":{"session_id":"session-abc123","version":1,"timestamp":"2025-11-01T16:00:08Z","nodes":[{"id":"node-1","label":"Mobile App","type":"topic","importance":0.9,"color":"#8B5CF6"}],"edges":[],"metadata":{}}}

data: {"event_type":"update","chunk_id":1,"timestamp":"2025-11-01T16:00:16Z","session_id":"session-abc123","transcript":{"chunk_id":1,"text":"B: We need authentication","timestamp":"2025-11-01T16:00:16Z","session_id":"session-abc123"},"graph":{"session_id":"session-abc123","version":2,"timestamp":"2025-11-01T16:00:16Z","nodes":[{"id":"node-1","label":"Mobile App","type":"topic"},{"id":"node-2","label":"Authentication","type":"concept"}],"edges":[{"source":"node-2","target":"node-1","type":"relates_to"}],"metadata":{}}}
```

**Event Types:**
- `update` - Normal update with transcript + graph
- `transcript_only` - Graph generation failed, transcript only
- `error` - Error event

---

### 5. Get Session State

```http
GET /sessions/{session_id}/state
```

**Response (200 OK):**
```json
{
  "session_id": "session-abc123",
  "status": "active",
  "created_at": "2025-11-01T16:00:00Z",
  "started_at": "2025-11-01T16:00:01Z",
  "graph": {
    "nodes": [...],
    "edges": [...],
    "version": 5
  },
  "graph_version": 5,
  "transcript_chunks": [...],
  "full_transcript": "A: Let's discuss... B: We need...",
  "chunk_count": 5,
  "metadata": {
    "total_graph_updates": 5,
    "last_update_at": "2025-11-01T16:00:40Z"
  }
}
```

---

### 6. Stop Session

```http
POST /sessions/{session_id}/stop
Content-Type: application/json
```

**Response (200 OK):**
```json
{
  "session_id": "session-abc123",
  "status": "stopped",
  "stopped_at": "2025-11-01T16:05:00Z",
  "summary": {
    "chunk_count": 10,
    "graph_version": 10,
    "transcript_length": 450,
    "total_graph_updates": 10
  },
  "final_graph": {
    "nodes": [...],
    "edges": [...]
  },
  "full_transcript": "Complete transcript text..."
}
```

---

### 7. Delete Session

```http
DELETE /sessions/{session_id}
```

**Response (204 No Content)**

---

## Testing Without Frontend

You can test the complete pipeline using curl:

```bash
# 1. Start a session
SESSION=$(curl -X POST http://localhost:8003/sessions/start | jq -r '.session_id')
echo "Session ID: $SESSION"

# 2. Stream the unified output
curl http://localhost:8003/sessions/$SESSION/stream

# 3. Speak into your microphone!
# Watch the stream output transcript chunks and updated graphs

# 4. In another terminal, check state
curl http://localhost:8003/sessions/$SESSION/state | jq

# 5. Stop the session
curl -X POST http://localhost:8003/sessions/$SESSION/stop | jq
```

## Data Flow Example

Here's what happens when you speak:

```
1. You speak: "Let's build a mobile app"

2. Speech-to-Text (8005):
   - Captures audio
   - Transcribes to text
   - Emits: {"text": "A: Let's build a mobile app", "chunk_id": 0}

3. Orchestrator (8003):
   - Receives transcript chunk
   - Adds to session history
   - Calls Graph Generation with:
     {
       "new_text": "A: Let's build a mobile app",
       "previous_graph": null,
       "session_id": "session-xyz"
     }

4. Graph Generation (8002):
   - Uses Claude LLM to analyze text
   - Creates/updates knowledge graph
   - Returns:
     {
       "nodes": [{"id": "node-1", "label": "Mobile App", ...}],
       "edges": [],
       "version": 1
     }

5. Orchestrator:
   - Stores updated graph
   - Emits unified SSE event:
     {
       "event_type": "update",
       "transcript": {...},
       "graph": {...}
     }

6. Frontend (your app):
   - Receives unified event
   - Updates visualization
   - Shows transcript + animated graph
```

## Configuration

Edit `.env` to customize:

```env
# Service URLs (change if services run elsewhere)
STT_SERVICE_URL=http://localhost:8005
GRAPH_SERVICE_URL=http://localhost:8002

# Orchestrator port
PORT=8003

# Debug mode
DEBUG=false

# Max concurrent sessions
MAX_SESSIONS=10

# Logging level
LOG_LEVEL=INFO
```

## Architecture Decisions

### Why This Design?

**1. Separation of Concerns**
- Each service has a single responsibility
- Easy to test, debug, and maintain
- Can swap implementations independently

**2. Stateless Services**
- STT and Graph-Gen are stateless
- Orchestrator manages state (can be moved to Redis later)
- Easy horizontal scaling

**3. SSE for Real-Time**
- Simple, lightweight streaming
- Works with HTTP/1.1 (no WebSocket needed)
- Built-in reconnection in browsers

**4. No Code Changes**
- Works with existing services as-is
- Zero modifications to STT or Graph-Gen
- Just configuration (URLs, ports)

### State Management

The orchestrator stores **in-memory** session state:
- Current graph (for passing to next update)
- Full transcript history
- All transcript chunks
- Metadata (timestamps, counts, errors)

**For production**, you could:
- Add Redis for persistence
- Implement session snapshots
- Add database for long-term storage

### Error Handling

The orchestrator handles failures gracefully:

**If STT fails:**
- Returns 503 on session start
- Emits error in SSE stream

**If Graph-Gen fails:**
- Emits `transcript_only` event
- Continues streaming transcripts
- Graph stays at previous version

**If Orchestrator restarts:**
- All sessions lost (in-memory only)
- Clients can reconnect and start new sessions

## Common Issues

### "STT service unavailable"
```bash
# Check STT is running
curl http://localhost:8005/health

# Start STT if needed
cd speech-to-text/src && python main.py
```

### "Graph generation failed"
```bash
# Check Graph-Gen is running
curl http://localhost:8002/health

# Check it has ANTHROPIC_API_KEY
cd graph-generation/segmentation
cat .env | grep ANTHROPIC_API_KEY

# Start if needed
python main.py
```

### "SSE stream disconnects"
- Normal behavior after ~5 minutes
- Frontend should auto-reconnect
- Use EventSource's built-in reconnection

### Port already in use
```bash
# Change port in .env
PORT=8004

# Or kill existing process
lsof -ti:8003 | xargs kill
```

## Development

### Running Tests

```bash
# Test with sample script
python test_orchestrator.py
```

### Adding Features

The orchestrator is designed to be extended:

**Session Persistence:**
```python
# Add Redis storage
import redis
r = redis.Redis()

def save_session(session_id, data):
    r.set(f"session:{session_id}", json.dumps(data))
```

**Graph History:**
```python
# Store all versions
session['graph_history'] = []
session['graph_history'].append(new_graph)
```

**Analytics:**
```python
# Track metrics
session['metrics'] = {
    'avg_chunk_length': 0,
    'topics_discovered': 0,
    'speaker_switches': 0
}
```

## Integration with Frontend

### JavaScript Example

```javascript
// Start session
const response = await fetch('http://localhost:8003/sessions/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' }
});
const { session_id } = await response.json();

// Subscribe to stream
const eventSource = new EventSource(
  `http://localhost:8003/sessions/${session_id}/stream`
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.event_type === 'update') {
    // Update transcript display
    updateTranscript(data.transcript);

    // Update graph visualization
    updateGraph(data.graph);
  }
};

// Stop session when done
await fetch(`http://localhost:8003/sessions/${session_id}/stop`, {
  method: 'POST'
});
```

### React Example

```jsx
import { useEffect, useState } from 'react';

function BrainstormSession() {
  const [sessionId, setSessionId] = useState(null);
  const [transcript, setTranscript] = useState([]);
  const [graph, setGraph] = useState(null);

  useEffect(() => {
    // Start session
    fetch('http://localhost:8003/sessions/start', { method: 'POST' })
      .then(r => r.json())
      .then(data => {
        setSessionId(data.session_id);

        // Connect to stream
        const es = new EventSource(
          `http://localhost:8003/sessions/${data.session_id}/stream`
        );

        es.onmessage = (event) => {
          const update = JSON.parse(event.data);
          if (update.event_type === 'update') {
            setTranscript(prev => [...prev, update.transcript]);
            setGraph(update.graph);
          }
        };
      });
  }, []);

  return (
    <div>
      <TranscriptView chunks={transcript} />
      <GraphView graph={graph} />
    </div>
  );
}
```

## Performance

**Latency:** ~2-5 seconds per update
- 0-8 seconds: Audio buffering (STT)
- 0.5-2 seconds: Transcription (OpenAI)
- 1-3 seconds: Graph generation (Claude)

**Throughput:** ~10-15 updates/minute
- Limited by speech rate (~8 second chunks)

**Resource Usage:**
- CPU: Low (mostly I/O waiting)
- Memory: ~50MB per session
- Network: ~5KB per update

## Support

Questions? Check:
- `test_orchestrator.py` - Test script with examples
- `../speech-to-text/INTEGRATION.md` - STT API docs
- `../graph-generation/README.md` - Graph-Gen docs
- `../CLAUDE.md` - Project overview

## Next Steps

1. ✅ Start all three services (STT, Graph-Gen, Orchestrator)
2. ✅ Test with curl commands
3. ✅ Build frontend that connects to orchestrator
4. ⚡ Add features (persistence, analytics, etc.)

Happy orchestrating! 🎤📊🚀
