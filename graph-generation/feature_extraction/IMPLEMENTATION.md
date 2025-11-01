# Feature Extraction Implementation

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set API Key

```bash
export ANTHROPIC_API_KEY=your-key-here
```

### 3. Basic Usage

```python
from feature_extractor import FeatureExtractor

# Initialize (uses ANTHROPIC_API_KEY from environment by default)
extractor = FeatureExtractor()

# Extract features
features = extractor.extract("""
We should redesign the mobile app. Let's focus on user experience.
What framework should we use? React Native looks good.
""")

# Access results
print(f"Entities: {len(features.entities)}")
print(f"Concepts: {len(features.concepts)}")
print(f"Actions: {len(features.actions)}")
```

## Configuration

### Claude Model Options

**Default (fast, cheap)**:
```python
extractor = FeatureExtractor(
    llm_model="claude-3-5-haiku-20241022"  # Default - fast and cheap
)
```

**Higher quality**:
```python
extractor = FeatureExtractor(
    llm_model="claude-3-5-sonnet-20241022"  # Better quality, slower
)
```

### With Metadata

```python
features = extractor.extract(
    text,
    metadata={
        'session_id': 'session-123',
        'timestamp': '2025-11-01T10:30:00Z'
    }
)
```

## Extracted Features

The `extract()` method returns an `ExtractedFeatures` object with:

- **`entities`**: Named entities (people, orgs, products) - `List[ExtractedEntity]`
- **`concepts`**: Key concepts with importance scores - `List[ExtractedConcept]`
- **`questions`**: Questions identified - `List[ExtractedQuestion]`
- **`actions`**: Action items/tasks - `List[ExtractedAction]`
- **`decisions`**: Decisions made - `List[ExtractedDecision]`
- **`key_phrases`**: Important phrases - `List[str]`
- **`sentences`**: Sentence segments - `List[str]`
- **`metadata`**: Extraction metadata - `Dict`

## Convert to JSON

```python
features_dict = features.to_dict()
# Can be serialized: json.dumps(features_dict)
```

## Testing

```bash
# Test with sample data
python test_feature_extraction.py

# Test module directly
python feature_extractor.py
```

## Troubleshooting

**Error**: `ANTHROPIC_API_KEY not found`
- Set API key: `export ANTHROPIC_API_KEY=your-key`

**Error**: `TypeError: Client.__init__() got an unexpected keyword argument 'proxies'`
- Upgrade: `pip install --upgrade anthropic httpx`

**Error**: `Failed to parse LLM response as JSON`
- Check API key and network connection
- Verify Claude response format

## Performance

- **Speed**: ~1-2 seconds per extraction (with Claude 3.5 Haiku)
- **Cost**: ~$0.001-0.002 per typical transcript (200 words)

## Integration

```python
# Step 1: Extract features
from feature_extractor import FeatureExtractor
extractor = FeatureExtractor()
features = extractor.extract(transcript_text)

# Step 2: Use in pipeline (future: clustering → graph generation)
# clusters = clusterer.cluster(features)
# graph = generator.generate(features, previous_graph)
```
