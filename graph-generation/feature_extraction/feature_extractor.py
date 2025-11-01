"""
Knowledge Graph Generation Module

This module generates knowledge graphs from transcript text using LLM.
It uses the system prompt to generate complete graph structures directly.
"""

import re
import os
import json
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def _extract_json_from_response(response_text: str) -> str:
    """Extract JSON from LLM response, handling markdown code blocks"""
    # Try to find JSON in markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if json_match:
        return json_match.group(1)
    
    # Try to find JSON object directly
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if json_match:
        return json_match.group(0)
    
    # Return as-is if no pattern matches
    return response_text.strip()


def _load_system_prompt() -> str:
    """Load the system prompt template from prompts/system-prompt.md"""
    # Get the directory of this file
    current_dir = Path(__file__).parent
    # Go up one level to graph-generation, then into prompts
    prompt_path = current_dir.parent / "prompts" / "system-prompt.md"
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"System prompt not found at {prompt_path}")
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()


class FeatureExtractor:
    """
    Generates knowledge graphs from transcript text using LLM.
    
    Uses the system prompt template to generate complete graph structures
    with nodes, edges, and metadata directly from transcript chunks.
    """
    
    def __init__(self, 
                 llm_model: str = "claude-3-5-haiku-20241022",
                 anthropic_api_key: Optional[str] = None):
        """
        Initialize the graph generator.
        
        Args:
            llm_model: Claude model name (default: "claude-3-5-haiku-20241022")
            anthropic_api_key: Anthropic API key (or use ANTHROPIC_API_KEY env var)
        """
        self.llm_model = llm_model
        
        # Initialize Anthropic client
        try:
            from anthropic import Anthropic
            api_key = anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY not found. "
                    "Set it as environment variable or pass anthropic_api_key parameter."
                )
            self.client = Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("anthropic package not installed. Install with: pip install anthropic")
        except Exception as e:
            raise ValueError(f"Failed to initialize Anthropic client: {e}")
        
        # Load system prompt template
        self.system_prompt_template = _load_system_prompt()
    
    def _create_prompt(self, previous_graph: Optional[Dict], new_text: str) -> str:
        """Create prompt by replacing placeholders in the system prompt template"""
        # Format previous_graph as JSON string or "null"
        if previous_graph:
            previous_graph_json = json.dumps(previous_graph, indent=2)
        else:
            previous_graph_json = "null"
        
        # Replace placeholders using string replacement (not .format() to avoid conflicts with JSON braces)
        prompt = self.system_prompt_template.replace(
            "{previous_graph}",
            previous_graph_json
        ).replace(
            "{new_text}",
            new_text
        )
        
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """Call Anthropic Claude API"""
        message = self.client.messages.create(
            model=self.llm_model,
            max_tokens=8000,  # Increased for complete graphs
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        return message.content[0].text
    
    def generate_graph(self, 
                      new_text: str, 
                      previous_graph: Optional[Dict] = None,
                      metadata: Optional[Dict] = None) -> Dict:
        """
        Generate a complete knowledge graph from new text and previous graph state.
        
        Args:
            new_text: New transcript chunk to process
            previous_graph: Previous graph state (or None if first chunk)
            metadata: Optional metadata (session_id, timestamp, etc.)
            
        Returns:
            Complete graph dictionary with nodes, edges, and metadata
        """
        if not new_text or not new_text.strip():
            # Return empty graph structure
            return {
                "nodes": [],
                "edges": [],
                "metadata": {
                    "summary": "",
                    "main_themes": [],
                    "graph_complexity": 0.0,
                    "layout_hint": "force"
                }
            }
        
        # Create prompt and call LLM
        prompt = self._create_prompt(previous_graph, new_text)
        
        try:
            response_text = self._call_llm(prompt)
        except Exception as e:
            raise RuntimeError(f"Failed to call Claude API for graph generation: {e}")
        
        # Extract JSON from response
        json_text = _extract_json_from_response(response_text)
        
        try:
            graph = json.loads(json_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}\nResponse was: {response_text[:500]}")
        
        # Validate basic structure
        if not isinstance(graph, dict):
            raise ValueError("LLM response is not a valid JSON object")
        
        # Ensure required top-level keys exist
        if "nodes" not in graph:
            graph["nodes"] = []
        if "edges" not in graph:
            graph["edges"] = []
        if "metadata" not in graph:
            graph["metadata"] = {}
        
        # Add generation metadata
        graph_metadata = graph.get("metadata", {})
        graph_metadata["generation_timestamp"] = datetime.utcnow().isoformat() + 'Z'
        graph_metadata["llm_model"] = self.llm_model
        
        # Merge with provided metadata
        if metadata:
            graph_metadata.update(metadata)
        
        graph["metadata"] = graph_metadata
        
        return graph


def generate_graph(new_text: str,
                   previous_graph: Optional[Dict] = None,
                   llm_model: str = "claude-3-5-haiku-20241022",
                   metadata: Optional[Dict] = None) -> Dict:
    """
    Convenience function to generate a graph from text using Claude.
    
    Args:
        new_text: New transcript chunk to process
        previous_graph: Previous graph state (or None if first chunk)
        llm_model: Claude model name
        metadata: Optional metadata dictionary
        
    Returns:
        Complete graph dictionary
    """
    extractor = FeatureExtractor(llm_model=llm_model)
    return extractor.generate_graph(new_text, previous_graph, metadata)


if __name__ == "__main__":
    # Test the graph generator
    test_text = "I think we need to focus on mobile responsiveness as part of the UX. Let's make sure it works on all devices. We should test on iPhone and Android."
    
    try:
        extractor = FeatureExtractor()
        
        # Test with no previous graph (first chunk)
        print("=== Generating First Graph ===\n")
        graph1 = extractor.generate_graph(test_text)
        
        print(f"Nodes: {len(graph1.get('nodes', []))}")
        print(f"Edges: {len(graph1.get('edges', []))}")
        print(f"\nSummary: {graph1.get('metadata', {}).get('summary', 'N/A')}")
        print(f"Themes: {graph1.get('metadata', {}).get('main_themes', [])}")
        
        print("\n=== Nodes ===")
        for node in graph1.get('nodes', [])[:5]:
            print(f"  - {node.get('label')} [{node.get('type')}] (importance: {node.get('importance', 0):.2f})")
        
        print("\n=== Edges ===")
        for edge in graph1.get('edges', [])[:5]:
            print(f"  - {edge.get('source')} -> {edge.get('target')} [{edge.get('type')}]")
        
        # Test with previous graph (update)
        print("\n\n=== Generating Updated Graph ===\n")
        graph2 = extractor.generate_graph(
            "Actually, I think we should prioritize tablet support too. And maybe add a dark mode feature.",
            previous_graph=graph1
        )
        
        print(f"Nodes: {len(graph2.get('nodes', []))}")
        print(f"Edges: {len(graph2.get('edges', []))}")
        print(f"\nSummary: {graph2.get('metadata', {}).get('summary', 'N/A')}")
        
        # Save to file for inspection
        with open('test_graph_output.json', 'w') as f:
            json.dump(graph2, f, indent=2)
        print("\n✓ Graph saved to test_graph_output.json")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
