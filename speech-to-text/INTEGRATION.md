# Speech-to-Text Integration Guide

Complete guide for using the speech-to-text component with the rest of the brainstorming graph project.

## Table of Contents
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Integration with Graph Generation](#integration-with-graph-generation)
- [Integration with Frontend](#integration-with-frontend)
- [Full System Integration](#full-system-integration)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Setup

```bash
cd speech-to-text

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 2. Start the Server

```bash
cd src
python main.py
```

Server runs on: **http://localhost:8005**

### 3. Test It Works

```bash
# In another terminal
cd speech-to-text
python3 test_simple.py
```

Speak into your microphone and see the transcription!

---

## API Reference

### Base URL
```
http://localhost:8005
```

### Endpoints

#### 1. Health Check
```http
GET /health
```

**Response** (200 OK):
```json
{
  "status": "healthy",
  "service": "speech-to-text",
  "timestamp": "2025-11-01T15:00:00Z"
}
```

---

#### 2. Start Recording Session
```http
POST /sessions/start
Content-Type: application/json
```

**Request Body** (optional):
```json
{
  "session_id": "custom-session-id"  // Optional: auto-generated if not provided
}
```

**Response** (201 Created):
```json
{
  "session_id": "session-abc123",
  "status": "started",
  "started_at": "2025-11-01T15:00:00Z",
  "config": {
    "chunk_duration": 8,
    "overlap_duration": 1,
    "sample_rate": 16000,
    "channels": 1
  }
}
```

---

#### 3. Stream Transcription (SSE)
```http
GET /sessions/{session_id}/stream
```

**Response** (Server-Sent Events stream):
```
data: {"chunk_id": 0, "text": "Hello world", "timestamp": "2025-11-01T15:00:08Z", "session_id": "session-abc123", "confidence": null}

data: {"chunk_id": 1, "text": "This is a test", "timestamp": "2025-11-01T15:00:16Z", "session_id": "session-abc123", "confidence": null}
```

**Event Format**:
```json
{
  "chunk_id": 0,
  "text": "transcribed text here",
  "timestamp": "2025-11-01T15:00:08Z",
  "session_id": "session-abc123",
  "confidence": null
}
```

**Timing**:
- New chunks arrive every ~8-10 seconds
- Earlier if 2+ seconds of silence detected

---

#### 4. Stop Recording Session
```http
POST /sessions/{session_id}/stop
Content-Type: application/json
```

**Response** (200 OK):
```json
{
  "session_id": "session-abc123",
  "status": "stopped",
  "started_at": "2025-11-01T15:00:00Z",
  "total_duration": 45.2,
  "chunk_count": 5,
  "full_transcript": "Complete transcription of entire session...",
  "chunks": [
    {
      "chunk_id": 0,
      "text": "First chunk",
      "timestamp": "2025-11-01T15:00:08Z",
      "confidence": null
    },
    // ... more chunks
  ]
}
```

---

#### 5. Get Session Info
```http
GET /sessions/{session_id}
```

**Response** (200 OK):
```json
{
  "session_id": "session-abc123",
  "started_at": "2025-11-01T15:00:00Z",
  "status": "active",
  "full_transcript": "Accumulated transcript so far...",
  "chunk_count": 3,
  "total_duration": 24.5
}
```

---

#### 6. List All Sessions
```http
GET /sessions
```

**Response** (200 OK):
```json
{
  "sessions": [
    {
      "session_id": "session-abc123",
      "status": "active",
      "chunk_count": 3,
      "started_at": "2025-11-01T15:00:00Z"
    }
  ],
  "total": 1
}
```

---

#### 7. Upload File for Transcription
```http
POST /transcribe/upload
Content-Type: multipart/form-data
```

**Request**:
```bash
curl -X POST http://localhost:8005/transcribe/upload \
  -F "audio=@recording.wav"
```

**Response** (200 OK):
```json
{
  "text": "Transcribed text from the file",
  "filename": "recording.wav",
  "size_bytes": 245600,
  "timestamp": "2025-11-01T15:00:00Z"
}
```

---

#### 8. Service Statistics
```http
GET /stats
```

**Response** (200 OK):
```json
{
  "transcription": {
    "total_requests": 42,
    "successful_requests": 40,
    "failed_requests": 2,
    "success_rate": "95.2%"
  },
  "sessions": {
    "total_sessions": 5,
    "active_sessions": 1
  },
  "active_recordings": 1,
  "timestamp": "2025-11-01T15:00:00Z"
}
```

---

## Integration with Graph Generation

The graph generation component needs to receive transcript chunks and generate graphs.

### Data Flow

```
Speech-to-Text → Transcript Chunk → Graph Generation → Updated Graph
```

### Backend Integration (Recommended)

Create a backend service that orchestrates both:

**Example** (`backend/orchestrator.py`):
```python
import requests
from flask import Flask, Response
import json

app = Flask(__name__)

STT_URL = "http://localhost:8005"
GRAPH_URL = "http://localhost:8002"  # Graph generation service

@app.route('/brainstorm/start', methods=['POST'])
def start_brainstorm():
    """Start a brainstorming session with both STT and graph generation."""

    # Start STT session
    stt_response = requests.post(f"{STT_URL}/sessions/start")
    session_data = stt_response.json()
    session_id = session_data['session_id']

    # Initialize graph state
    current_graph = None

    # Return session info
    return {
        'session_id': session_id,
        'stt_stream_url': f"{STT_URL}/sessions/{session_id}/stream",
        'status': 'started'
    }

@app.route('/brainstorm/<session_id>/stream')
def stream_brainstorm(session_id):
    """Stream both transcripts and graphs."""

    current_graph = None

    def generate():
        # Connect to STT stream
        stt_stream = requests.get(
            f"{STT_URL}/sessions/{session_id}/stream",
            stream=True
        )

        for line in stt_stream.iter_lines():
            if line.startswith(b'data: '):
                # Parse transcript chunk
                chunk_data = json.loads(line[6:])

                # Send transcript to graph generation
                graph_response = requests.post(
                    f"{GRAPH_URL}/generate-graph",
                    json={
                        'session_id': session_id,
                        'new_text': chunk_data['text'],
                        'previous_graph': current_graph
                    }
                )

                new_graph = graph_response.json()
                current_graph = new_graph

                # Emit both transcript and graph
                yield f"data: {json.dumps({
                    'type': 'transcript',
                    'data': chunk_data
                })}\n\n"

                yield f"data: {json.dumps({
                    'type': 'graph',
                    'data': new_graph
                })}\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(port=8000)
```

### Frontend Integration (Alternative)

Handle orchestration in the frontend:

**Example** (`frontend/lib/brainstorm.ts`):
```typescript
const STT_URL = 'http://localhost:8005';
const GRAPH_URL = 'http://localhost:8002';

export class BrainstormSession {
  sessionId: string;
  currentGraph: any = null;

  async start() {
    // Start STT session
    const response = await fetch(`${STT_URL}/sessions/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    const data = await response.json();
    this.sessionId = data.session_id;

    return this.sessionId;
  }

  async connectStream(onTranscript: (text: string) => void, onGraph: (graph: any) => void) {
    // Connect to STT stream
    const eventSource = new EventSource(
      `${STT_URL}/sessions/${this.sessionId}/stream`
    );

    eventSource.onmessage = async (event) => {
      const chunk = JSON.parse(event.data);

      // Show transcript
      onTranscript(chunk.text);

      // Generate graph
      const graphResponse = await fetch(`${GRAPH_URL}/generate-graph`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: this.sessionId,
          new_text: chunk.text,
          previous_graph: this.currentGraph
        })
      });

      const newGraph = await graphResponse.json();
      this.currentGraph = newGraph;

      // Update graph visualization
      onGraph(newGraph);
    };

    return eventSource;
  }

  async stop() {
    const response = await fetch(
      `${STT_URL}/sessions/${this.sessionId}/stop`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      }
    );

    return await response.json();
  }
}
```

**Usage** (`frontend/components/BrainstormView.tsx`):
```tsx
'use client';

import { useState } from 'react';
import { BrainstormSession } from '@/lib/brainstorm';

export default function BrainstormView() {
  const [session, setSession] = useState<BrainstormSession | null>(null);
  const [transcript, setTranscript] = useState('');
  const [graph, setGraph] = useState(null);

  const startBrainstorming = async () => {
    const newSession = new BrainstormSession();
    await newSession.start();

    newSession.connectStream(
      (text) => setTranscript(prev => prev + ' ' + text),
      (newGraph) => setGraph(newGraph)
    );

    setSession(newSession);
  };

  const stopBrainstorming = async () => {
    if (session) {
      await session.stop();
      setSession(null);
    }
  };

  return (
    <div>
      <button onClick={startBrainstorming}>Start Recording</button>
      <button onClick={stopBrainstorming}>Stop</button>

      <div>
        <h3>Transcript</h3>
        <p>{transcript}</p>
      </div>

      <div>
        <h3>Graph</h3>
        {graph && <GraphVisualization graph={graph} />}
      </div>
    </div>
  );
}
```

---

## Integration with Frontend

### Using EventSource (Server-Sent Events)

**React/Next.js Example**:

```typescript
import { useEffect, useState } from 'react';

export function useTranscription(sessionId: string) {
  const [transcript, setTranscript] = useState<string>('');
  const [chunks, setChunks] = useState<any[]>([]);

  useEffect(() => {
    if (!sessionId) return;

    const eventSource = new EventSource(
      `http://localhost:8005/sessions/${sessionId}/stream`
    );

    eventSource.onmessage = (event) => {
      const chunk = JSON.parse(event.data);

      setChunks(prev => [...prev, chunk]);
      setTranscript(prev => prev + ' ' + chunk.text);
    };

    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [sessionId]);

  return { transcript, chunks };
}
```

**Usage**:
```tsx
function BrainstormPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const { transcript, chunks } = useTranscription(sessionId);

  const startRecording = async () => {
    const response = await fetch('http://localhost:8005/sessions/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    const data = await response.json();
    setSessionId(data.session_id);
  };

  return (
    <div>
      <button onClick={startRecording}>Start</button>
      <p>{transcript}</p>
    </div>
  );
}
```

---

## Full System Integration

### Architecture

```
┌─────────────┐
│   Browser   │
│  (Frontend) │
└──────┬──────┘
       │
       ├──────────────────────────────────┐
       │                                  │
       ▼                                  ▼
┌──────────────┐                  ┌──────────────┐
│ Speech-to-   │  Transcript      │    Graph     │
│    Text      │─────────────────▶│  Generation  │
│ :8005        │                  │   :8002      │
└──────────────┘                  └──────┬───────┘
                                         │
                                         ▼
                                  ┌──────────────┐
                                  │  Updated     │
                                  │   Graph      │
                                  └──────────────┘
```

### Complete Flow

1. **User clicks "Start Brainstorming"**
   ```
   Frontend → POST /sessions/start → STT Service
   ```

2. **STT starts recording and streaming**
   ```
   Frontend ← SSE stream ← GET /sessions/{id}/stream
   ```

3. **Every 8-10 seconds: New transcript chunk**
   ```
   Frontend receives: {text: "new text", chunk_id: 0}
   ```

4. **Frontend sends to graph generation**
   ```
   Frontend → POST /generate-graph → Graph Service
   Body: {new_text: "new text", previous_graph: {...}}
   ```

5. **Graph service returns updated graph**
   ```
   Frontend ← {nodes: [...], edges: [...]}
   ```

6. **Frontend updates visualization**
   ```
   React component re-renders with new graph
   ```

7. **Repeat steps 3-6 until session ends**

8. **User clicks "Stop"**
   ```
   Frontend → POST /sessions/{id}/stop → STT Service
   Frontend ← {full_transcript: "...", chunks: [...]}
   ```

### Environment Variables

**Speech-to-Text** (`.env`):
```env
OPENAI_API_KEY=sk-your-key
PORT=8005
CORS_ORIGINS=http://localhost:3005,http://localhost:3000
```

**Graph Generation** (`.env`):
```env
ANTHROPIC_API_KEY=sk-ant-your-key
PORT=8002
CORS_ORIGINS=http://localhost:3005,http://localhost:3000
```

**Frontend** (`.env.local`):
```env
NEXT_PUBLIC_STT_API=http://localhost:8005
NEXT_PUBLIC_GRAPH_API=http://localhost:8002
```

---

## Troubleshooting

### Issue: "Cannot connect to server"
**Solution**:
```bash
# Check if server is running
curl http://localhost:8005/health

# If not, start it:
cd speech-to-text/src && python main.py
```

### Issue: "Port already in use"
**Solution**: Change port in `.env`:
```env
PORT=8006  # Use different port
```

### Issue: "No audio detected"
**Solution**:
```bash
# Test microphone
cd speech-to-text/src
python audio_capture.py

# Check volume levels
```

### Issue: "Empty transcriptions"
**Solution**:
- Speak louder and clearer
- Check microphone permissions
- Verify API key is valid

### Issue: "CORS errors in browser"
**Solution**: Add your frontend URL to `.env`:
```env
CORS_ORIGINS=http://localhost:3005,http://localhost:3000
```

### Issue: "Transcription too slow"
**Solution**: Already optimized! But if needed:
- Reduce chunk duration in `.env`: `CHUNK_DURATION_SECONDS=6`
- Use faster internet connection
- OpenAI API is usually ~1-2 seconds

### Issue: "Duplicate words in transcript"
**Solution**: Already handled by deduplication! If still seeing issues:
- Check `OVERLAP_DURATION_SECONDS` in `.env`
- Should be 1 second (default)

---

## Performance Tips

### Cost Optimization
- Current setup: ~$0.54 per 30-minute session
- Already very cheap!
- No optimization needed for hackathon

### Speed Optimization
- Already optimized for real-time
- 8-10 second updates are perfect
- Don't reduce chunk duration (quality will suffer)

### Quality Optimization
- Speak clearly at normal volume
- Reduce background noise
- Use good microphone if available
- Current setup already uses best Whisper model

---

## Next Steps

1. ✅ Test speech-to-text standalone
2. ⏭️ Build graph-generation component
3. ⏭️ Build frontend
4. ⏭️ Integrate all three
5. 🎉 Demo!

---

## Questions?

- Check `README.md` for setup
- Check `QUICKSTART.md` for 5-minute guide
- Check `../docs/architecture.md` for system design
- Check `../docs/integration.md` for overall integration

**API Endpoint Summary**:
```
GET    /health                    - Health check
POST   /sessions/start            - Start recording
GET    /sessions/{id}/stream      - Stream transcripts (SSE)
POST   /sessions/{id}/stop        - Stop recording
GET    /sessions/{id}             - Get session info
GET    /sessions                  - List sessions
POST   /transcribe/upload         - Upload audio file
GET    /stats                     - Service statistics
```

Happy coding! 🎤🚀
