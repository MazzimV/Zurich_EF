"""
Feature Extraction Module

This module extracts structured features from transcript text before semantic clustering/graph generation.
It performs NLP analysis to identify entities, key phrases, concepts, questions, actions, and decisions.
"""

import re
import os
import json
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import spacy
from rake_nltk import Rake
import nltk
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Download required NLTK data (run once)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)


@dataclass
class ExtractedEntity:
    """Represents a named entity extracted from text"""
    text: str
    label: str  # PERSON, ORG, PRODUCT, GPE, etc.
    start_char: int
    end_char: int
    confidence: float = 0.8


@dataclass
class ExtractedConcept:
    """Represents a key concept or phrase"""
    text: str
    importance_score: float  # 0-1 based on TF-IDF, position, frequency
    frequency: int = 1
    positions: List[int] = None  # Character positions where mentioned


@dataclass
class ExtractedQuestion:
    """Represents a question identified in the text"""
    text: str
    question_type: str  # "what", "how", "why", "when", "where", "who", "yes_no"
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


class FeatureExtractor:
    """
    Extracts structured features from transcript text.
    
    This is step 1 of the graph generation pipeline:
    1. Feature Extraction (this module) - Extract entities, concepts, patterns
    2. Semantic Clustering - Group related features
    3. Graph Generation - Create graph structure from clustered features
    """
    
    def __init__(self, spacy_model: str = "en_core_web_sm", 
                 use_llm_filter: bool = True,
                 anthropic_api_key: Optional[str] = None):
        """
        Initialize the feature extractor.
        
        Args:
            spacy_model: Name of spaCy model to load. Defaults to "en_core_web_sm"
                       For better performance, use "en_core_web_md" or "en_core_web_lg"
            use_llm_filter: Whether to use Anthropic LLM to filter key phrases for relevance
            anthropic_api_key: Anthropic API key (if not provided, reads from ANTHROPIC_API_KEY env var)
        """
        try:
            self.nlp = spacy.load(spacy_model)
        except OSError:
            raise ValueError(
                f"spaCy model '{spacy_model}' not found. "
                f"Install it with: python -m spacy download {spacy_model}"
            )
        
        self.rake = Rake()
        self.use_llm_filter = use_llm_filter
        
        # Initialize Anthropic client if LLM filtering is enabled
        self.anthropic_client = None
        if use_llm_filter:
            try:
                from anthropic import Anthropic
                api_key = anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')
                if api_key:
                    self.anthropic_client = Anthropic(api_key=api_key)
                else:
                    print("Warning: ANTHROPIC_API_KEY not found. LLM filtering disabled.")
                    self.use_llm_filter = False
            except ImportError:
                print("Warning: anthropic package not installed. LLM filtering disabled.")
                self.use_llm_filter = False
        
        # Patterns for detecting actions
        self.action_patterns = [
            r"\b(?:we|I|let's|we should|we need to|we must|we have to)\s+(?:do|make|create|build|implement|add|fix|update|change|test|review|schedule|plan)",
            r"\b(?:need to|must|should|have to|going to|plan to)\s+\w+",
            r"\baction items?|next steps?|todo|task|tasks",
        ]
        
        # Patterns for detecting decisions
        self.decision_patterns = [
            r"\b(?:we decided|we chose|we'll use|we're going with|let's go with|we'll go with)",
            r"\b(?:decision|decided|chose|selected|picked|settled on)",
            r"\b(?:will use|will go with|will choose)",
        ]
        
        # Question words
        self.question_words = ["what", "how", "why", "when", "where", "who", "which"]
        
    def extract(self, text: str, metadata: Optional[Dict] = None) -> ExtractedFeatures:
        """
        Extract all features from the given text.
        
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
        
        # Process with spaCy
        doc = self.nlp(text)
        
        # Extract different feature types
        entities = self._extract_entities(doc)
        concepts = self._extract_concepts(doc, text)
        questions = self._extract_questions(doc, text)
        actions = self._extract_actions(doc, text)
        decisions = self._extract_decisions(doc, text)
        key_phrases = self._extract_key_phrases(text)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        
        extract_metadata = {
            'text_length': len(text),
            'word_count': len(doc),
            'sentence_count': len(sentences),
            'extraction_timestamp': datetime.utcnow().isoformat() + 'Z',
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
    
    def _extract_entities(self, doc) -> List[ExtractedEntity]:
        """Extract named entities (people, organizations, products, etc.)"""
        entities = []
        for ent in doc.ents:
            # Map spaCy labels to our labels
            label_mapping = {
                'PERSON': 'PERSON',
                'ORG': 'ORGANIZATION',
                'GPE': 'LOCATION',
                'PRODUCT': 'PRODUCT',
                'EVENT': 'EVENT',
                'WORK_OF_ART': 'WORK_OF_ART',
                'LAW': 'LAW',
                'LANGUAGE': 'LANGUAGE',
            }
            
            if ent.label_ in label_mapping:
                entities.append(ExtractedEntity(
                    text=ent.text,
                    label=label_mapping[ent.label_],
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                    confidence=0.9 if ent.label_ in ['PERSON', 'ORG'] else 0.8
                ))
        
        return entities
    
    def _extract_concepts(self, doc, text: str) -> List[ExtractedConcept]:
        """
        Extract key concepts and phrases from the text.
        Uses noun phrases and important terms.
        """
        concepts_dict: Dict[str, ExtractedConcept] = {}
        
        # Extract noun phrases
        for chunk in doc.noun_chunks:
            # Filter out common stop words and pronouns
            if len(chunk.text.split()) > 1:  # Multi-word phrases only
                normalized = chunk.text.lower().strip()
                
                # Skip if it's mostly stop words
                if self._is_meaningful_phrase(normalized):
                    if normalized not in concepts_dict:
                        # Calculate initial importance based on position and length
                        importance = self._calculate_concept_importance(chunk, text)
                        concepts_dict[normalized] = ExtractedConcept(
                            text=chunk.text,  # Keep original case
                            importance_score=importance,
                            frequency=1,
                            positions=[chunk.start_char]
                        )
                    else:
                        # Update existing concept
                        concepts_dict[normalized].frequency += 1
                        concepts_dict[normalized].positions.append(chunk.start_char)
                        # Increase importance with frequency
                        concepts_dict[normalized].importance_score = min(
                            1.0,
                            concepts_dict[normalized].importance_score + 0.1
                        )
        
        # Also extract important single-word nouns (capitalized or important terms)
        for token in doc:
            if (token.pos_ == "NOUN" and 
                token.is_alpha and 
                not token.is_stop and
                len(token.text) > 3):
                
                normalized = token.text.lower()
                if normalized not in concepts_dict:
                    importance = 0.3  # Lower importance for single words
                    concepts_dict[normalized] = ExtractedConcept(
                        text=token.text,
                        importance_score=importance,
                        frequency=1,
                        positions=[token.idx]
                    )
        
        # Convert to list and sort by importance
        concepts = list(concepts_dict.values())
        concepts.sort(key=lambda x: x.importance_score, reverse=True)
        
        return concepts[:30]  # Limit to top 30 concepts
    
    def _extract_questions(self, doc, text: str) -> List[ExtractedQuestion]:
        """Extract questions from the text"""
        questions = []
        
        for sent in doc.sents:
            sent_text = sent.text.strip()
            
            # Check if sentence is a question
            if sent_text.endswith('?') or any(sent_text.lower().startswith(qw) for qw in self.question_words):
                # Determine question type
                question_type = "yes_no"
                for qw in self.question_words:
                    if sent_text.lower().startswith(qw):
                        question_type = qw
                        break
                
                questions.append(ExtractedQuestion(
                    text=sent_text,
                    question_type=question_type,
                    start_char=sent.start_char,
                    end_char=sent.end_char
                ))
        
        return questions
    
    def _extract_actions(self, doc, text: str) -> List[ExtractedAction]:
        """Extract action items and tasks"""
        actions = []
        
        for sent in doc.sents:
            sent_text = sent.text.strip()
            sent_lower = sent_text.lower()
            
            # Check against action patterns
            for pattern in self.action_patterns:
                if re.search(pattern, sent_lower, re.IGNORECASE):
                    # Try to find the main action verb
                    action_verb = self._find_action_verb(sent)
                    
                    actions.append(ExtractedAction(
                        text=sent_text,
                        action_verb=action_verb,
                        confidence=0.8,
                        start_char=sent.start_char,
                        end_char=sent.end_char
                    ))
                    break  # Only add once per sentence
        
        return actions
    
    def _extract_decisions(self, doc, text: str) -> List[ExtractedDecision]:
        """Extract decisions and commitments"""
        decisions = []
        
        for sent in doc.sents:
            sent_text = sent.text.strip()
            sent_lower = sent_text.lower()
            
            # Check against decision patterns
            for pattern in self.decision_patterns:
                if re.search(pattern, sent_lower, re.IGNORECASE):
                    # Determine decision type
                    decision_type = "choice"
                    if "decided" in sent_lower or "decision" in sent_lower:
                        decision_type = "choice"
                    elif "commit" in sent_lower or "going to" in sent_lower:
                        decision_type = "commitment"
                    elif "plan" in sent_lower:
                        decision_type = "plan"
                    
                    decisions.append(ExtractedDecision(
                        text=sent_text,
                        decision_type=decision_type,
                        confidence=0.8,
                        start_char=sent.start_char,
                        end_char=sent.end_char
                    ))
                    break
        
        return decisions
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """
        Extract key phrases using RAKE algorithm, optionally filtered by LLM for relevance.
        
        Args:
            text: Input text to extract phrases from
            
        Returns:
            List of relevant key phrases
        """
        self.rake.extract_keywords_from_text(text)
        phrases = self.rake.get_ranked_phrases()[:15]  # Top 15 key phrases
        
        # Filter using LLM if enabled
        if self.use_llm_filter and self.anthropic_client and phrases:
            phrases = self._filter_key_phrases_with_llm(phrases, text)
        
        return phrases
    
    def _filter_key_phrases_with_llm(self, phrases: List[str], context_text: str) -> List[str]:
        """
        Use Anthropic LLM to filter key phrases and keep only relevant ones.
        
        Args:
            phrases: List of extracted key phrases to filter
            context_text: Original text context for better relevance judgment
            
        Returns:
            Filtered list of relevant key phrases
        """
        if not phrases or not self.anthropic_client:
            return phrases
        
        try:
            # Build prompt for LLM to evaluate relevance
            prompt = f"""You are analyzing key phrases extracted from a brainstorming discussion transcript.

ORIGINAL TEXT:
{context_text[:1000]}

EXTRACTED KEY PHRASES:
{json.dumps(phrases, indent=2)}

Your task: Identify which key phrases are ACTUALLY RELEVANT and meaningful for understanding the discussion topics. 

Filter out:
- Generic words/phrases ("okay", "let", "think", "really need")
- Incomplete phrases ("confusing right", "time users")
- Common filler words
- Phrases that don't convey substantive meaning

Keep only:
- Specific topics, concepts, or meaningful phrases
- Technical terms, product names, features
- Actionable items or decisions
- Important entities or themes

Return ONLY a JSON array of the relevant phrases, nothing else. Format: ["phrase1", "phrase2", ...]

RELEVANT PHRASES:"""
            
            message = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",  # Fast and cheap model
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            response_text = message.content[0].text.strip()
            
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                filtered_phrases = json.loads(json_match.group(0))
                # Ensure all returned phrases were in original list
                filtered_phrases = [p for p in filtered_phrases if p in phrases]
                return filtered_phrases
            else:
                # Fallback: return original if parsing fails
                print(f"Warning: Could not parse LLM response, using original phrases")
                return phrases
                
        except Exception as e:
            print(f"Warning: LLM filtering failed ({str(e)}), using original phrases")
            return phrases
    
    def _is_meaningful_phrase(self, phrase: str) -> bool:
        """Check if a phrase is meaningful (not just stop words)"""
        stop_words = {'the', 'a', 'an', 'this', 'that', 'these', 'those', 'it', 'they', 'we', 'you'}
        words = phrase.split()
        meaningful_words = [w for w in words if w not in stop_words]
        return len(meaningful_words) > 0
    
    def _calculate_concept_importance(self, chunk, text: str) -> float:
        """
        Calculate importance score for a concept based on:
        - Position in text (earlier = more important)
        - Length (longer phrases might be more specific)
        - Sentence position
        """
        # Base importance
        importance = 0.5
        
        # Position bonus (earlier in text = higher importance)
        position_ratio = chunk.start_char / max(len(text), 1)
        if position_ratio < 0.3:  # First 30% of text
            importance += 0.2
        elif position_ratio < 0.6:  # First 60%
            importance += 0.1
        
        # Length bonus (longer phrases are often more specific)
        word_count = len(chunk.text.split())
        if word_count >= 3:
            importance += 0.1
        
        return min(1.0, importance)
    
    def _find_action_verb(self, sent) -> str:
        """Find the main action verb in a sentence"""
        for token in sent:
            if token.pos_ == "VERB" and not token.is_stop:
                return token.lemma_  # Return base form
        return "act"  # Default


def extract_features(text: str, metadata: Optional[Dict] = None) -> Dict:
    """
    Convenience function to extract features from text.
    
    Args:
        text: Input transcript text
        metadata: Optional metadata dictionary
        
    Returns:
        Dictionary representation of extracted features
    """
    extractor = FeatureExtractor()
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
    
    extractor = FeatureExtractor()
    features = extractor.extract(test_text)
    
    print("=== Extracted Features ===\n")
    print(f"Entities ({len(features.entities)}):")
    for entity in features.entities:
        print(f"  - {entity.text} ({entity.label})")
    
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

