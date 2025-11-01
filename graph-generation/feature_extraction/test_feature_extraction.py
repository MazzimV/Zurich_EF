"""
Test script for graph generation module (Claude-based)
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from feature_extractor import FeatureExtractor, generate_graph
from dotenv import load_dotenv

load_dotenv()


def test_basic_graph_generation():
    """Test basic graph generation with no previous graph"""
    print("=" * 60)
    print("Testing Basic Graph Generation (First Chunk)")
    print("=" * 60)
    
    # Check for API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("⚠ API key not found!")
        print("   Set ANTHROPIC_API_KEY in .env file or environment variable.")
        return None
    
    test_text = """
    Okay, so let's talk about the mobile app redesign. I think we really need to focus on user experience, 
    especially for first-time users. The onboarding flow is confusing right now. 
    
    What do you think about using React Native? We should test it on iPhone and Android devices. 
    We decided to go with a modern design system. Let's schedule a meeting with the design team next week.
    """
    
    extractor = FeatureExtractor()
    graph = extractor.generate_graph(
        test_text,
        previous_graph=None,
        metadata={'session_id': 'test-123', 'chunk_id': 1}
    )
    
    print(f"\nClaude Model: {graph.get('metadata', {}).get('llm_model', 'unknown')}")
    print(f"Generation Timestamp: {graph.get('metadata', {}).get('generation_timestamp', 'N/A')}")
    
    print(f"\n{'='*60}")
    print(f"NODES ({len(graph.get('nodes', []))})")
    print(f"{'='*60}")
    for node in graph.get('nodes', []):
        node_id = node.get('id', 'N/A')
        label = node.get('label', 'N/A')
        node_type = node.get('type', 'N/A')
        importance = node.get('importance', 0)
        print(f"  {node_id:<12} {label:<30} [{node_type}] importance: {importance:.2f}")
    
    print(f"\n{'='*60}")
    print(f"EDGES ({len(graph.get('edges', []))})")
    print(f"{'='*60}")
    for edge in graph.get('edges', []):
        edge_id = edge.get('id', 'N/A')
        source = edge.get('source', 'N/A')
        target = edge.get('target', 'N/A')
        edge_type = edge.get('type', 'N/A')
        print(f"  {edge_id:<12} {source} -> {target} [{edge_type}]")
    
    print(f"\n{'='*60}")
    print(f"METADATA")
    print(f"{'='*60}")
    metadata = graph.get('metadata', {})
    print(f"  Summary: {metadata.get('summary', 'N/A')}")
    print(f"  Main Themes: {metadata.get('main_themes', [])}")
    print(f"  Graph Complexity: {metadata.get('graph_complexity', 'N/A')}")
    print(f"  Layout Hint: {metadata.get('layout_hint', 'N/A')}")
    
    return graph


def test_graph_update():
    """Test graph generation with previous graph (update scenario)"""
    print("\n\n")
    print("=" * 60)
    print("Testing Graph Update (Second Chunk)")
    print("=" * 60)
    
    # Check for API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("⚠ API key not found! Skipping this test.")
        return None
    
    # First, create an initial graph
    extractor = FeatureExtractor()
    
    initial_text = "I think we need to focus on mobile responsiveness as part of the UX."
    print(f"\nInitial text: {initial_text}")
    
    previous_graph = extractor.generate_graph(
        initial_text,
        previous_graph=None,
        metadata={'session_id': 'test-123', 'chunk_id': 1}
    )
    
    print(f"\nPrevious graph had {len(previous_graph.get('nodes', []))} nodes")
    
    # Now update with new text
    new_text = "Actually, I think we should prioritize tablet support too. And maybe add a dark mode feature."
    print(f"\nNew text: {new_text}")
    
    updated_graph = extractor.generate_graph(
        new_text,
        previous_graph=previous_graph,
        metadata={'session_id': 'test-123', 'chunk_id': 2}
    )
    
    print(f"\nUpdated graph has {len(updated_graph.get('nodes', []))} nodes")
    
    # Check if node IDs are preserved
    previous_node_ids = {node.get('id') for node in previous_graph.get('nodes', [])}
    updated_node_ids = {node.get('id') for node in updated_graph.get('nodes', [])}
    
    preserved_ids = previous_node_ids.intersection(updated_node_ids)
    print(f"\nPreserved node IDs: {len(preserved_ids)}")
    if preserved_ids:
        print(f"  IDs: {', '.join(sorted(preserved_ids))}")
    
    # Save updated graph
    with open('test_graph_output.json', 'w') as f:
        json.dump(updated_graph, f, indent=2)
    
    print("\n✓ Updated graph saved to test_graph_output.json")
    
    return updated_graph


def test_hierarchical_expansion():
    """Test graph expansion with text that should create multiple children from a parent"""
    print("\n\n")
    print("=" * 60)
    print("Testing Hierarchical Graph Expansion (Multiple Children)")
    print("=" * 60)
    
    # Check for API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("⚠ API key not found! Skipping this test.")
        return None
    
    extractor = FeatureExtractor()
    
    # Use the same initial text as test_basic_graph_generation
    initial_text = """
    Okay, so let's talk about the mobile app redesign. I think we really need to focus on user experience, 
    especially for first-time users. The onboarding flow is confusing right now. 
    
    What do you think about using React Native? We should test it on iPhone and Android devices. 
    We decided to go with a modern design system. Let's schedule a meeting with the design team next week.
    """
    
    print(f"\nInitial text chunk:")
    print(f"  {initial_text.strip()[:100]}...")
    
    previous_graph = extractor.generate_graph(
        initial_text,
        previous_graph=None,
        metadata={'session_id': 'test-123', 'chunk_id': 1}
    )
    
    print(f"\nPrevious graph: {len(previous_graph.get('nodes', []))} nodes, {len(previous_graph.get('edges', []))} edges")
    
    # Follow-up text that expands on onboarding flow with multiple specific improvements
    # This should create a hierarchical structure where "Onboarding Flow" has multiple children
    followup_text = """
    For the onboarding flow, we need to improve several things: welcome screens, 
    tutorial steps, permission requests, and account setup. Also, we should add 
    progress indicators and skip options. The welcome screens should be engaging 
    and explain our app's value proposition clearly.
    
    Regarding React Native, we've decided to proceed with it. Now we need to set up 
    the development environment, configure the build tools, and integrate with our 
    existing backend APIs.
    
    For the modern design system, we're going with Material Design 3. This means 
    we'll need components for buttons, cards, navigation, forms, and typography. 
    Let's create a design token system too.
    """
    
    print(f"\nFollow-up text chunk (should expand graph hierarchically):")
    print(f"  {followup_text.strip()[:100]}...")
    
    updated_graph = extractor.generate_graph(
        followup_text,
        previous_graph=previous_graph,
        metadata={'session_id': 'test-123', 'chunk_id': 2}
    )
    
    print(f"\nUpdated graph: {len(updated_graph.get('nodes', []))} nodes, {len(updated_graph.get('edges', []))} edges")
    
    # Check for nodes with multiple children
    nodes = updated_graph.get('nodes', [])
    edges = updated_graph.get('edges', [])
    node_ids = {node['id'] for node in nodes}
    
    # Count children per node
    children_count = {}
    for edge in edges:
        source = edge.get('source')
        if source in node_ids:
            children_count[source] = children_count.get(source, 0) + 1
    
    # Find nodes with multiple children
    multi_child_nodes = {node_id: count for node_id, count in children_count.items() if count > 1}
    
    print(f"\nNodes with multiple children: {len(multi_child_nodes)}")
    if multi_child_nodes:
        print("\nHierarchical structure found:")
        for node_id, child_count in multi_child_nodes.items():
            node = next((n for n in nodes if n['id'] == node_id), None)
            if node:
                print(f"  {node.get('label')} -> {child_count} children")
                # Show the children
                child_ids = [e.get('target') for e in edges if e.get('source') == node_id]
                for child_id in child_ids[:5]:  # Show first 5 children
                    child = next((n for n in nodes if n['id'] == child_id), None)
                    if child:
                        print(f"    - {child.get('label')}")
    
    # Check if node IDs are preserved
    previous_node_ids = {node.get('id') for node in previous_graph.get('nodes', [])}
    updated_node_ids = {node.get('id') for node in updated_graph.get('nodes', [])}
    
    preserved_ids = previous_node_ids.intersection(updated_node_ids)
    print(f"\nPreserved node IDs: {len(preserved_ids)}/{len(previous_node_ids)}")
    if preserved_ids:
        print(f"  IDs: {', '.join(sorted(preserved_ids))}")
    
    # Save updated graph
    with open('test_hierarchical_update.json', 'w') as f:
        json.dump(updated_graph, f, indent=2)
    
    print("\n✓ Updated hierarchical graph saved to test_hierarchical_update.json")
    
    return updated_graph


def test_with_sample_transcript():
    """Test with sample transcript from shared/examples"""
    print("\n\n")
    print("=" * 60)
    print("Testing with Sample Transcript")
    print("=" * 60)
    
    # Check for API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("⚠ API key not found! Skipping this test.")
        return None
    
    # Load sample transcript
    try:
        with open('../../shared/examples/sample-transcript.json', 'r') as f:
            transcript_data = json.load(f)
        
        text = transcript_data['text']
        
        extractor = FeatureExtractor()
        graph = extractor.generate_graph(
            text,
            previous_graph=None,
            metadata={
                'session_id': transcript_data.get('session_id'),
                'timestamp': transcript_data.get('timestamp'),
                'chunk_id': transcript_data.get('chunk_id')
            }
        )
        
        print(f"\nGenerated graph with {len(graph.get('nodes', []))} nodes and {len(graph.get('edges', []))} edges")
        
        # Show metadata
        metadata = graph.get('metadata', {})
        print(f"\nSummary: {metadata.get('summary', 'N/A')}")
        print(f"Themes: {metadata.get('main_themes', [])}")
        
        # Show top nodes by importance
        nodes = graph.get('nodes', [])
        sorted_nodes = sorted(nodes, key=lambda n: n.get('importance', 0), reverse=True)
        
        print("\nTop 5 Nodes by Importance:")
        for node in sorted_nodes[:5]:
            print(f"  - {node.get('label')} [{node.get('type')}] (importance: {node.get('importance', 0):.2f})")
        
        # Save to file
        with open('test_graph_output.json', 'w') as f:
            json.dump(graph, f, indent=2)
        
        print("\n✓ Graph saved to test_graph_output.json")
        
        return graph
        
    except FileNotFoundError:
        print("⚠ Sample transcript file not found, skipping this test")
        return None


def test_empty_text():
    """Test edge case with empty text"""
    print("\n\n")
    print("=" * 60)
    print("Testing Edge Case: Empty Text")
    print("=" * 60)
    
    # Check for API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("⚠ API key not found! Skipping this test.")
        return None
    
    extractor = FeatureExtractor()
    graph = extractor.generate_graph("")
    
    assert len(graph.get('nodes', [])) == 0
    assert len(graph.get('edges', [])) == 0
    print("✓ Empty text handled correctly")


if __name__ == "__main__":
    try:
        # Basic generation test
        graph1 = test_basic_graph_generation()
        
        # Graph update test
        graph2 = test_graph_update()
        
        # Hierarchical expansion test
        graph3 = test_hierarchical_expansion()
        
        # Test with sample transcript
        graph4 = test_with_sample_transcript()
        
        # Edge case test
        test_empty_text()
        
        print("\n\n" + "=" * 60)
        print("ALL TESTS COMPLETED ✓")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
