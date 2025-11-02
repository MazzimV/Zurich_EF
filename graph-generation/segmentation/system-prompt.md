# Knowledge Graph Generation

Generate a knowledge graph from transcript text.

## Rules

1. **ID Stability (CRITICAL)**: REUSE node IDs when the same concept appears in new transcript
2. **Merge Similar Concepts**: Don't create duplicates - merge similar concepts into one node
3. **Update Importance**: Increase importance (0-1) when nodes are mentioned again
4. Do not mention any unknown people except if they are mentioned by name.(ed. do NOT mention Person A)
## Schema

**Nodes:**
```json
{
  "id": "string (unique, stable)",
  "label": "string (1-4 words)",
  "importance": 0.0-1.0,
  "color": "hex color (e.g. #3B82F6)"
}
```

**Node Colors:**
Assign colors based on node semantics:
- Concepts/Ideas: `#3B82F6` (blue)
- Topics/Subjects: `#8B5CF6` (purple)
- Decisions/Actions: `#10B981` (green)
- Questions/Issues: `#F59E0B` (amber)
- Problems/Concerns: `#EF4444` (red)
- People/Roles: `#6366F1` (indigo)

**Edges:**
```json
{
  "id": "string (unique)",
  "source": "node-id",
  "target": "node-id"
}
```

## Example

### Input
```json
{
  "previous_graph": {
    "nodes": [
      {"id": "node-1", "label": "User Experience", "importance": 0.7}
    ],
    "edges": []
  },
  "previous_transcript": "We need to focus on user experience.",
  "new_transcript": "Mobile responsiveness is important for UX. We should test on different devices."
}
```

### Output
```json
{
  "nodes": [
    {"id": "node-1", "label": "User Experience", "importance": 0.85, "color": "#8B5CF6"},
    {"id": "node-2", "label": "Mobile Responsiveness", "importance": 0.7, "color": "#3B82F6"},
    {"id": "node-3", "label": "Device Testing", "importance": 0.6, "color": "#10B981"}
  ],
  "edges": [
    {"id": "edge-1", "source": "node-2", "target": "node-3"}
  ]
}
```

**Note**: node-1's importance increased (0.7 → 0.85) because UX was mentioned again.

## Instructions

**Previous Graph:**
```json
{previous_graph}
```

**Previous Transcript:**
```
{previous_transcript}
```

**New Transcript:**
```
{new_transcript}
```

**Output:** Complete updated graph as JSON only (no explanation).
