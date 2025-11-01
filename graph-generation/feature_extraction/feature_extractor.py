"""
Feature Extraction Module

This module extracts structured features from transcript text using LLM before semantic clustering/graph generation.
It uses an LLM to identify entities, key phrases, concepts, questions, actions, and decisions.
"""

import re
import os
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class ExtractedEntity:
    """Represents a named entity extracted from text"""
    text: str
    label: str  # PERSON, ORGANIZATION, PRODUCT, LOCATION, etc.
    start_char: int
    end_char: int
    confidence: float = 0.8


@dataclass
class ExtractedConcept:
    """Represents a key concept or phrase"""
    text: str
    importance_score: float  # 0-1
    frequency: int = 1
    positions: List[int] = None


@dataclass
class ExtractedQuestion:
    """Represents a question identified in the text"""
    text: str
    question_type: str  # "what", "how", "why", "when", "where", "who", "which", "yes_no"
    start_char: int
    end_char: int


@dataclass
class ExtractedAction:
    """Represents an action item or task"""
    text: str
    action_verb: str
    confidence: float
    start_char: int
    end_char: int


@dataclass
class ExtractedDecision:
    """Represents a decision or commitment"""
    text: str
    decision_type: str  # "choice", "commitment", "plan"
    confidence: float
    start_char: int
    end_char: int


@dataclass
class ExtractedFeatures:
    """Complete feature extraction output"""
    entities: List[ExtractedEntity]
    concepts: List[ExtractedConcept]
    questions: List[ExtractedQuestion]
    actions: List[ExtractedAction]
    decisions: List[ExtractedDecision]
    key_phrases: List[str]
    sentences: List[str]
    metadata: Dict
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'entities': [asdict(e) for e in self.entities],
            'concepts': [asdict(c) for c in self.concepts],
            'questions': [asdict(q) for q in self.questions],
            'actions': [asdict(a) for a in self.actions],
            'decisions': [asdict(d) for d in self.decisions],
            'key_phrases': self.key_phrases,
            'sentences': self.sentences,
            'metadata': self.metadata
        }


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


def _split_into_sentences(text: str) -> List[str]:
    """Simple sentence splitting using regex"""
    # Split on sentence-ending punctuation
    sentences = re.split(r'[.!?]+', text)
    # Clean up and filter empty strings
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences


class FeatureExtractor:
    """
    Extracts structured features from transcript text using LLM.
    
    This is step 1 of the graph generation pipeline:
    1. Feature Extraction (this module) - Extract entities, concepts, patterns using LLM
    2. Semantic Clustering - Group related features
    3. Graph Generation - Create graph structure from clustered features
    """
    
    def __init__(self, 
                 llm_model: str = "claude-3-5-haiku-20241022",
                 anthropic_api_key: Optional[str] = None):
        """
        Initialize the feature extractor.
        
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
    
    def _create_extraction_prompt(self, text: str) -> str:
        """Create prompt for LLM to extract features"""
        prompt = f"""Analyze the following transcript text and extract structured features. Return ONLY valid JSON, no explanations.

Text to analyze:
---
{text}
---

Extract the following features and return as JSON:

{{
  "entities": [
    {{
      "text": "entity text",
      "label": "PERSON|ORGANIZATION|PRODUCT|LOCATION|TECHNOLOGY|EVENT|OTHER",
      "start_char": 0,
      "end_char": 10,
      "confidence": 0.9
    }}
  ],
  "concepts": [
    {{
      "text": "key concept or phrase",
      "importance_score": 0.8,
      "frequency": 1,
      "positions": [0]
    }}
  ],
  "questions": [
    {{
      "text": "question text",
      "question_type": "what|how|why|when|where|who|which|yes_no",
      "start_char": 0,
      "end_char": 20
    }}
  ],
  "actions": [
    {{
      "text": "action item sentence",
      "action_verb": "main verb",
      "confidence": 0.8,
      "start_char": 0,
      "end_char": 30
    }}
  ],
  "decisions": [
    {{
      "text": "decision statement",
      "decision_type": "choice|commitment|plan",
      "confidence": 0.8,
      "start_char": 0,
      "end_char": 25
    }}
  ],
  "key_phrases": ["phrase1", "phrase2", "phrase3"]
}}

Guidelines:
- Extract named entities: people, organizations, products, technologies, locations
- Extract important concepts and topics (noun phrases, key terms)
- Identify all questions (sentences ending with "?" or starting with question words)
- Identify action items (tasks, to-dos, things to do)
- Identify decisions (choices made, commitments, plans)
- For key_phrases, extract 5-15 most important phrases
- Use character positions (start_char, end_char) to locate text in the original
- Set importance_score for concepts (0.0-1.0), higher for more important/repeated concepts
- Set confidence scores (0.0-1.0) for entities, actions, decisions

Return ONLY the JSON object, no markdown, no explanations."""
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """Call Anthropic Claude API"""
        message = self.client.messages.create(
            model=self.llm_model,
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        return message.content[0].text
    
    def extract(self, text: str, metadata: Optional[Dict] = None) -> ExtractedFeatures:
        """
        Extract all features from the given text using LLM.
        
        Args:
            text: Input transcript text
            metadata: Optional metadata (timestamp, session_id, etc.)
            
        Returns:
            ExtractedFeatures object containing all extracted features
        """
        if not text or not text.strip():
            return ExtractedFeatures(
                entities=[],
                concepts=[],
                questions=[],
                actions=[],
                decisions=[],
                key_phrases=[],
                sentences=[],
                metadata=metadata or {}
            )
        
        # Create prompt and call LLM
        prompt = self._create_extraction_prompt(text)
        
        try:
            response_text = self._call_llm(prompt)
        except Exception as e:
            raise RuntimeError(f"Failed to call Claude API for feature extraction: {e}")
        
        # Extract JSON from response
        json_text = _extract_json_from_response(response_text)
        
        try:
            extracted_data = json.loads(json_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}\nResponse was: {response_text[:500]}")
        
        # Parse extracted data into structured objects
        entities = [
            ExtractedEntity(
                text=e['text'],
                label=e.get('label', 'OTHER'),
                start_char=e.get('start_char', 0),
                end_char=e.get('end_char', len(e['text'])),
                confidence=e.get('confidence', 0.8)
            )
            for e in extracted_data.get('entities', [])
        ]
        
        concepts = [
            ExtractedConcept(
                text=c['text'],
                importance_score=c.get('importance_score', 0.5),
                frequency=c.get('frequency', 1),
                positions=c.get('positions', [0])
            )
            for c in extracted_data.get('concepts', [])
        ]
        
        questions = [
            ExtractedQuestion(
                text=q['text'],
                question_type=q.get('question_type', 'yes_no'),
                start_char=q.get('start_char', 0),
                end_char=q.get('end_char', len(q['text']))
            )
            for q in extracted_data.get('questions', [])
        ]
        
        actions = [
            ExtractedAction(
                text=a['text'],
                action_verb=a.get('action_verb', 'act'),
                confidence=a.get('confidence', 0.8),
                start_char=a.get('start_char', 0),
                end_char=a.get('end_char', len(a['text']))
            )
            for a in extracted_data.get('actions', [])
        ]
        
        decisions = [
            ExtractedDecision(
                text=d['text'],
                decision_type=d.get('decision_type', 'choice'),
                confidence=d.get('confidence', 0.8),
                start_char=d.get('start_char', 0),
                end_char=d.get('end_char', len(d['text']))
            )
            for d in extracted_data.get('decisions', [])
        ]
        
        key_phrases = extracted_data.get('key_phrases', [])
        sentences = _split_into_sentences(text)
        
        extract_metadata = {
            'text_length': len(text),
            'word_count': len(text.split()),
            'sentence_count': len(sentences),
            'extraction_timestamp': datetime.utcnow().isoformat() + 'Z',
            'llm_model': self.llm_model,
            **(metadata or {})
        }
        
        return ExtractedFeatures(
            entities=entities,
            concepts=concepts,
            questions=questions,
            actions=actions,
            decisions=decisions,
            key_phrases=key_phrases,
            sentences=sentences,
            metadata=extract_metadata
        )


def extract_features(text: str, 
                    llm_model: str = "claude-3-5-haiku-20241022",
                    metadata: Optional[Dict] = None) -> Dict:
    """
    Convenience function to extract features from text using Claude.
    
    Args:
        text: Input transcript text
        llm_model: Claude model name
        metadata: Optional metadata dictionary
        
    Returns:
        Dictionary representation of extracted features
    """
    extractor = FeatureExtractor(llm_model=llm_model)
    features = extractor.extract(text, metadata)
    return features.to_dict()


if __name__ == "__main__":
    # Test the feature extractor
    test_text = """
    Okay, so let's talk about the mobile app redesign. I think we really need to focus on user experience, 
    especially for first-time users. The onboarding flow is confusing right now. 
    
    What do you think about using React Native? We should test it on iPhone and Android devices. 
    We decided to go with a modern design system. Let's schedule a meeting with the design team next week.
    """
    
    try:
        extractor = FeatureExtractor()
        features = extractor.extract(test_text)
        
        print("=== Extracted Features ===\n")
        print(f"Entities ({len(features.entities)}):")
        for entity in features.entities:
            print(f"  - {entity.text} ({entity.label}) confidence: {entity.confidence:.2f}")
        
        print(f"\nConcepts ({len(features.concepts)}):")
        for concept in features.concepts[:10]:
            print(f"  - {concept.text} (importance: {concept.importance_score:.2f}, freq: {concept.frequency})")
        
        print(f"\nQuestions ({len(features.questions)}):")
        for question in features.questions:
            print(f"  - {question.text} ({question.question_type})")
        
        print(f"\nActions ({len(features.actions)}):")
        for action in features.actions:
            print(f"  - {action.text} (verb: {action.action_verb})")
        
        print(f"\nDecisions ({len(features.decisions)}):")
        for decision in features.decisions:
            print(f"  - {decision.text} (type: {decision.decision_type})")
        
        print(f"\nKey Phrases ({len(features.key_phrases)}):")
        for phrase in features.key_phrases[:10]:
            print(f"  - {phrase}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
