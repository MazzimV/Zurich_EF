# Orchestrator Quick Start Guide

Get the complete pipeline running in 5 minutes!

## What is This?

The orchestrator bridges your speech-to-text and graph-generation services:

```
[Microphone] → STT → ORCHESTRATOR → Graph-Gen → [Unified Stream]
                                                        ↓
                                                   Frontend
```

## Prerequisites

You need all three services running:

1. **Speech-to-Text** (port 8005)
2. **Graph-Generation** (port 8002)
3. **Orchestrator** (port 8003) ← this service

## Setup Steps

### 1. Start Speech-to-Text

```bash
# Terminal 1
cd speech-to-text/src
python main.py

# Should show: Running on port 8005
```

### 2. Start Graph Generation

```bash
# Terminal 2
cd graph-generation/segmentation
python main.py

# Should show: Running on port 8002
```

**Important:** Make sure you have `ANTHROPIC_API_KEY` in `graph-generation/segmentation/.env`

### 3. Start Orchestrator

```bash
# Terminal 3
cd orchestrator

# Create virtual environment (first time only)
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies (first time only)
pip install -r requirements.txt

# Start the orchestrator
cd src
python main.py

# Should show:
# ✅ Speech-to-text service healthy
# ✅ Graph generation service healthy
```

## Quick Test

In a **fourth terminal**, run the test script:

```bash
cd orchestrator
source venv/bin/activate
python test_orchestrator.py
```

The test will:
1. Check all services are healthy
2. Start a session
3. Stream for 20 seconds (**speak into your mic!**)
4. Show transcript chunks + updated graphs
5. Stop the session

## Manual Testing with curl

### Start a session:

```bash
curl -X POST http://localhost:8003/sessions/start | jq
```

You'll get a `session_id`. Copy it!

### Stream the unified output:

```bash
# Replace SESSION_ID with your actual session ID
curl http://localhost:8003/sessions/SESSION_ID/stream
```

**Now speak into your microphone!** You'll see:

```json
data: {
  "event_type": "update",
  "transcript": {
    "text": "A: Let's discuss the mobile app",
    "chunk_id": 0
  },
  "graph": {
    "nodes": [{"label": "Mobile App", ...}],
    "edges": [],
    "version": 1
  }
}
```

### Stop the session:

```bash
curl -X POST http://localhost:8003/sessions/SESSION_ID/stop | jq
```

## What You'll See

**In the stream, you get both:**

1. **Transcript chunks** - Text with speaker labels (A, B, C, etc.)
2. **Updated graphs** - Knowledge graph extracted from the conversation

All in one unified stream, ready for your frontend!

## Common Issues

### "STT service unavailable"

```bash
# Check if running
curl http://localhost:8005/health

# If not, start it
cd speech-to-text/src && python main.py
```

### "Graph generation failed"

```bash
# Check if running
curl http://localhost:8002/health

# If not, check API key
cd graph-generation/segmentation
cat .env | grep ANTHROPIC_API_KEY

# Then start it
python main.py
```

### Port already in use

```bash
# Find what's using the port
lsof -ti:8003 | xargs kill

# Or change the port in orchestrator/.env
PORT=8004
```

## Next Steps

Once everything works:

1. **Build your frontend** - Connect to `http://localhost:8003/sessions/{id}/stream`
2. **Visualize the graph** - Use D3.js, Cytoscape, or your favorite library
3. **Display transcripts** - Show real-time speech-to-text with speaker labels
4. **Add features** - Export, replay, analytics, etc.

## Frontend Integration Example

```javascript
// Start session
const res = await fetch('http://localhost:8003/sessions/start', {
  method: 'POST'
});
const { session_id } = await res.json();

// Subscribe to unified stream
const eventSource = new EventSource(
  `http://localhost:8003/sessions/${session_id}/stream`
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  // Update transcript UI
  updateTranscript(data.transcript);

  // Update graph visualization
  updateGraph(data.graph);
};
```

## Architecture

The orchestrator is **stateless** for the underlying services but **stateful** for sessions:

- Stores current graph state (for passing to next update)
- Stores full transcript history
- Manages session lifecycle
- Handles errors gracefully

This means:
- STT and Graph-Gen can be scaled independently
- Sessions survive as long as orchestrator runs
- Easy to add persistence (Redis) later

## Need Help?

Check:
- `README.md` - Complete API reference
- `test_orchestrator.py` - Test script with examples
- `../speech-to-text/INTEGRATION.md` - STT docs
- `../graph-generation/README.md` - Graph-Gen docs

Happy orchestrating! 🎤📊🚀
