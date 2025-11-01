# Feature Extraction Module

## Overview

The feature extraction module is the **first step** in the graph generation pipeline. It performs NLP analysis on transcript text to extract structured features before semantic clustering and graph generation.

## Pipeline Architecture

```
Transcript Text
    ↓
[1] Feature Extraction (this module)
    → Entities, Concepts, Questions, Actions, Decisions
    ↓
[2] Semantic Clustering (future)
    → Group related features
    ↓
[3] Graph Generation (LLM)
    → Create graph structure
```

## What Gets Extracted

### 1. Entities
- **Named entities**: People, organizations, locations, products
- **Labels**: PERSON, ORGANIZATION, LOCATION, PRODUCT, EVENT
- **Metadata**: Text, position in document, confidence score

### 2. Concepts
- **Noun phrases**: Multi-word phrases that represent topics/concepts
- **Important terms**: Significant single-word nouns
- **Scoring**: Importance score based on position, frequency, and length
- **Metadata**: Frequency count, character positions

### 3. Questions
- **Question detection**: Sentences ending with "?" or starting with question words
- **Question types**: what, how, why, when, where, who, which, yes_no
- **Metadata**: Full question text, position

### 4. Actions
- **Action items**: Tasks and to-dos mentioned in discussion
- **Pattern matching**: Detects phrases like "we should", "need to", "let's"
- **Metadata**: Action verb, confidence, sentence text

### 5. Decisions
- **Decision detection**: Identifies commitments and choices
- **Decision types**: choice, commitment, plan
- **Pattern matching**: Detects phrases like "we decided", "we'll use", "going with"
- **Metadata**: Decision type, confidence, sentence text

### 6. Key Phrases
- **RAKE algorithm**: Extracts important phrases automatically
- **Ranking**: Phrases ranked by importance
- **Output**: Top 15 key phrases

## Usage

### Basic Usage

```python
from feature_extractor import FeatureExtractor

extractor = FeatureExtractor()
features = extractor.extract("Your transcript text here")

# Access extracted features
print(f"Found {len(features.entities)} entities")
print(f"Found {len(features.concepts)} concepts")
print(f"Found {len(features.actions)} actions")
```

### With Metadata

```python
features = extractor.extract(
    text,
    metadata={
        'session_id': 'session-123',
        'timestamp': '2025-11-01T10:30:00Z',
        'chunk_id': 1
    }
)
```

### Convert to Dictionary (JSON serializable)

```python
features_dict = features.to_dict()
# Can be serialized to JSON for API responses
```

## Output Structure

```python
ExtractedFeatures(
    entities: List[ExtractedEntity],      # Named entities
    concepts: List[ExtractedConcept],      # Key concepts with importance scores
    questions: List[ExtractedQuestion],    # Questions identified
    actions: List[ExtractedAction],        # Action items
    decisions: List[ExtractedDecision],    # Decisions made
    key_phrases: List[str],                # RAKE-extracted phrases
    sentences: List[str],                  # Sentence segmentation
    metadata: Dict                         # Extraction metadata
)
```

## Installation

### Prerequisites

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Download spaCy language model:
```bash
python -m spacy download en_core_web_sm
```

For better accuracy (recommended):
```bash
python -m spacy download en_core_web_md
```

### Verify Installation

```bash
python test_feature_extraction.py
```

## Configuration

### Using Different spaCy Models

```python
# Small model (faster, less accurate)
extractor = FeatureExtractor(spacy_model="en_core_web_sm")

# Medium model (balanced, recommended)
extractor = FeatureExtractor(spacy_model="en_core_web_md")

# Large model (slower, most accurate)
extractor = FeatureExtractor(spacy_model="en_core_web_lg")
```

## Examples

### Example Input

```
Okay, so let's talk about the mobile app redesign. I think we really need to focus on user experience, 
especially for first-time users. The onboarding flow is confusing right now. 

What do you think about using React Native? We should test it on iPhone and Android devices. 
We decided to go with a modern design system. Let's schedule a meeting with the design team next week.
```

### Example Output (Key Features)

**Entities:**
- "React Native" (PRODUCT)
- "iPhone" (PRODUCT)
- "Android" (PRODUCT)

**Concepts:**
- "mobile app redesign" (importance: 0.9)
- "user experience" (importance: 0.8)
- "first-time users" (importance: 0.7)
- "onboarding flow" (importance: 0.7)
- "design system" (importance: 0.6)

**Questions:**
- "What do you think about using React Native?" (type: what)

**Actions:**
- "We should test it on iPhone and Android devices" (verb: test)
- "Let's schedule a meeting with the design team next week" (verb: schedule)

**Decisions:**
- "We decided to go with a modern design system" (type: choice)

## Next Steps

After feature extraction, the next step is **semantic clustering**:

1. Group related concepts (e.g., "user experience" + "UX" + "usability")
2. Link entities to concepts (e.g., "React Native" → "mobile app")
3. Create concept hierarchies
4. Prepare features for LLM graph generation

## Performance

- **Speed**: ~100-500ms per transcript chunk (depending on text length and model)
- **Accuracy**: Medium model provides good balance of speed and accuracy
- **Memory**: Small model uses ~50MB, medium uses ~200MB

## Limitations

- Designed for English text only
- Entity recognition may miss domain-specific terms
- Action/decision detection relies on pattern matching (may miss implicit actions)
- Concept extraction focuses on noun phrases (may miss verb-based concepts)

## Future Improvements

- [ ] Support for multiple languages
- [ ] Domain-specific entity recognition
- [ ] Better implicit action detection (using dependency parsing)
- [ ] Temporal relationship detection ("after", "before", "then")
- [ ] Sentiment analysis for concepts
- [ ] Relationship extraction (who said what, who owns what)

