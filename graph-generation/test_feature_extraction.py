"""
Test script for feature extraction module
"""

import json
import os
from feature_extractor import FeatureExtractor, extract_features
from dotenv import load_dotenv

load_dotenv()

def test_basic_extraction():
    """Test basic feature extraction"""
    print("=" * 60)
    print("Testing Basic Feature Extraction")
    print("=" * 60)
    
    test_text = """
    Okay, so let's talk about the mobile app redesign. I think we really need to focus on user experience, 
    especially for first-time users. The onboarding flow is confusing right now. 
    
    What do you think about using React Native? We should test it on iPhone and Android devices. 
    We decided to go with a modern design system. Let's schedule a meeting with the design team next week.
    """
    
    extractor = FeatureExtractor()
    features = extractor.extract(test_text, metadata={'session_id': 'test-123'})
    
    print(f"\nText length: {len(test_text)} characters")
    print(f"Word count: {features.metadata['word_count']}")
    print(f"Sentence count: {features.metadata['sentence_count']}")
    
    print(f"\n{'='*60}")
    print(f"ENTITIES ({len(features.entities)})")
    print(f"{'='*60}")
    for entity in features.entities:
        print(f"  {entity.text:<30} [{entity.label}] confidence: {entity.confidence:.2f}")
    
    print(f"\n{'='*60}")
    print(f"CONCEPTS ({len(features.concepts)})")
    print(f"{'='*60}")
    for concept in features.concepts[:15]:
        print(f"  {concept.text:<40} importance: {concept.importance_score:.2f} (freq: {concept.frequency})")
    
    print(f"\n{'='*60}")
    print(f"QUESTIONS ({len(features.questions)})")
    print(f"{'='*60}")
    for question in features.questions:
        print(f"  [{question.question_type}] {question.text}")
    
    print(f"\n{'='*60}")
    print(f"ACTIONS ({len(features.actions)})")
    print(f"{'='*60}")
    for action in features.actions:
        print(f"  [{action.action_verb}] {action.text[:80]}")
    
    print(f"\n{'='*60}")
    print(f"DECISIONS ({len(features.decisions)})")
    print(f"{'='*60}")
    for decision in features.decisions:
        print(f"  [{decision.decision_type}] {decision.text[:80]}")
    
    print(f"\n{'='*60}")
    print(f"KEY PHRASES ({len(features.key_phrases)})")
    print(f"{'='*60}")
    for phrase in features.key_phrases[:10]:
        print(f"  - {phrase}")
    
    return features


def test_llm_filtering():
    """Test LLM filtering of key phrases"""
    print("\n\n")
    print("=" * 60)
    print("Testing LLM Key Phrase Filtering")
    print("=" * 60)
    
    test_text = """
    Okay, so let's talk about the mobile app redesign. I think we really need to focus on user experience, 
    especially for first-time users. The onboarding flow is confusing right now. 
    
    What do you think about using React Native? We should test it on iPhone and Android devices. 
    We decided to go with a modern design system. Let's schedule a meeting with the design team next week.
    """
    
    # Test without LLM filter (baseline)
    print("\n--- WITHOUT LLM FILTER (Baseline) ---")
    extractor_no_filter = FeatureExtractor(use_llm_filter=False)
    features_no_filter = extractor_no_filter.extract(test_text)
    print(f"Key phrases ({len(features_no_filter.key_phrases)}):")
    for phrase in features_no_filter.key_phrases:
        print(f"  - {phrase}")
    
    # Test with LLM filter
    print("\n--- WITH LLM FILTER (Filtered) ---")
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("⚠ ANTHROPIC_API_KEY not found. Cannot test LLM filtering.")
        print("   Set your API key in .env file or environment variable.")
        return None
    
    extractor_with_filter = FeatureExtractor(use_llm_filter=True, anthropic_api_key=api_key)
    features_with_filter = extractor_with_filter.extract(test_text)
    print(f"Key phrases ({len(features_with_filter.key_phrases)}):")
    for phrase in features_with_filter.key_phrases:
        print(f"  ✓ {phrase}")
    
    # Show comparison
    print(f"\n--- COMPARISON ---")
    print(f"Before filtering: {len(features_no_filter.key_phrases)} phrases")
    print(f"After filtering:  {len(features_with_filter.key_phrases)} phrases")
    print(f"Removed:          {len(features_no_filter.key_phrases) - len(features_with_filter.key_phrases)} phrases")
    
    removed = set(features_no_filter.key_phrases) - set(features_with_filter.key_phrases)
    if removed:
        print(f"\nFiltered out:")
        for phrase in removed:
            print(f"  ✗ {phrase}")
    
    return features_with_filter


def test_with_sample_transcript():
    """Test with sample transcript from shared/examples"""
    print("\n\n")
    print("=" * 60)
    print("Testing with Sample Transcript")
    print("=" * 60)
    
    # Load sample transcript
    try:
        with open('../shared/examples/sample-transcript.json', 'r') as f:
            transcript_data = json.load(f)
        
        text = transcript_data['text']
        extractor = FeatureExtractor()
        features = extractor.extract(
            text, 
            metadata={
                'session_id': transcript_data.get('session_id'),
                'timestamp': transcript_data.get('timestamp'),
                'chunk_id': transcript_data.get('chunk_id')
            }
        )
        
        print(f"\nExtracted {len(features.concepts)} concepts, {len(features.entities)} entities")
        print(f"Found {len(features.actions)} actions and {len(features.decisions)} decisions")
        
        # Show top concepts
        print("\nTop 5 Concepts by Importance:")
        for concept in features.concepts[:5]:
            print(f"  - {concept.text} (score: {concept.importance_score:.2f})")
        
        # Convert to dict and save (for inspection)
        features_dict = features.to_dict()
        with open('test_features_output.json', 'w') as f:
            json.dump(features_dict, f, indent=2)
        
        print("\n✓ Features saved to test_features_output.json")
        
        return features
        
    except FileNotFoundError:
        print("⚠ Sample transcript file not found, skipping this test")
        return None


def test_empty_text():
    """Test edge case with empty text"""
    print("\n\n")
    print("=" * 60)
    print("Testing Edge Case: Empty Text")
    print("=" * 60)
    
    extractor = FeatureExtractor()
    features = extractor.extract("")
    
    assert len(features.entities) == 0
    assert len(features.concepts) == 0
    assert len(features.questions) == 0
    print("✓ Empty text handled correctly")


if __name__ == "__main__":
    try:
        # Basic extraction test
        features1 = test_basic_extraction()
        
        # Test LLM filtering
        features_filtered = test_llm_filtering()
        
        # Test with sample transcript
        features2 = test_with_sample_transcript()
        
        # Edge case test
        test_empty_text()
        
        print("\n\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

