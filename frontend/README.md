# Frontend Component

Interactive web interface for visualizing and controlling the brainstorming graph.

## Responsibility

- Display live, updating knowledge graph
- Provide controls for starting/stopping sessions
- Show transcript alongside visualization
- Enable user interaction (zoom, pan, select nodes)
- Export graph and transcript

## Tech Stack

**Recommended**: Next.js + React + TypeScript

**Graph Visualization Library Options**:
1. **React Flow** - Easy, good for interactive graphs, well-documented
2. **D3.js** - Maximum flexibility, steeper learning curve
3. **Cytoscape.js** - Powerful, good for complex graphs
4. **vis-network** - Simple setup, good defaults

**Recommendation for Hackathon**: **React Flow** (easiest to get started, great UX)

## Setup

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --app --no-src-dir
npm install
```

### Additional Dependencies

```bash
# For React Flow (recommended)
npm install reactflow

# For state management
npm install zustand

# For API calls
npm install axios

# For animations
npm install framer-motion
```

### Configuration

Create `.env.local`:

```env
NEXT_PUBLIC_STT_API_URL=http://localhost:8001
NEXT_PUBLIC_GRAPH_API_URL=http://localhost:8002
```

## Development

### Project Structure

```
frontend/
├── app/
│   ├── page.tsx              # Main brainstorming interface
│   ├── layout.tsx            # Root layout
│   └── globals.css           # Global styles
├── components/
│   ├── GraphVisualization.tsx    # Main graph component
│   ├── TranscriptPanel.tsx       # Transcript display
│   ├── ControlPanel.tsx          # Start/stop controls
│   ├── NodeDetail.tsx            # Node info popup
│   └── ExportButton.tsx          # Export functionality
├── lib/
│   ├── api.ts                # API client functions
│   ├── store.ts              # Zustand state management
│   └── graph-utils.ts        # Graph transformation utilities
├── types/
│   ├── graph.ts              # TypeScript types for graph
│   └── transcript.ts         # TypeScript types for transcript
└── public/
```

### Running Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Implementation Guide

### Step 1: Define TypeScript Types

Create `types/graph.ts`:

```typescript
export interface Node {
  id: string;
  label: string;
  type: 'concept' | 'topic' | 'decision' | 'question' | 'action' | 'person';
  description?: string;
  importance: number;
  confidence: number;
  color: string;
  metadata?: {
    tags?: string[];
    mentions_count?: number;
  };
}

export interface Edge {
  id: string;
  source: string;
  target: string;
  type: string;
  label?: string;
  strength: number;
  confidence: number;
}

export interface Graph {
  session_id: string;
  version: number;
  timestamp: string;
  nodes: Node[];
  edges: Edge[];
  metadata: {
    summary?: string;
    main_themes?: string[];
    layout_hint?: string;
  };
}
```

### Step 2: State Management

Create `lib/store.ts`:

```typescript
import { create } from 'zustand';
import { Graph } from '@/types/graph';

interface AppState {
  sessionId: string | null;
  isRecording: boolean;
  currentGraph: Graph | null;
  transcript: string;

  startSession: () => void;
  stopSession: () => void;
  updateGraph: (graph: Graph) => void;
  appendTranscript: (text: string) => void;
}

export const useStore = create<AppState>((set) => ({
  sessionId: null,
  isRecording: false,
  currentGraph: null,
  transcript: '',

  startSession: () => {
    const sessionId = `session-${Date.now()}`;
    set({ sessionId, isRecording: true, transcript: '', currentGraph: null });
  },

  stopSession: () => {
    set({ isRecording: false });
  },

  updateGraph: (graph) => {
    set({ currentGraph: graph });
  },

  appendTranscript: (text) => {
    set((state) => ({ transcript: state.transcript + ' ' + text }));
  },
}));
```

### Step 3: API Client

Create `lib/api.ts`:

```typescript
import axios from 'axios';
import { Graph } from '@/types/graph';

const STT_API = process.env.NEXT_PUBLIC_STT_API_URL;
const GRAPH_API = process.env.NEXT_PUBLIC_GRAPH_API_URL;

export async function startTranscription(sessionId: string) {
  await axios.post(`${STT_API}/transcribe/start`, { session_id: sessionId });
}

export async function stopTranscription(sessionId: string) {
  await axios.post(`${STT_API}/transcribe/stop`, { session_id: sessionId });
}

export async function generateGraph(
  sessionId: string,
  newText: string,
  previousGraph: Graph | null
): Promise<Graph> {
  const response = await axios.post(`${GRAPH_API}/generate-graph`, {
    session_id: sessionId,
    new_text: newText,
    previous_graph: previousGraph,
  });
  return response.data;
}
```

### Step 4: Graph Visualization Component

Create `components/GraphVisualization.tsx` (using React Flow):

```typescript
'use client';

import { useCallback, useEffect } from 'react';
import ReactFlow, {
  Node as FlowNode,
  Edge as FlowEdge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Graph } from '@/types/graph';

interface Props {
  graph: Graph | null;
}

export default function GraphVisualization({ graph }: Props) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    if (!graph) return;

    // Transform graph nodes to React Flow format
    const flowNodes: FlowNode[] = graph.nodes.map((node, index) => ({
      id: node.id,
      type: 'default',
      data: {
        label: node.label,
        description: node.description,
      },
      position: node.position || {
        x: Math.random() * 500,
        y: Math.random() * 500
      }, // Auto-layout in production
      style: {
        background: node.color,
        color: '#fff',
        border: '2px solid #222',
        borderRadius: '8px',
        padding: '10px',
        fontSize: `${12 + node.importance * 8}px`,
        fontWeight: node.importance > 0.7 ? 'bold' : 'normal',
      },
    }));

    // Transform edges
    const flowEdges: FlowEdge[] = graph.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.label,
      type: 'smoothstep',
      style: {
        strokeWidth: 1 + edge.strength * 3,
        stroke: '#94a3b8',
      },
      labelStyle: {
        fontSize: '10px',
        fill: '#64748b',
      },
    }));

    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [graph, setNodes, setEdges]);

  return (
    <div style={{ width: '100%', height: '600px' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}
```

### Step 5: Main Page

Create `app/page.tsx`:

```typescript
'use client';

import { useEffect } from 'react';
import { useStore } from '@/lib/store';
import { startTranscription, stopTranscription, generateGraph } from '@/lib/api';
import GraphVisualization from '@/components/GraphVisualization';
import TranscriptPanel from '@/components/TranscriptPanel';
import ControlPanel from '@/components/ControlPanel';

export default function Home() {
  const {
    sessionId,
    isRecording,
    currentGraph,
    transcript,
    startSession,
    stopSession,
    updateGraph,
    appendTranscript,
  } = useStore();

  // Handle transcript stream
  useEffect(() => {
    if (!isRecording || !sessionId) return;

    const eventSource = new EventSource(
      `${process.env.NEXT_PUBLIC_STT_API_URL}/transcribe/stream?session_id=${sessionId}`
    );

    eventSource.onmessage = async (event) => {
      const chunk = JSON.parse(event.data);
      appendTranscript(chunk.text);

      // Generate updated graph
      try {
        const newGraph = await generateGraph(
          sessionId,
          chunk.text,
          currentGraph
        );
        updateGraph(newGraph);
      } catch (error) {
        console.error('Failed to generate graph:', error);
      }
    };

    return () => {
      eventSource.close();
    };
  }, [isRecording, sessionId, currentGraph]);

  const handleStart = async () => {
    startSession();
    const newSessionId = `session-${Date.now()}`;
    await startTranscription(newSessionId);
  };

  const handleStop = async () => {
    if (sessionId) {
      await stopTranscription(sessionId);
    }
    stopSession();
  };

  return (
    <main className="min-h-screen p-8">
      <h1 className="text-4xl font-bold mb-8">Brainstorm Graph</h1>

      <ControlPanel
        isRecording={isRecording}
        onStart={handleStart}
        onStop={handleStop}
      />

      <div className="grid grid-cols-3 gap-8 mt-8">
        <div className="col-span-2">
          <GraphVisualization graph={currentGraph} />
        </div>

        <div className="col-span-1">
          <TranscriptPanel transcript={transcript} />
        </div>
      </div>
    </main>
  );
}
```

## Features to Implement

### Phase 1: Core Functionality
- [x] Project setup
- [ ] Basic graph visualization
- [ ] Connect to STT API
- [ ] Connect to Graph API
- [ ] Real-time updates
- [ ] Start/stop controls

### Phase 2: Enhanced UX
- [ ] Smooth graph transitions
- [ ] Node click for details
- [ ] Search/filter nodes
- [ ] Layout algorithms (auto-arrange)
- [ ] Color themes

### Phase 3: Polish
- [ ] Export to PNG/SVG
- [ ] Export transcript
- [ ] Session history
- [ ] Responsive design
- [ ] Loading states
- [ ] Error handling

## Graph Layout Strategies

### Auto-Layout with React Flow

React Flow has built-in layouts. For better results:

```bash
npm install dagre  # For hierarchical layout
npm install elkjs  # For auto-layout
```

Example with dagre:

```typescript
import dagre from 'dagre';

function getLayoutedElements(nodes, edges) {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: 'TB' });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 150, height: 50 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x,
        y: nodeWithPosition.y,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}
```

## Smooth Transitions

Use position interpolation for smooth updates:

```typescript
import { useSpring, animated } from 'framer-motion';

// In your node component
const x = useSpring(node.position.x);
const y = useSpring(node.position.y);
```

## Styling Tips

### Tailwind Classes

```typescript
// Control panel
className="bg-white rounded-lg shadow-lg p-6"

// Graph container
className="border border-gray-200 rounded-lg overflow-hidden shadow-xl"

// Transcript panel
className="bg-gray-50 rounded-lg p-4 h-full overflow-y-auto"
```

## Testing

### Component Testing

```bash
npm install --save-dev @testing-library/react @testing-library/jest-dom
```

### E2E Testing (Optional)

```bash
npm install --save-dev @playwright/test
```

## Deployment

### Deploy to Vercel

```bash
npm install -g vercel
vercel
```

Or connect GitHub repo to Vercel for auto-deployment.

### Environment Variables

Add to Vercel:
- `NEXT_PUBLIC_STT_API_URL`
- `NEXT_PUBLIC_GRAPH_API_URL`

## Common Issues

**Issue**: Graph doesn't update smoothly
- **Solution**: Maintain node positions, only animate new nodes
- **Solution**: Use `useTransition` from React

**Issue**: API calls failing
- **Solution**: Check CORS settings on backend
- **Solution**: Verify environment variables

**Issue**: Performance issues with large graphs
- **Solution**: Use React Flow's viewport limits
- **Solution**: Implement node pruning
- **Solution**: Use virtualization for transcript

## Resources

- [React Flow Documentation](https://reactflow.dev/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Zustand State Management](https://docs.pmnd.rs/zustand)
- Graph schema: `../docs/graph-schema.md`

## Support

Questions? Check:
- `../docs/integration.md` for API integration
- `../docs/architecture.md` for system overview
- `../shared/examples/` for sample data format
- `../CLAUDE.md` for project context
