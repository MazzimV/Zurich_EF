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
            # Increase max_tokens for larger graphs (Claude Sonnet 4.5 supports up to 8192)
            # Use higher limit to handle complex graphs with many nodes/edges
            max_tokens = int(os.getenv('MAX_TOKENS', '8192'))
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": user_prompt
                }]
            )
            
            response_text = message.content[0].text
            
            # Check if response was truncated (stop_reason is on the message object)
            try:
                stop_reason = getattr(message, 'stop_reason', None)
                if stop_reason == 'max_tokens':
                    raise ValueError(
                        f"LLM response was truncated (hit max_tokens limit of {max_tokens}). "
                        f"The graph may be too complex. Try reducing the number of nodes or increasing MAX_TOKENS."
                    )
            except AttributeError:
                # stop_reason might not be available in all API versions
                pass
            
            return response_text
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
        # Try to find JSON in markdown code blocks (non-greedy match)
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object directly - match from first { to last }
            # This is more robust for incomplete JSON
            brace_start = text.find('{')
            if brace_start != -1:
                # Find the matching closing brace
                brace_count = 0
                json_end = -1
                for i in range(brace_start, len(text)):
                    if text[i] == '{':
                        brace_count += 1
                    elif text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                if json_end > brace_start:
                    json_str = text[brace_start:json_end]
                else:
                    # JSON appears incomplete - try to find what we can
                    json_str = text[brace_start:]
            else:
                json_str = text.strip()
        
        # Parse JSON
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # Check if JSON appears incomplete (common signs: unclosed strings, missing brackets)
            if json_str.count('{') != json_str.count('}'):
                error_msg = (
                    f"JSON appears incomplete (unmatched braces). "
                    f"Response may have been truncated.\n"
                    f"Error: {e}\n"
                    f"Response preview (first 1000 chars):\n{text[:1000]}"
                )
            elif json_str.endswith(('"', "'", ',')) or not json_str.strip().endswith('}'):
                error_msg = (
                    f"JSON appears incomplete (ends unexpectedly). "
                    f"Response may have been truncated.\n"
                    f"Error: {e}\n"
                    f"JSON end: ...{json_str[-200:]}"
                )
            else:
                error_msg = (
                    f"Failed to parse JSON from LLM response: {e}\n"
                    f"Response preview (first 1000 chars):\n{text[:1000]}"
                )
            raise ValueError(error_msg)

