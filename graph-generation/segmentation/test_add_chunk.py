"""
Test script to add a new text chunk to an existing graph

This demonstrates how the graph updates when new text is added.
"""

import json
import os
import sys
from pathlib import Path

# Add current directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from graph_generator import generate_graph
from graph_validator import validate_graph


def print_graph_summary(graph, title="Graph"):
    """Print a summary of the graph"""
    print(f"\n{'='*60}")
    print(f"{title} Summary")
    print(f"{'='*60}")
    print(f"Version: {graph.get('version', 'N/A')}")
    print(f"Timestamp: {graph.get('timestamp', 'N/A')}")
    print(f"Nodes: {len(graph.get('nodes', []))}")
    print(f"Edges: {len(graph.get('edges', []))}")
    
    print(f"\n📊 Nodes:")
    for node in graph.get('nodes', []):
        importance = node.get('importance', 0)
        mentions = node.get('metadata', {}).get('mentions_count', 0)
        print(f"  • [{node['id']}] {node['label']} ({node['type']})")
        print(f"      Importance: {importance:.2f} | Mentions: {mentions}")
    
    print(f"\n🔗 Edges:")
    for edge in graph.get('edges', []):
        source_label = next(
            (n['label'] for n in graph['nodes'] if n['id'] == edge['source']), 
            edge['source']
        )
        target_label = next(
            (n['label'] for n in graph['nodes'] if n['id'] == edge['target']), 
            edge['target']
        )
        print(f"  • {source_label} --[{edge.get('type', 'relates_to')}]--> {target_label}")
    
    if graph.get('metadata'):
        print(f"\n📝 Summary: {graph['metadata'].get('summary', 'N/A')}")
        print(f"🎯 Themes: {', '.join(graph['metadata'].get('main_themes', []))}")


def compare_graphs(before_graph, after_graph):
    """Compare two graphs and show what changed"""
    print(f"\n{'='*60}")
    print("Changes Detected")
    print(f"{'='*60}")
    
    # Version change
    before_version = before_graph.get('version', 0)
    after_version = after_graph.get('version', 0)
    if after_version > before_version:
        print(f"✓ Version: {before_version} → {after_version}")
    
    # Node changes
    before_nodes = {n['id']: n for n in before_graph.get('nodes', [])}
    after_nodes = {n['id']: n for n in after_graph.get('nodes', [])}
    
    # Check for updated nodes
    print(f"\n📝 Node Updates:")
    updated_count = 0
    for node_id in before_nodes:
        if node_id in after_nodes:
            before_node = before_nodes[node_id]
            after_node = after_nodes[node_id]
            
            changes = []
            if before_node.get('label') != after_node.get('label'):
                changes.append(f"label: '{before_node['label']}' → '{after_node['label']}'")
            if before_node.get('importance', 0) != after_node.get('importance', 0):
                changes.append(f"importance: {before_node.get('importance', 0):.2f} → {after_node.get('importance', 0):.2f}")
            
            before_mentions = before_node.get('metadata', {}).get('mentions_count', 0)
            after_mentions = after_node.get('metadata', {}).get('mentions_count', 0)
            if before_mentions != after_mentions:
                changes.append(f"mentions: {before_mentions} → {after_mentions}")
            
            if changes:
                updated_count += 1
                print(f"  • {before_node['label']} [{node_id}]:")
                print(f"      {', '.join(changes)}")
    
    if updated_count == 0:
        print("  (No existing nodes were updated)")
    
    # Check for new nodes
    new_node_ids = set(after_nodes.keys()) - set(before_nodes.keys())
    if new_node_ids:
        print(f"\n✨ New Nodes Added ({len(new_node_ids)}):")
        for node_id in new_node_ids:
            node = after_nodes[node_id]
            print(f"  • [{node_id}] {node['label']} ({node['type']}) - importance: {node.get('importance', 0):.2f}")
    else:
        print(f"\n✨ New Nodes: None")
    
    # Check for removed nodes (shouldn't happen often, but possible)
    removed_node_ids = set(before_nodes.keys()) - set(after_nodes.keys())
    if removed_node_ids:
        print(f"\n🗑️  Nodes Removed ({len(removed_node_ids)}):")
        for node_id in removed_node_ids:
            node = before_nodes[node_id]
            print(f"  • [{node_id}] {node['label']}")
    
    # Edge changes
    before_edges = {e['id']: e for e in before_graph.get('edges', [])}
    after_edges = {e['id']: e for e in after_graph.get('edges', [])}
    
    new_edge_ids = set(after_edges.keys()) - set(before_edges.keys())
    if new_edge_ids:
        print(f"\n🔗 New Edges Added ({len(new_edge_ids)}):")
        for edge_id in new_edge_ids:
            edge = after_edges[edge_id]
            source_label = next(
                (n['label'] for n in after_graph['nodes'] if n['id'] == edge['source']), 
                edge['source']
            )
            target_label = next(
                (n['label'] for n in after_graph['nodes'] if n['id'] == edge['target']), 
                edge['target']
            )
            print(f"  • {source_label} --[{edge.get('type', 'relates_to')}]--> {target_label}")


def test_add_chunk_to_existing_graph():
    """Test adding a new text chunk to the existing test-graph.json"""
    
    print("=" * 60)
    print("Testing Graph Update with New Text Chunk")
    print("=" * 60)
    
    # Load existing graph
    current_dir = Path(__file__).parent
    graph_path = current_dir.parent.parent / 'shared' / 'examples' / 'test-graph.json'
    
    if not graph_path.exists():
        print(f"\n⚠ Existing graph not found at {graph_path}")
        print("  Creating a new graph first...")
        
        # Create initial graph
        initial_text = """
        Okay, so let's talk about the mobile app redesign. 
        I think we really need to focus on user experience, 
        especially for first-time users. The onboarding flow is confusing right now.
        """
        before_graph = generate_graph(initial_text, previous_graph=None, session_id="chunk-test")
        
        # Save it
        with open(graph_path, 'w') as f:
            json.dump(before_graph, f, indent=2)
        print(f"  ✓ Created initial graph at {graph_path}")
    else:
        print(f"\n📂 Loading existing graph from {graph_path}")
        with open(graph_path, 'r') as f:
            before_graph = json.load(f)
        print(f"  ✓ Loaded graph version {before_graph.get('version', 'N/A')}")
    
    # Show current state
    print_graph_summary(before_graph, "BEFORE - Current Graph")
    
    # New text chunk to add
    new_chunk = """
    Actually, we should also consider using React Native for the mobile app. 
    This will help with cross-platform development and make it easier to maintain 
    both iOS and Android versions. We'll need to test the performance on different 
    devices to make sure it meets our requirements.
    """
    
    print(f"\n{'='*60}")
    print("Adding New Text Chunk")
    print(f"{'='*60}")
    print(f"\n📝 New Text:")
    print(f"   {new_chunk.strip()}")
    
    # Generate updated graph
    print(f"\n🔄 Generating updated graph...")
    after_graph = generate_graph(
        new_text=new_chunk.strip(),
        previous_graph=before_graph,
        session_id=before_graph.get('session_id', 'chunk-test')
    )
    
    # Validate
    validate_graph(after_graph)
    print("  ✓ Graph validation passed")
    
    # Show updated state
    print_graph_summary(after_graph, "AFTER - Updated Graph")
    
    # Compare graphs
    compare_graphs(before_graph, after_graph)
    
    # Save updated graph
    with open(graph_path, 'w') as f:
        json.dump(after_graph, f, indent=2)
    print(f"\n💾 Updated graph saved to {graph_path}")
    
    return before_graph, after_graph


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Graph Chunk Addition Test")
    print("=" * 60)
    print("\nMake sure ANTHROPIC_API_KEY is set in your environment!")
    print("=" * 60 + "\n")
    
    try:
        before, after = test_add_chunk_to_existing_graph()
        
        print("\n\n" + "=" * 60)
        print("TEST COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nKey observations:")
        print("  • Check if node IDs remained stable (ID stability)")
        print("  • Check if labels were refined (if concepts became more specific)")
        print("  • Check if importance scores increased for mentioned concepts")
        print("  • Check if new nodes were created for new concepts")
        print("  • Check if new edges connected related concepts")
        print("  • Check if version number incremented")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

