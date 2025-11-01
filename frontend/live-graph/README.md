# Live Graph Visualization

Real-time force-directed network graph visualization for the brainstorm tool.

## Overview

This frontend component visualizes knowledge graphs from the orchestrator service using D3.js force simulation. It supports:

- **Real-time updates**: Smooth transitions as graph evolves
- **Interactive nodes**: Drag, zoom, and pan
- **Transcript display**: Shows conversation alongside graph
- **Node sizing**: Based on importance scores
- **Edge styling**: Thickness based on relationship strength

## Quick Start

### Test Mode (No Backend Required)

Open `index.html` in a browser to test with static data and mock updates:

```bash
# From the live-graph directory
open index.html
# or
python3 -m http.server 8080
# Then visit http://localhost:8080
```

### Test 1: Static Graph

Click "Test 1: Load Static Graph" to:
- Load a pre-saved graph from `test-data/static-graph.json`
- Render 5 nodes with 4 edges
- Display sample transcript

**Expected Result**: Graph renders with nodes positioned by force simulation.

### Test 2: Mock Updates

Click "Test 2: Start Mock Updates" to:
- Simulate SSE stream with 3 incremental updates
- Updates arrive every 3 seconds
- New nodes/edges appear with smooth transitions
- Existing nodes update (size, label, importance)

**Expected Result**:
- Update 1: Initial 5 nodes
- Update 2: +2 nodes (React Native, Cross-Platform Development)
- Update 3: +1 node (iOS Priority), label refinement on "Device Testing"

### Test Controls

- **Stop Mock Updates**: Pause the mock SSE stream
- **Clear All**: Reset graph and transcript
- **Reset Zoom**: Re-center graph view

## Architecture

### Components

**GraphRenderer** (`js/graph-renderer.js`)
- D3 force simulation configuration
- Node/edge rendering with enter/update/exit patterns
- Drag, zoom, and pan interactions
- Smooth transitions for all changes

**TranscriptDisplay** (`js/transcript-display.js`)
- Scrollable transcript panel
- Speaker labels and timestamps
- Auto-scroll to latest chunk

### Data Flow

```
Static JSON or Mock Updates
         ↓
   GraphRenderer.updateGraph()
         ↓
   D3 Data Join (key function by node.id)
         ↓
   Enter/Update/Exit with transitions
         ↓
   Force simulation positions nodes
```

### Key Features

**1. Stable Node IDs**
- Data joins use `.data(nodes, d => d.id)` for identity
- Existing nodes keep positions and velocities
- New nodes enter with fade-in animation

**2. Smooth Transitions**
- All property changes use `.transition().duration(500)`
- Node radius, color, and labels animate
- Edge thickness and opacity animate

**3. Force Simulation**
- `forceLink`: Connects related nodes (shorter = stronger edge)
- `forceManyBody`: Node repulsion (-300 strength)
- `forceCenter`: Keeps graph centered
- `forceCollide`: Prevents node overlap

**4. Interactive Controls**
- **Drag nodes**: Click and drag to reposition
- **Zoom/Pan**: Mouse wheel to zoom, drag background to pan
- **Hover**: Tooltip shows node details

## File Structure

```
live-graph/
├── index.html              # Main test page
├── css/
│   └── style.css          # All styles
├── js/
│   ├── graph-renderer.js  # D3 force-directed graph
│   └── transcript-display.js  # Transcript panel
└── test-data/
    ├── static-graph.json  # Sample graph for Test 1
    └── mock-updates.js    # Simulated SSE for Test 2
```

## Connecting to Live Orchestrator

To connect to the real orchestrator SSE stream (not implemented in this test version):

```javascript
// Create SSE connection to orchestrator
const eventSource = new EventSource('http://localhost:8003/sessions/{session_id}/stream');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  // Update graph
  graphRenderer.updateGraph(data.graph);

  // Add transcript
  transcriptDisplay.addChunk({
    text: data.transcript.text,
    speaker: data.transcript.speaker,
    timestamp: data.timestamp,
    chunk_id: data.chunk_id
  });
};

eventSource.onerror = (error) => {
  console.error('SSE connection error:', error);
  eventSource.close();
};
```

## Graph Data Format

Expected input format from orchestrator:

```json
{
  "session_id": "session-123",
  "version": 2,
  "timestamp": "2025-11-01T10:00:00Z",
  "nodes": [
    {
      "id": "node-1",
      "label": "Mobile App",
      "type": "topic",
      "importance": 0.9,
      "color": "#8B5CF6",
      "description": "..."
    }
  ],
  "edges": [
    {
      "id": "edge-1",
      "source": "node-1",
      "target": "node-2",
      "type": "relates_to",
      "strength": 0.8
    }
  ],
  "metadata": {
    "summary": "...",
    "main_themes": ["..."]
  }
}
```

## Node Types and Colors

| Type     | Color     | Use Case                    |
|----------|-----------|-----------------------------|
| topic    | `#8B5CF6` | Main discussion topics      |
| concept  | `#10B981` | Ideas and concepts          |
| action   | `#F59E0B` | Action items and tasks      |
| decision | `#3B82F6` | Decisions made              |
| question | `#EF4444` | Open questions              |
| person   | `#EC4899` | People mentioned            |

## Customization

### Adjust Force Simulation

```javascript
const graphRenderer = new GraphRenderer('graph-canvas', {
  width: 1200,
  height: 800,
  nodeRadiusScale: [8, 35],    // Min/max node size
  edgeWidthScale: [1, 5]       // Min/max edge thickness
});

// Modify forces
graphRenderer.simulation
  .force('charge', d3.forceManyBody().strength(-500))  // Stronger repulsion
  .force('link', d3.forceLink().distance(150));        // Longer edges
```

### Transcript Options

```javascript
const transcriptDisplay = new TranscriptDisplay('transcript-display', {
  maxChunks: 50,        // Limit displayed chunks
  autoScroll: true      // Auto-scroll to latest
});
```

## Browser Compatibility

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

Requires modern browser with ES6+ support and SVG rendering.

## Troubleshooting

**Graph not appearing:**
- Check browser console for errors
- Ensure D3.js loaded: `console.log(d3.version)`
- Verify graph data has `nodes` array

**Nodes overlapping:**
- Increase collision force radius
- Decrease node importance scale
- Increase canvas size

**Slow performance:**
- Limit max nodes to 50
- Reduce simulation complexity
- Disable transitions during updates

## Next Steps

1. ✅ Test 1: Static graph rendering
2. ✅ Test 2: Mock SSE updates with transitions
3. ⏳ Test 3: Connect to live orchestrator SSE stream
4. ⏳ Add session management UI (start/stop)
5. ⏳ Add graph export (PNG, JSON)
6. ⏳ Add node filtering and search
7. ⏳ Add edge labels and tooltips
8. ⏳ Optimize for large graphs (100+ nodes)

## Development

No build process required - pure HTML/CSS/JS.

Edit files and refresh browser to see changes.

Use browser dev tools to inspect:
- Graph data: `graphRenderer.getStats()`
- Transcript data: `transcriptDisplay.getStats()`
- D3 selections: `graphRenderer.nodeSelection`, `graphRenderer.linkSelection`
