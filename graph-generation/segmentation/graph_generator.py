"""
Graph Generator

Core logic for generating knowledge graphs from transcript text using LLM.
"""

import os
import json
from typing import Dict, Optional
from datetime import datetime

from llm_client import LLMClient
from graph_validator import validate_graph, GraphValidationError


class GraphGenerator:
    """Generates knowledge graphs from transcript text using Claude API"""
    
    def __init__(self, model: Optional[str] = None):
        """
        Initialize graph generator.
        
        Args:
            model: Claude model name. If None, uses default from LLM_MODEL env var
        """
        self.llm_client = LLMClient(model=model)
        self._load_prompt_template()
    
    def _load_prompt_template(self) -> None:
        """Load the system prompt template"""
        # Get directory where this file is located (segmentation folder)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Prompt is now in the same folder
        prompt_path = os.path.join(current_dir, 'system-prompt.md')
        
        try:
            with open(prompt_path, 'r') as f:
                self.prompt_template = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Prompt template not found at {prompt_path}. "
                "Please ensure system-prompt.md exists in the segmentation folder."
            )
    
    def generate(
        self,
        previous_transcript: Optional[str] = None,
        new_transcript: Optional[str] = None,
        previous_graph: Optional[Dict] = None,
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Generate or update a knowledge graph from new transcript text.

        Args:
            previous_transcript: Transcript used to build the previous graph
            new_transcript: New transcript to process and add to graph
            previous_graph: Previous graph state (or None for first chunk)
            session_id: Optional session ID

        Returns:
            Complete updated graph as dictionary
        """
        # Handle None values - backward compatibility
        if new_transcript is None:
            new_transcript = ''

        if not new_transcript or not new_transcript.strip():
            # Return empty graph structure if no text
            return self._empty_graph(session_id, previous_graph)
        
        # Split prompt template into system and user parts
        if '## Instructions' in self.prompt_template:
            system_prompt = self.prompt_template.split('## Instructions')[0].strip()
            user_template = self.prompt_template.split('## Instructions')[1].strip()
        else:
            system_prompt = self.prompt_template
            user_template = "Given the previous_graph and new_transcript below, generate an updated graph.\n\n**Previous Graph:**\n```json\n{previous_graph}\n```\n\n**New Transcript:**\n```\n{new_transcript}\n```\n\n**Output:**\n\nGenerate ONLY the complete updated graph as valid JSON."

        # Format user prompt
        previous_graph_json = json.dumps(previous_graph, indent=2) if previous_graph else "null"

        # Default to empty string if previous_transcript not provided
        previous_transcript_text = previous_transcript if previous_transcript else ''

        # Check if template expects previous_transcript (new format)
        if '{previous_transcript}' in user_template:
            user_prompt = user_template.format(
                previous_graph=previous_graph_json,
                previous_transcript=previous_transcript_text,
                new_transcript=new_transcript
            )
        else:
            # Backward compatibility: old template format
            user_prompt = user_template.format(
                previous_graph=previous_graph_json,
                new_transcript=new_transcript
            )
        
        # Call LLM
        try:
            response = self.llm_client.generate_graph(system_prompt, user_prompt)
            graph = self.llm_client.extract_json(response)
        except Exception as e:
            raise RuntimeError(f"LLM graph generation failed: {e}") from e
        
        # Validate schema
        try:
            validate_graph(graph)
        except GraphValidationError as e:
            raise GraphValidationError(f"Generated graph failed validation: {e}") from e
        
        # Add metadata
        now = datetime.utcnow().isoformat() + 'Z'
        graph['timestamp'] = now
        graph['version'] = (previous_graph.get('version', 0) + 1) if previous_graph else 1
        if session_id:
            graph['session_id'] = session_id
        
        # Ensure metadata field exists
        if 'metadata' not in graph:
            graph['metadata'] = {}
        
        return graph
    
    def expand_node(
        self,
        node_id: str,
        current_graph: Dict,
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Expand a node by generating 4 subtopic nodes related to it.
        
        Args:
            node_id: ID of the node to expand
            current_graph: Current graph state
            session_id: Optional session ID
            
        Returns:
            Updated graph with new subtopic nodes and edges
        """
        # Find the target node
        nodes = current_graph.get('nodes', [])
        target_node = None
        for node in nodes:
            if node.get('id') == node_id:
                target_node = node
                break
        
        if not target_node:
            raise ValueError(f"Node with id '{node_id}' not found in graph")
        
        # Create expansion prompt
        system_prompt = """You are a knowledge graph assistant that expands nodes into subtopics.
When given a node from a knowledge graph, generate exactly 4 subtopic nodes that dive deeper into that topic.
These subtopics should be:
- Related and relevant to the parent node
- Distinct from each other
- Meaningful subdivisions or aspects of the parent topic
- Appropriately labeled (1-4 words)
- Assigned appropriate types (concept, topic, action, question, etc.)
- Given appropriate colors based on their type"""
        
        graph_json = json.dumps(current_graph, indent=2)
        target_node_json = json.dumps(target_node, indent=2)
        
        user_prompt = f"""Given the following knowledge graph and a target node, generate exactly 4 new subtopic nodes that explore this topic in more depth.

**Current Graph:**
```json
{graph_json}
```

**Target Node to Expand:**
```json
{target_node_json}
```

**Task:**
Generate 4 new subtopic nodes that relate to "{target_node.get('label', '')}" and add them to the graph.

**Requirements:**
1. Create exactly 4 new nodes (no more, no less)
2. Each new node should have:
   - A unique ID (e.g., "{node_id}-sub-1", "{node_id}-sub-2", etc. or use descriptive IDs)
   - A label that represents a subtopic/aspect of the parent node
   - Appropriate type (concept, topic, action, question, etc.)
   - Importance between 0.4 and 0.7 (subtopics should be less important than parent)
   - Confidence between 0.7 and 0.9
   - Appropriate color based on type
   - Created_at timestamp (now)
   - Metadata with tags
3. Create edges connecting each new subtopic node to the target node:
   - Edge type: "elaborates" (subtopics elaborate on the parent)
   - Strength: 0.7-0.9
   - Label: optional description of relationship
4. Keep all existing nodes and edges from the current graph
5. Update the target node's updated_at timestamp

**Output:**
Return ONLY the complete updated graph as valid JSON, including:
- All existing nodes (unchanged except target node's updated_at)
- All existing edges (unchanged)
- 4 new subtopic nodes
- 4 new edges connecting subtopics to target node
- Updated metadata if needed"""
        
        # Call LLM
        try:
            response = self.llm_client.generate_graph(system_prompt, user_prompt)
            graph = self.llm_client.extract_json(response)
        except Exception as e:
            raise RuntimeError(f"LLM node expansion failed: {e}") from e
        
        # Validate schema
        try:
            validate_graph(graph)
        except GraphValidationError as e:
            raise GraphValidationError(f"Expanded graph failed validation: {e}") from e
        
        # Add metadata
        now = datetime.utcnow().isoformat() + 'Z'
        graph['timestamp'] = now
        graph['version'] = current_graph.get('version', 0) + 1
        if session_id:
            graph['session_id'] = session_id
        
        # Ensure metadata field exists
        if 'metadata' not in graph:
            graph['metadata'] = current_graph.get('metadata', {})
        
        return graph
    
    def _empty_graph(self, session_id: Optional[str] = None, previous_graph: Optional[Dict] = None) -> Dict:
        """Create an empty graph structure"""
        now = datetime.utcnow().isoformat() + 'Z'
        graph = {
            'nodes': [],
            'edges': [],
            'metadata': {
                'summary': '',
                'main_themes': [],
                'graph_complexity': 0.0,
                'layout_hint': 'force'
            },
            'timestamp': now,
            'version': (previous_graph.get('version', 0) + 1) if previous_graph else 1
        }
        if session_id:
            graph['session_id'] = session_id
        return graph


def generate_graph(
    previous_transcript: Optional[str] = None,
    new_transcript: Optional[str] = None,
    previous_graph: Optional[Dict] = None,
    session_id: Optional[str] = None,
    model: Optional[str] = None
) -> Dict:
    """
    Convenience function to generate a graph.

    Args:
        previous_transcript: Transcript used to build the previous graph
        new_transcript: New transcript to process
        previous_graph: Previous graph state (or None for first chunk)
        session_id: Optional session ID
        model: Optional Claude model name

    Returns:
        Complete updated graph as dictionary
    """
    generator = GraphGenerator(model=model)
    return generator.generate(previous_transcript, new_transcript, previous_graph, session_id)

