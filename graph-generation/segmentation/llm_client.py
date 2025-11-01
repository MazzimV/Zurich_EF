"""
LLM Client for Graph Generation

Provides a wrapper for calling Claude API (Anthropic).
"""

import os
import json
import re
from typing import Optional

# Load environment variables from .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class LLMClient:
    """Wrapper for Claude API calls"""
    
    def __init__(self, model: Optional[str] = None):
        """
        Initialize LLM client.
        
        Args:
            model: Claude model name. If None, reads from LLM_MODEL env var
                   Defaults to 'claude-sonnet-4-5-20250929' (Claude Sonnet 4.5 - recommended)
                   Also available: 'claude-haiku-4-5-20251001' (faster/cheaper)
                                   'claude-opus-4-1-20250805' (most advanced)
        """
        # Use Claude Sonnet 4.5 by default - best balance of intelligence, speed, and cost
        self.model = model or os.getenv('LLM_MODEL', 'claude-sonnet-4-5-20250929')
        
        try:
            from anthropic import Anthropic
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            self.client = Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("anthropic package not installed. Install with: pip install anthropic")
    
    def generate_graph(self, system_prompt: str, user_prompt: str) -> str:
        """
        Call Claude API to generate a graph.
        
        Args:
            system_prompt: System-level instructions
            user_prompt: User input with previous graph and new text
            
        Returns:
            LLM response text (should be JSON)
        """
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": user_prompt
                }]
            )
            return message.content[0].text
        except Exception as e:
            # Provide helpful error message if API key is missing or invalid
            if "api_key" in str(e).lower() or "authentication" in str(e).lower():
                raise ValueError(
                    f"Claude API authentication failed. Please set ANTHROPIC_API_KEY environment variable.\n"
                    f"Get your API key from: https://console.anthropic.com/"
                ) from e
            raise
    
    def extract_json(self, text: str) -> dict:
        """
        Extract JSON from LLM response, handling markdown code blocks.
        
        Args:
            text: LLM response text that may contain JSON
            
        Returns:
            Parsed JSON as dictionary
        """
        # Try to find JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object directly
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = text.strip()
        
        # Parse JSON
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from LLM response: {e}\nResponse: {text[:500]}")

