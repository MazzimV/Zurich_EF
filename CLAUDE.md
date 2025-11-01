# Claude Code Context

This file helps AI assistants understand the project structure and current state.

## Project Summary

Real-time brainstorming tool that converts speech to knowledge graphs. Three independent components work together to capture audio, generate graphs, and visualize results.

## Current State

**Status**: Initial setup - documentation and structure only, no code yet

**Teams**:
- Speech-to-Text: Building audio capture and transcription
- Graph Generation: Building LLM-based graph generation
- Frontend: Not started yet (Next.js planned)

## Architecture

### Data Flow
```
Audio Input → Speech-to-Text → Transcript JSON
                                     ↓
                     Graph Generation (LLM) ← Previous Graph
                                     ↓
                               New Graph JSON
                                     ↓
                              Frontend Display
```

### Update Cycle
- Every 5-10 seconds: new transcript chunk is sent to graph generator
- Graph generator receives: new text + previous graph
- LLM outputs: complete new graph with UI metadata
- Frontend applies smooth transitions

## Key Technical Decisions

1. **Full Graph Replacement**: LLM outputs complete graph each time (not deltas)
2. **Stable Node IDs**: Graph must maintain consistent IDs for smooth UI transitions
3. **Rich Metadata**: JSON includes colors, sizes, positions, importance scores
4. **Single Transcript**: One merged transcript (not per-speaker initially)
5. **LLM Freedom**: Graph generation has creative control over structure

## Component Contracts

### Speech-to-Text Output
```json
{
  "timestamp": "ISO-8601",
  "text": "new transcript segment",
  "session_id": "unique-id"
}
```

### Graph Generation Input
```json
{
  "new_text": "latest transcript chunk",
  "previous_graph": { /* full graph object */ },
  "session_id": "unique-id"
}
```

### Graph Generation Output
See `shared/schemas/graph.json` for complete schema

## File Organization

- `speech-to-text/`: Python, isolated STT logic
- `graph-generation/`: Python + LLM API, isolated graph logic
- `frontend/`: Next.js, consumes JSON only
- `shared/`: Schema definitions and test data
- `docs/`: Design documentation

## Development Priorities

1. Get each component working independently
2. Validate against shared schemas
3. Test with sample data from `shared/examples/`
4. Integrate components
5. Polish UI/UX

## Open Questions

- [ ] Which STT service to use?
- [ ] Which LLM for graph generation?
- [ ] Graph visualization library choice?
- [ ] WebSocket vs polling for real-time updates?
- [ ] Session persistence strategy?

## Recent Changes

- Initial project structure created
- Documentation scaffolded
- Schemas defined

## Next Steps

1. Speech-to-Text team: Implement basic transcription
2. Graph Generation team: Create initial LLM prompt and test with sample data
3. Define exact JSON schemas based on early prototypes
4. Frontend team: Set up Next.js and choose graph library

## Useful Commands

(To be added as development progresses)

## Notes for AI Assistants

- This is a hackathon project - prioritize speed and core functionality
- Teams work independently - maintain clear contracts via JSON schemas
- Graph generation is the "magic" - give LLM maximum creative freedom
- UI/UX is the differentiator - visualization quality matters
- Keep complexity low, focus on the core experience
