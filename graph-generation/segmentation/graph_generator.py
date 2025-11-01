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
        
        # Extract minimal context (only target + neighbors) - huge token savings
        minimal_context = self._extract_minimal_context(node_id, current_graph)
        
        # Use faster model for expansions
        expansion_model = os.getenv('EXPANSION_MODEL', 'claude-haiku-4-5-20251001')
        from llm_client import LLMClient
        fast_client = LLMClient(model=expansion_model)
        
        # Ultra-minimal prompt for speed
        system_prompt = "Generate 4 subtopic nodes. Return JSON: {new_nodes: [...], new_edges: [...]}"
        
        # Minimal context JSON (compact, no indent)
        context_json = json.dumps(minimal_context)  # No indent = 30% smaller
        target_label = target_node.get('label', '')
        
        user_prompt = f"""Expand "{target_label}" with 4 subtopics.

Neighbors: {context_json}

Return JSON only:
{{"new_nodes": [
  {{"id": "{node_id}-sub-1", "label": "...", "importance": 0.5, "color": "#3B82F6"}},
  {{"id": "{node_id}-sub-2", "label": "...", "importance": 0.5, "color": "#8B5CF6"}},
  {{"id": "{node_id}-sub-3", "label": "...", "importance": 0.5, "color": "#10B981"}},
  {{"id": "{node_id}-sub-4", "label": "...", "importance": 0.5, "color": "#F59E0B"}}
], "new_edges": [
  {{"id": "e1", "source": "{node_id}-sub-1", "target": "{node_id}"}},
  {{"id": "e2", "source": "{node_id}-sub-2", "target": "{node_id}"}},
  {{"id": "e3", "source": "{node_id}-sub-3", "target": "{node_id}"}},
  {{"id": "e4", "source": "{node_id}-sub-4", "target": "{node_id}"}}
]}}"""
        
        # Call LLM with reduced max_tokens (only need ~500 for 4 nodes + 4 edges)
        try:
            response = fast_client.generate_graph(system_prompt, user_prompt, max_tokens_override=512)
            response_data = fast_client.extract_json(response)
            
            # Extract only new nodes/edges from response
            new_nodes = response_data.get('new_nodes', [])
            new_edges = response_data.get('new_edges', [])
            
            if len(new_nodes) != 4 or len(new_edges) != 4:
                raise ValueError(f"Expected 4 nodes and 4 edges, got {len(new_nodes)} and {len(new_edges)}")
            
            # Merge with existing graph (don't return full graph from LLM)
            now = datetime.utcnow().isoformat() + 'Z'
            expanded_graph = json.loads(json.dumps(current_graph))  # Deep copy
            
            # Add new nodes/edges
            expanded_graph['nodes'].extend(new_nodes)
            expanded_graph['edges'].extend(new_edges)
            
            # Update metadata
            expanded_graph['timestamp'] = now
            expanded_graph['version'] = current_graph.get('version', 0) + 1
            if session_id:
                expanded_graph['session_id'] = session_id
            
            graph = expanded_graph
        except Exception as e:
            raise RuntimeError(f"LLM node expansion failed: {e}") from e
        
        # Lightweight validation (only new nodes/edges, skip full graph check for speed)
        try:
            for node in new_nodes:
                if not node.get('id') or not node.get('label') or 'importance' not in node:
                    raise GraphValidationError(f"Invalid new node: missing required fields")
            for edge in new_edges:
                if not edge.get('id') or not edge.get('source') or not edge.get('target'):
                    raise GraphValidationError(f"Invalid new edge: missing required fields")
        except GraphValidationError as e:
            raise GraphValidationError(f"Expansion validation failed: {e}") from e
        
        return graph
    
    def _extract_minimal_context(self, node_id: str, current_graph: Dict) -> Dict:
        """
        Extract minimal context: only target node + immediate neighbors.
        Reduces input tokens by 80-90%.
        """
        nodes = current_graph.get('nodes', [])
        edges = current_graph.get('edges', [])
        
        # Find target node
        target_node = None
        for node in nodes:
            if node.get('id') == node_id:
                target_node = node
                break
        
        if not target_node:
            raise ValueError(f"Node {node_id} not found")
        
        # Find neighbors (directly connected nodes)
        connected_ids = {node_id}
        relevant_edges = []
        
        for edge in edges:
            source = edge.get('source')
            target = edge.get('target')
            if source == node_id or target == node_id:
                relevant_edges.append({'source': source, 'target': target})
                connected_ids.add(source)
                connected_ids.add(target)
        
        # Extract only relevant nodes (minimal fields)
        relevant_nodes = []
        for node in nodes:
            if node.get('id') in connected_ids:
                relevant_nodes.append({
                    'id': node.get('id'),
                    'label': node.get('label'),
                    'importance': node.get('importance', 0.5)
                })
        
        return {'nodes': relevant_nodes, 'edges': relevant_edges}
    
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

