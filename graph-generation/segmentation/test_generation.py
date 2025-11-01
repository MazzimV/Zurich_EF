"""
Test script for graph generation pipeline

Tests the graph generator with sample transcript data.
"""

import json
import os
import sys
from pathlib import Path

# Add current directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from graph_generator import generate_graph
from graph_validator import validate_graph


def test_basic_generation():
    """Test basic graph generation from simple text"""
    print("=" * 60)
    print("Test 1: Basic Graph Generation")
    print("=" * 60)
    
    new_text = """
    Okay, so let's talk about the mobile app redesign. 
    I think we really need to focus on user experience, 
    especially for first-time users. The onboarding flow is confusing right now.
    """
    
    graph = generate_graph(new_text, previous_graph=None, session_id="test-1")
    
    print(f"\nGenerated graph:")
    print(f"  Nodes: {len(graph['nodes'])}")
    print(f"  Edges: {len(graph['edges'])}")
    print(f"  Version: {graph.get('version', 'N/A')}")
    
    print(f"\nNodes:")
    for node in graph['nodes']:
        print(f"  - {node['label']} ({node['type']}) - importance: {node.get('importance', 0):.2f}")
    
    print(f"\nEdges:")
    for edge in graph['edges']:
        source_label = next((n['label'] for n in graph['nodes'] if n['id'] == edge['source']), edge['source'])
        target_label = next((n['label'] for n in graph['nodes'] if n['id'] == edge['target']), edge['target'])
        print(f"  - {source_label} --[{edge.get('type', 'relates_to')}]--> {target_label}")
    
    # Validate
    validate_graph(graph)
    print("\n✓ Graph validation passed")
    
    return graph


def test_label_refinement():
    """Test label refinement - more specific labels should update existing nodes"""
    print("\n\n" + "=" * 60)
    print("Test 2: Label Refinement")
    print("=" * 60)
    
    # Start with a general concept
    initial_text = "We need to manage the budget better."
    graph = generate_graph(initial_text, previous_graph=None, session_id="test-2")
    
    print(f"\nInitial graph - node label:")
    if graph['nodes']:
        initial_node = graph['nodes'][0]
        print(f"  {initial_node['label']} (ID: {initial_node['id']})")
        initial_id = initial_node['id']
    else:
        print("  No nodes found!")
        return graph
    
    # Add more specific text about budget expenses
    refined_text = "Let's track our budget expenses more carefully, especially the monthly recurring costs."
    graph = generate_graph(refined_text, previous_graph=graph, session_id="test-2")
    
    print(f"\nAfter refinement - node label:")
    # Find the same node ID
    updated_node = next((n for n in graph['nodes'] if n['id'] == initial_id), None)
    if updated_node:
        print(f"  {updated_node['label']} (ID: {updated_node['id']})")
        if updated_node['label'] != initial_node['label']:
            print(f"\n✓ Label refined: '{initial_node['label']}' → '{updated_node['label']}'")
        else:
            print(f"\n⚠ Label unchanged (might need prompt tuning)")
    else:
        print(f"  Node ID {initial_id} not found (may have been replaced)")
    
    return graph


def test_incremental_updates():
    """Test incremental graph updates with multiple chunks"""
    print("\n\n" + "=" * 60)
    print("Test 3: Incremental Updates (ID Stability)")
    print("=" * 60)
    
    graph = None
    texts = [
        "We should focus on user experience for the mobile app.",
        "Mobile responsiveness is key for good UX. Let's test on iPhone and Android.",
        "We decided to use React Native for the mobile app. This will help with cross-platform development."
    ]
    
    for i, text in enumerate(texts):
        print(f"\nChunk {i+1}: {text[:50]}...")
        graph = generate_graph(text, previous_graph=graph, session_id="test-3")
        print(f"  Nodes: {len(graph['nodes'])}, Edges: {len(graph['edges'])}, Version: {graph['version']}")
        
        # Show node IDs to verify stability
        node_ids = [n['id'] for n in graph['nodes']]
        print(f"  Node IDs: {node_ids[:5]}{'...' if len(node_ids) > 5 else ''}")
    
    print("\n✓ Incremental updates completed")
    return graph


def test_with_sample_transcript():
    """Test with sample transcript file if available"""
    print("\n\n" + "=" * 60)
    print("Test 4: Sample Transcript")
    print("=" * 60)
    
    # Try to load sample transcript
    current_dir = Path(__file__).parent
    sample_path = current_dir.parent.parent / 'shared' / 'examples' / 'sample-transcript.json'
    
    if not sample_path.exists():
        print(f"⚠ Sample transcript not found at {sample_path}")
        print("  Skipping this test")
        return None
    
    try:
        with open(sample_path, 'r') as f:
            transcript_data = json.load(f)
        
        text = transcript_data.get('text', '')
        if not text:
            print("⚠ Sample transcript has no text field")
            return None
        
        print(f"\nProcessing sample transcript ({len(text)} chars)...")
        graph = generate_graph(text, previous_graph=None, session_id="sample-test")
        
        print(f"\nGenerated graph:")
        print(f"  Nodes: {len(graph['nodes'])}")
        print(f"  Edges: {len(graph['edges'])}")
        
        # Save output
        output_path = current_dir.parent.parent / 'shared' / 'examples' / 'test-graph.json'
        with open(output_path, 'w') as f:
            json.dump(graph, f, indent=2)
        
        print(f"\n✓ Graph saved to {output_path}")
        return graph
        
    except Exception as e:
        print(f"❌ Error processing sample transcript: {e}")
        return None


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Graph Generation Test Suite")
    print("=" * 60)
    print("\nMake sure ANTHROPIC_API_KEY is set in your environment!")
    print("=" * 60 + "\n")
    
    try:
        # Run tests
        graph1 = test_basic_generation()
        graph2 = test_label_refinement()
        graph3 = test_incremental_updates()
        graph4 = test_with_sample_transcript()
        
        print("\n\n" + "=" * 60)
        print("ALL TESTS COMPLETED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

