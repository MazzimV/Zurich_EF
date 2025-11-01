# Brainstorm Graph

Real-time brainstorming visualization tool that converts spoken discussions into dynamic knowledge graphs.

## Overview

This tool listens to conversations, transcribes them in real-time, and generates a live, evolving graph that visualizes concepts, relationships, and the flow of discussion. Perfect for team brainstorming sessions, meetings, and collaborative thinking.

## How It Works

1. **Speech-to-Text**: Captures audio and converts it to text transcripts
2. **Graph Generation**: LLM processes transcript increments to generate/update a graph (nodes, edges, metadata)
3. **Live Visualization**: Interactive UI displays the graph with smooth updates every 5-10 seconds

## Project Structure

```
brainstorm-graph/
├── speech-to-text/       # Audio capture & transcription
├── graph-generation/     # LLM-based graph generation from text
├── frontend/             # Next.js UI for visualization
├── shared/               # Common schemas and examples
└── docs/                 # Architecture & integration docs
```

## Team Assignments

- **Speech-to-Text Team**: `speech-to-text/` directory
- **Graph Generation Team**: `graph-generation/` directory
- **Frontend Team**: `frontend/` directory (coming soon)

## Quick Start

Each component has its own README with setup instructions:
- [Speech-to-Text Setup](./speech-to-text/README.md)
- [Graph Generation Setup](./graph-generation/README.md)
- [Frontend Setup](./frontend/README.md)

## Development Workflow

1. Teams work independently in their directories
2. Use schemas in `shared/schemas/` for data contracts
3. Test integration using examples in `shared/examples/`
4. See `docs/integration.md` for how components connect

## Key Design Decisions

- **Update Pattern**: New transcript chunk + old graph → new graph (every 5-10 seconds)
- **LLM Freedom**: Graph generation LLM has creative freedom to design the graph
- **JSON-Based**: All data exchange via JSON (see schemas)
- **Real-time First**: Focus on smooth, live updates

## Documentation

- [Architecture Overview](./docs/architecture.md)
- [Graph Schema](./docs/graph-schema.md)
- [Integration Guide](./docs/integration.md)
- [CLAUDE.md](./CLAUDE.md) - AI development context

## Tech Stack

- **Speech-to-Text**: Python (Whisper, OpenAI API, or similar)
- **Graph Generation**: Python + LLM API (Claude, GPT-4, etc.)
- **Frontend**: Next.js + React + D3.js/React Flow/Cytoscape
- **Data Format**: JSON

## Getting Started

1. Clone this repository
2. Each team: navigate to your directory and follow the README
3. Use the shared schemas to ensure compatibility
4. Test with the sample data in `shared/examples/`

## Contributing

This is a hackathon project. Keep it simple, move fast, and focus on the core experience!

## License

MIT
