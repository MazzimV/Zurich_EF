# Feature Extraction Module

This module extracts structured features from transcript text using Claude LLM.

## Quick Start

See [IMPLEMENTATION.md](./IMPLEMENTATION.md) for detailed usage instructions.

## Files

- `feature_extractor.py` - Main feature extraction implementation
- `test_feature_extraction.py` - Test script
- `IMPLEMENTATION.md` - Implementation guide
- `test_features_output.json` - Sample test output

## Usage

```python
from feature_extraction import FeatureExtractor

extractor = FeatureExtractor()
features = extractor.extract("Your transcript text here")
```

