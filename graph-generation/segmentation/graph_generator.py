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
        new_text: str, 
        previous_graph: Optional[Dict] = None,
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Generate or update a knowledge graph from new transcript text.
        
        Args:
            new_text: New transcript chunk text
            previous_graph: Previous graph state (or None for first chunk)
            session_id: Optional session ID
            
        Returns:
            Complete updated graph as dictionary
        """
        if not new_text or not new_text.strip():
            # Return empty graph structure if no text
            return self._empty_graph(session_id, previous_graph)
        
        # Split prompt template into system and user parts
        if '## Instructions' in self.prompt_template:
            system_prompt = self.prompt_template.split('## Instructions')[0].strip()
            user_template = self.prompt_template.split('## Instructions')[1].strip()
        else:
            system_prompt = self.prompt_template
            user_template = "Given the previous_graph and new_text below, generate an updated graph.\n\n**Previous Graph:**\n```json\n{previous_graph}\n```\n\n**New Text:**\n```\n{new_text}\n```\n\n**Output:**\n\nGenerate ONLY the complete updated graph as valid JSON."
        
        # Format user prompt
        previous_graph_json = json.dumps(previous_graph, indent=2) if previous_graph else "null"
        user_prompt = user_template.format(
            previous_graph=previous_graph_json,
            new_text=new_text
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
    new_text: str,
    previous_graph: Optional[Dict] = None,
    session_id: Optional[str] = None,
    model: Optional[str] = None
) -> Dict:
    """
    Convenience function to generate a graph.
    
    Args:
        new_text: New transcript chunk text
        previous_graph: Previous graph state (or None for first chunk)
        session_id: Optional session ID
        model: Optional Claude model name
        
    Returns:
        Complete updated graph as dictionary
    """
    generator = GraphGenerator(model=model)
    return generator.generate(new_text, previous_graph, session_id)

