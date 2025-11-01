# What Happens When New Text is Added to the Graph

This document explains how the knowledge graph updates when new transcript text is processed.

## Overview

When `generate_graph()` is called with:
- `new_text`: New transcript chunk
- `previous_graph`: Existing graph state (or `None` for the first chunk)

The system uses an LLM (Claude) to intelligently merge the new information into the existing graph structure.

## Update Process

### 1. **ID Stability (Critical)**
- **Existing nodes keep their IDs** when the same concept is discussed
- Example: If you have `{"id": "node-2", "label": "User Experience"}` and new text mentions UX again, the node keeps ID `"node-2"` but may update its properties

### 2. **Label Refinement**
- If new text mentions a concept that's **more specific** than an existing node, the label is updated to be more specific
- The node ID stays the same
- Examples:
  - `"budget management"` → `"budget expenses"` (more specific)
  - `"user interface"` → `"mobile user interface"` (more specific)
  - `"testing"` → `"automated testing"` (more specific)

### 3. **Node Updates**
When an existing concept is mentioned:
- **Importance**: Increases for frequently mentioned concepts
- **Description**: May be expanded with new context
- **Updated timestamp**: `updated_at` field is refreshed
- **Mentions count**: Incremented in metadata
- **Tags**: May be added or refined

### 4. **New Nodes**
- Created only for **genuinely new concepts** not in the previous graph
- Each new node gets:
  - A unique ID (e.g., `"node-6"`)
  - Appropriate type (concept, topic, decision, question, action, person)
  - Initial importance score
  - Color based on semantic type
  - Creation timestamp

### 5. **Edge Creation**
- New edges connect related nodes from the new text
- Edge types: `relates_to`, `causes`, `supports`, `contradicts`, `follows`, `elaborates`
- Strength and confidence scores reflect relationship certainty
- Edges include metadata explaining why the connection exists

### 6. **Version Increment**
- Graph `version` number is incremented: `previous_version + 1`
- Timestamp is updated to current time
- Session ID is preserved (if provided)

### 7. **Metadata Updates**
- **Summary**: Updated to reflect the full conversation so far
- **Main themes**: Updated list of key topics
- **Graph complexity**: Recalculated based on node/edge count
- **Layout hint**: May change based on graph structure

## Example Flow

### Initial State
```json
{
  "nodes": [
    {"id": "node-1", "label": "Mobile App", "importance": 0.7}
  ],
  "version": 1
}
```

### New Text: "We need to improve mobile responsiveness for the app. Test on iPhone and Android."

### Updated Graph
```json
{
  "nodes": [
    {
      "id": "node-1", 
      "label": "Mobile App", 
      "importance": 0.8,  // ↑ Increased (mentioned again)
      "updated_at": "2025-11-01T10:05:00Z"  // Updated
    },
    {
      "id": "node-2",  // NEW node
      "label": "Mobile Responsiveness",
      "type": "concept",
      "importance": 0.75,
      "created_at": "2025-11-01T10:05:00Z"
    },
    {
      "id": "node-3",  // NEW node
      "label": "Device Testing",
      "type": "action",
      "importance": 0.6,
      "created_at": "2025-11-01T10:05:00Z"
    }
  ],
  "edges": [
    {
      "id": "edge-1",  // NEW edge
      "source": "node-2",
      "target": "node-1",
      "type": "supports",
      "strength": 0.9
    },
    {
      "id": "edge-2",  // NEW edge
      "source": "node-2",
      "target": "node-3",
      "type": "causes",
      "strength": 0.85
    }
  ],
  "version": 2,  // ↑ Incremented
  "metadata": {
    "summary": "Discussion about mobile app with focus on responsiveness and testing",
    "main_themes": ["mobile app", "responsiveness", "testing"]
  }
}
```

## Key Behaviors

### Merge vs. Duplicate
- The LLM tries to **merge** similar concepts into existing nodes rather than creating duplicates
- Example: "mobile UX" and "responsive design" might update the same node instead of creating two

### Importance Scoring
- Nodes mentioned repeatedly get higher importance (affects visual size in frontend)
- Nodes not mentioned recently may have decreased importance

### Graph Size Management
- Maximum 50 nodes (less important nodes may be pruned if limit is reached)
- Focus on main concepts, not every detail

## Technical Implementation

1. **Prompt Construction**: The system creates a prompt with:
   - Previous graph JSON (or `null` if first chunk)
   - New text chunk
   - Instructions on how to update (from `system-prompt.md`)

2. **LLM Processing**: Claude analyzes both inputs and generates a complete updated graph

3. **Validation**: Generated graph is validated against schema

4. **Metadata Addition**: Timestamp, version, and session_id are added automatically

## Testing

You can see this behavior in action by running:
```bash
python test_generation.py
```

The `test_label_refinement()` and `test_incremental_updates()` functions demonstrate how the graph evolves with new text.

