# Graph Schema Documentation

## Overview

The graph is represented as a JSON object with nodes, edges, and metadata. The LLM has freedom to decide structure, but must follow this schema for UI compatibility.

## Core Principles

1. **Stable IDs**: Node and edge IDs must persist across updates
2. **Rich Metadata**: Include visual hints for better UX
3. **Semantic Depth**: Nodes can have types, importance, and relationships
4. **UI-Friendly**: Schema designed for direct consumption by visualization libraries

## Graph Object Structure

```json
{
  "session_id": "string",
  "version": "integer",
  "timestamp": "ISO-8601 string",
  "nodes": [ /* array of nodes */ ],
  "edges": [ /* array of edges */ ],
  "metadata": { /* graph-level metadata */ }
}
```

## Node Schema

```json
{
  "id": "string (stable, unique)",
  "label": "string (display text)",
  "type": "string (concept|topic|decision|question|action|person)",
  "description": "string (optional, fuller explanation)",
  "importance": "number (0-1, affects size)",
  "confidence": "number (0-1, how certain is this node)",
  "created_at": "ISO-8601 string",
  "updated_at": "ISO-8601 string",
  "color": "string (hex color or category)",
  "size": "number (optional, override importance)",
  "position": {
    "x": "number (optional hint)",
    "y": "number (optional hint)"
  },
  "metadata": {
    "tags": ["array", "of", "strings"],
    "mentions_count": "integer",
    "related_timestamps": ["array of transcript timestamps"]
  }
}
```

### Node Types

- **concept**: Abstract ideas or themes
- **topic**: Specific subjects being discussed
- **decision**: Concrete decisions made
- **question**: Unresolved questions
- **action**: Action items or next steps
- **person**: Referenced people or stakeholders

### Node Importance

0.0-0.3: Minor mention
0.3-0.6: Regular topic
0.6-0.9: Major theme
0.9-1.0: Central concept

## Edge Schema

```json
{
  "id": "string (stable, unique)",
  "source": "string (node id)",
  "target": "string (node id)",
  "type": "string (relates_to|causes|supports|contradicts|follows)",
  "label": "string (optional, relationship description)",
  "strength": "number (0-1, affects visual weight)",
  "confidence": "number (0-1)",
  "created_at": "ISO-8601 string",
  "metadata": {
    "reason": "string (why this connection exists)"
  }
}
```

### Edge Types

- **relates_to**: General relationship
- **causes**: Causal relationship (A→B)
- **supports**: One concept supports another
- **contradicts**: Concepts in tension
- **follows**: Temporal or logical sequence
- **elaborates**: One concept expands on another

### Edge Strength

0.0-0.3: Weak connection
0.3-0.7: Moderate connection
0.7-1.0: Strong connection

## Graph Metadata

```json
{
  "summary": "string (brief overview of discussion)",
  "main_themes": ["array", "of", "central", "themes"],
  "participant_count": "integer",
  "duration_seconds": "integer",
  "graph_complexity": "number (0-1)",
  "layout_hint": "string (force|hierarchical|radial|timeline)"
}
```

### Layout Hints

Suggest to UI how to arrange the graph:
- **force**: Force-directed (default)
- **hierarchical**: Top-down or left-right tree
- **radial**: Central concept with radiating nodes
- **timeline**: Chronological left-to-right

## Color Scheme Suggestions

The LLM can use semantic colors:

```json
{
  "concept": "#3B82F6",      // blue
  "topic": "#8B5CF6",        // purple
  "decision": "#10B981",     // green
  "question": "#F59E0B",     // amber
  "action": "#EF4444",       // red
  "person": "#6366F1"        // indigo
}
```

Or generate custom colors based on semantic clustering.

## Example: Simple Graph

```json
{
  "session_id": "demo-123",
  "version": 5,
  "timestamp": "2025-11-01T10:35:00Z",
  "nodes": [
    {
      "id": "node-1",
      "label": "User Experience",
      "type": "topic",
      "description": "Focus on improving the overall user experience",
      "importance": 0.9,
      "confidence": 0.95,
      "created_at": "2025-11-01T10:30:00Z",
      "updated_at": "2025-11-01T10:35:00Z",
      "color": "#8B5CF6",
      "metadata": {
        "tags": ["UX", "design", "priority"],
        "mentions_count": 3
      }
    },
    {
      "id": "node-2",
      "label": "Mobile Responsiveness",
      "type": "concept",
      "description": "Ensure the app works well on mobile devices",
      "importance": 0.7,
      "confidence": 0.8,
      "created_at": "2025-11-01T10:33:00Z",
      "updated_at": "2025-11-01T10:35:00Z",
      "color": "#3B82F6",
      "metadata": {
        "tags": ["mobile", "responsive"],
        "mentions_count": 2
      }
    },
    {
      "id": "node-3",
      "label": "Test on different devices",
      "type": "action",
      "importance": 0.6,
      "confidence": 0.9,
      "created_at": "2025-11-01T10:35:00Z",
      "updated_at": "2025-11-01T10:35:00Z",
      "color": "#EF4444",
      "metadata": {
        "tags": ["testing", "todo"],
        "mentions_count": 1
      }
    }
  ],
  "edges": [
    {
      "id": "edge-1",
      "source": "node-2",
      "target": "node-1",
      "type": "supports",
      "label": "improves",
      "strength": 0.8,
      "confidence": 0.9,
      "created_at": "2025-11-01T10:33:00Z",
      "metadata": {
        "reason": "Mobile responsiveness is part of good UX"
      }
    },
    {
      "id": "edge-2",
      "source": "node-2",
      "target": "node-3",
      "type": "causes",
      "label": "requires",
      "strength": 0.9,
      "confidence": 0.95,
      "created_at": "2025-11-01T10:35:00Z",
      "metadata": {
        "reason": "Need to test mobile responsiveness"
      }
    }
  ],
  "metadata": {
    "summary": "Discussion about improving user experience with focus on mobile responsiveness",
    "main_themes": ["UX", "mobile", "testing"],
    "duration_seconds": 300,
    "graph_complexity": 0.3,
    "layout_hint": "force"
  }
}
```

## LLM Instructions for Graph Generation

When generating graphs, the LLM should:

1. **Maintain ID stability**: Reuse node IDs when concepts persist
2. **Merge similar concepts**: Don't create duplicate nodes
3. **Update importance**: Increase for repeated mentions
4. **Prune irrelevant nodes**: Remove if no longer relevant (optional)
5. **Create meaningful edges**: Only connect truly related concepts
6. **Use semantic types**: Choose appropriate node/edge types
7. **Provide context**: Use description and metadata fields
8. **Balance complexity**: Don't overwhelm with too many nodes

## Validation

The graph should be validated against this schema before sending to frontend. Key checks:

- All node IDs in edges exist
- No duplicate node/edge IDs
- Numeric values in valid ranges
- Required fields present
- Timestamps in ISO-8601 format

See `shared/schemas/graph.json` for JSON Schema definition.
