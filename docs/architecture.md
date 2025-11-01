# Architecture Overview

## System Design

The Brainstorm Graph system consists of three independent components that communicate via JSON:

```
┌─────────────────┐
│  Audio Input    │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  Speech-to-Text     │
│  Component          │
└────────┬────────────┘
         │ Transcript JSON
         │ (every 5-10s)
         ▼
┌─────────────────────┐      ┌──────────────────┐
│  Graph Generation   │◄─────│  Previous Graph  │
│  Component (LLM)    │      │  State           │
└────────┬────────────┘      └──────────────────┘
         │ New Graph JSON
         │
         ▼
┌─────────────────────┐
│  Frontend           │
│  Visualization      │
└─────────────────────┘
```

## Components

### 1. Speech-to-Text Component
**Responsibility**: Capture audio and convert to text

**Input**: Audio stream (microphone or file)

**Output**: JSON transcript chunks
```json
{
  "timestamp": "2025-11-01T10:30:45Z",
  "text": "So I think we should focus on the user experience",
  "session_id": "session-123",
  "chunk_id": 42
}
```

**Technology**: Python + STT API (Whisper, Deepgram, etc.)

**Key Requirements**:
- Real-time processing
- Emit chunks every 5-10 seconds
- Handle pauses in speech
- Maintain session continuity

### 2. Graph Generation Component
**Responsibility**: Transform transcript into knowledge graph

**Input**: New transcript + previous graph state
```json
{
  "new_text": "recent transcript chunk",
  "previous_graph": { /* full graph */ },
  "session_id": "session-123"
}
```

**Output**: Complete new graph with UI metadata
```json
{
  "nodes": [...],
  "edges": [...],
  "metadata": {...}
}
```

**Technology**: Python + LLM API (Claude, GPT-4, etc.)

**Key Requirements**:
- Fast response (<2-3 seconds)
- Maintain node ID stability
- Merge new concepts with existing graph
- Generate rich UI metadata (colors, sizes, positions)
- Handle context window limits

### 3. Frontend Component
**Responsibility**: Visualize and interact with the graph

**Input**: Graph JSON from generation component

**Output**: Interactive visualization

**Technology**: Next.js + React + Graph library (D3.js/React Flow/Cytoscape)

**Key Requirements**:
- Smooth transitions between graph states
- Real-time updates without jarring jumps
- Interactive controls (zoom, pan, select)
- Export capabilities
- Session management

## Data Flow

### Initialization
1. User starts a session
2. Frontend creates session ID
3. Speech-to-Text begins capturing audio
4. Graph starts empty

### Update Cycle (every 5-10 seconds)
1. STT emits new transcript chunk
2. Frontend/Backend sends to Graph Generation:
   - New text chunk
   - Current graph state
3. LLM processes and returns new complete graph
4. Frontend applies new graph with smooth transitions
5. Repeat

### Session End
1. User stops recording
2. Final transcript chunk processed
3. Final graph generated
4. Export options available

## Component Communication

### Option A: Direct API Calls
```
Frontend ←→ Graph Generation API ←→ LLM
    ↑
    └─ Speech-to-Text API
```

### Option B: Message Queue (if needed)
```
Frontend → Message Queue ← Graph Generation
    ↑                          ↑
    └─ Speech-to-Text ─────────┘
```

For hackathon: **Option A** (simpler, direct HTTP/WebSocket)

## State Management

### Session State
```json
{
  "session_id": "unique-id",
  "started_at": "timestamp",
  "full_transcript": "accumulated text...",
  "current_graph": { /* latest graph */ },
  "history": [ /* previous graphs */ ]
}
```

### Storage Strategy
- **In-memory**: For hackathon, keep state in backend
- **Future**: Redis/database for persistence

## Scalability Considerations

For hackathon scope:
- Single user session at a time
- In-memory state
- Direct API calls

Future improvements:
- Multi-user sessions
- WebSocket for real-time push
- State persistence
- Replay functionality

## Error Handling

### STT Failures
- Buffer audio and retry
- Show "reconnecting" in UI

### Graph Generation Failures
- Keep previous graph
- Retry with backoff
- Show error state in UI

### Frontend Issues
- Cache last N graphs for recovery
- Graceful degradation

## Performance Targets

- STT latency: <1 second
- Graph generation: <3 seconds
- UI update: <100ms (smooth transition)
- Total cycle: 5-10 seconds

## Security Considerations

For hackathon:
- API keys in environment variables
- CORS configuration
- Basic session validation

Future:
- Authentication
- Rate limiting
- Audio data privacy
