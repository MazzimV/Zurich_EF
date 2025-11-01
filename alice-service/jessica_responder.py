"""Jessica responder - generates answers to meeting questions using Claude."""

import logging
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any
from llm_client import LLMClient
from tts_client import TTSClient

logger = logging.getLogger(__name__)


class JessicaResponder:
    """Generates answers to meeting questions using Claude and converts to speech."""

    def __init__(self, model: Optional[str] = None):
        """
        Initialize Jessica responder.

        Args:
            model: Optional model override (defaults to Claude Sonnet 4.5)
        """
        self.llm_client = LLMClient(model=model)
        self.tts_client = TTSClient()
        self._load_prompt_template()

    def _load_prompt_template(self) -> None:
        """Load the Jessica system prompt template from file."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(current_dir, 'jessica-prompt.md')

        try:
            with open(prompt_path, 'r') as f:
                self.system_prompt = f.read()
            logger.info("Loaded Jessica system prompt")
        except Exception as e:
            logger.error(f"Failed to load Jessica prompt template: {e}")
            # Fallback to basic prompt
            self.system_prompt = "You are Jessica, a helpful meeting assistant. Answer questions about the meeting concisely."

    def answer(
        self,
        question: str,
        transcript: str,
        graph: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate an answer to a meeting question.

        Args:
            question: The question asked by the participant
            transcript: The full meeting transcript
            graph: Optional knowledge graph structure
            session_id: Optional session identifier

        Returns:
            Dictionary containing:
            - answer: The text answer from Jessica
            - audio_base64: Base64-encoded audio (if TTS succeeds)
            - timestamp: ISO-8601 timestamp
            - error: Error message if something failed (optional)
        """
        try:
            # Format the user prompt
            user_prompt = self._format_user_prompt(question, transcript, graph)

            # Call Claude to generate answer
            logger.info(f"Generating answer for question: {question[:100]}...")
            answer_text = self.llm_client.generate_graph(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt
            )

            # Generate audio from the answer
            audio_base64, tts_error = self.tts_client.text_to_speech(answer_text)

            # Build response
            response = {
                'answer': answer_text,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }

            if audio_base64:
                response['audio_base64'] = audio_base64

            if tts_error:
                response['tts_error'] = tts_error
                logger.warning(f"TTS generation failed: {tts_error}")

            logger.info("Successfully generated answer")
            return response

        except Exception as e:
            logger.error(f"Failed to generate answer: {e}", exc_info=True)
            return {
                'answer': "I'm sorry, I encountered an error while processing your question.",
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'error': str(e)
            }

    def _format_user_prompt(
        self,
        question: str,
        transcript: str,
        graph: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format the user prompt with question, transcript, and graph context.

        Args:
            question: The question to answer
            transcript: Meeting transcript
            graph: Optional knowledge graph

        Returns:
            Formatted user prompt string
        """
        prompt_parts = []

        # Add the question
        prompt_parts.append(f"**Question**: {question}")
        prompt_parts.append("")

        # Add transcript
        if transcript:
            prompt_parts.append("**Meeting Transcript**:")
            prompt_parts.append("```")
            prompt_parts.append(transcript)
            prompt_parts.append("```")
            prompt_parts.append("")
        else:
            prompt_parts.append("**Meeting Transcript**: (No transcript available yet)")
            prompt_parts.append("")

        # Add graph if available
        if graph:
            try:
                # Extract key information from graph
                graph_summary = self._summarize_graph(graph)
                prompt_parts.append("**Knowledge Graph Summary**:")
                prompt_parts.append(graph_summary)
                prompt_parts.append("")
            except Exception as e:
                logger.warning(f"Failed to process graph: {e}")

        prompt_parts.append("**Your Task**: Provide a concise, helpful answer based on the above information.")

        return "\n".join(prompt_parts)

    def _summarize_graph(self, graph: Dict[str, Any]) -> str:
        """
        Create a text summary of the knowledge graph.

        Args:
            graph: The knowledge graph structure

        Returns:
            Text summary of the graph
        """
        summary_parts = []

        # Extract nodes
        nodes = graph.get('nodes', [])
        if nodes:
            # Group nodes by type
            nodes_by_type = {}
            for node in nodes:
                node_type = node.get('type', 'unknown')
                if node_type not in nodes_by_type:
                    nodes_by_type[node_type] = []
                nodes_by_type[node_type].append(node.get('label', 'Unknown'))

            summary_parts.append("Main concepts identified:")
            for node_type, labels in nodes_by_type.items():
                if labels:
                    summary_parts.append(f"- {node_type.capitalize()}: {', '.join(labels[:5])}")

        # Extract metadata summary
        metadata = graph.get('metadata', {})
        if metadata:
            main_summary = metadata.get('summary', '')
            if main_summary:
                summary_parts.append(f"\nOverall: {main_summary}")

            themes = metadata.get('main_themes', [])
            if themes:
                summary_parts.append(f"Main themes: {', '.join(themes)}")

        return "\n".join(summary_parts) if summary_parts else "No graph information available."
