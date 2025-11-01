"""
Test script for hierarchical graph generation

Tests that graphs can form proper tree structures with:
- Multiple children from a single parent
- Complex edge relationships (not just linear chains)
- Hierarchical organization
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from feature_extractor import FeatureExtractor, generate_graph
from dotenv import load_dotenv

load_dotenv()


def analyze_graph_structure(graph):
    """Analyze the graph structure and return statistics"""
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    
    # Build adjacency maps
    outgoing = defaultdict(list)  # node -> list of targets
    incoming = defaultdict(list)  # node -> list of sources
    node_ids = {node['id'] for node in nodes}
    
    for edge in edges:
        source = edge.get('source')
        target = edge.get('target')
        if source in node_ids and target in node_ids:
            outgoing[source].append(target)
            incoming[target].append(source)
    
    # Find root nodes (nodes with no incoming edges)
    root_nodes = [node_id for node_id in node_ids if node_id not in incoming or len(incoming[node_id]) == 0]
    
    # Find leaf nodes (nodes with no outgoing edges)
    leaf_nodes = [node_id for node_id in node_ids if node_id not in outgoing or len(outgoing[node_id]) == 0]
    
    # Find nodes with multiple children
    multi_child_nodes = {node_id: children for node_id, children in outgoing.items() if len(children) > 1}
    
    # Find nodes with multiple parents
    multi_parent_nodes = {node_id: parents for node_id, parents in incoming.items() if len(parents) > 1}
    
    # Calculate max depth (simple approximation)
    def calculate_depth(node_id, visited=None):
        if visited is None:
            visited = set()
        if node_id in visited or node_id not in outgoing:
            return 0
        visited.add(node_id)
        if not outgoing[node_id]:
            return 1
        return 1 + max((calculate_depth(child, visited.copy()) for child in outgoing[node_id]), default=0)
    
    max_depth = max((calculate_depth(root) for root in root_nodes), default=0) if root_nodes else 0
    
    return {
        'total_nodes': len(nodes),
        'total_edges': len(edges),
        'root_nodes': root_nodes,
        'leaf_nodes': leaf_nodes,
        'multi_child_nodes': multi_child_nodes,
        'multi_parent_nodes': multi_parent_nodes,
        'max_children': max((len(children) for children in outgoing.values()), default=0),
        'max_depth': max_depth,
        'avg_outgoing': sum(len(children) for children in outgoing.values()) / len(nodes) if nodes else 0,
        'avg_incoming': sum(len(parents) for parents in incoming.values()) / len(nodes) if nodes else 0,
    }


def test_hierarchical_structure():
    """Test that graphs can form hierarchical structures with multiple children per parent"""
    print("=" * 80)
    print("Testing Hierarchical Graph Structure (Multiple Children per Parent)")
    print("=" * 80)
    
    # Check for API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("⚠ API key not found!")
        print("   Set ANTHROPIC_API_KEY in .env file or environment variable.")
        return None
    
    # Use text that should naturally create a hierarchical structure
    # A project with multiple sub-components, each with multiple tasks
    hierarchical_text = """
    We're building a new mobile app. The project has three main components: 
    authentication, user dashboard, and messaging features. 
    
    For authentication, we need to implement login, registration, password reset, 
    and two-factor authentication. 
    
    The user dashboard needs a profile page, settings page, notification center, 
    and analytics view.
    
    For messaging, we need real-time chat, file sharing, group chats, and message search.
    
    Each component requires database setup, API endpoints, and frontend UI.
    """
    
    extractor = FeatureExtractor()
    graph = extractor.generate_graph(
        hierarchical_text,
        previous_graph=None,
        metadata={'session_id': 'hierarchical-test', 'chunk_id': 1}
    )
    
    print(f"\nGenerated graph:")
    print(f"  Nodes: {len(graph.get('nodes', []))}")
    print(f"  Edges: {len(graph.get('edges', []))}")
    
    # Analyze structure
    stats = analyze_graph_structure(graph)
    
    print(f"\n{'='*80}")
    print("GRAPH STRUCTURE ANALYSIS")
    print(f"{'='*80}")
    print(f"Total nodes: {stats['total_nodes']}")
    print(f"Total edges: {stats['total_edges']}")
    print(f"Root nodes: {len(stats['root_nodes'])} {stats['root_nodes']}")
    print(f"Leaf nodes: {len(stats['leaf_nodes'])}")
    print(f"Max children from single node: {stats['max_children']}")
    print(f"Nodes with multiple children: {len(stats['multi_child_nodes'])}")
    print(f"Max depth: {stats['max_depth']}")
    print(f"Avg outgoing edges per node: {stats['avg_outgoing']:.2f}")
    print(f"Avg incoming edges per node: {stats['avg_incoming']:.2f}")
    
    # Show nodes with multiple children
    if stats['multi_child_nodes']:
        print(f"\n{'='*80}")
        print("NODES WITH MULTIPLE CHILDREN (Hierarchical Structure)")
        print(f"{'='*80}")
        for node_id, children in stats['multi_child_nodes'].items():
            node = next((n for n in graph['nodes'] if n['id'] == node_id), None)
            if node:
                print(f"\n  Parent: {node.get('label')} [{node.get('type')}] (ID: {node_id})")
                print(f"    Has {len(children)} children:")
                for child_id in children:
                    child = next((n for n in graph['nodes'] if n['id'] == child_id), None)
                    if child:
                        print(f"      - {child.get('label')} [{child.get('type')}] (ID: {child_id})")
    else:
        print(f"\n⚠ WARNING: No nodes with multiple children found!")
        print("   The graph may be forming a linear chain instead of a tree.")
    
    # Validation checks
    print(f"\n{'='*80}")
    print("VALIDATION CHECKS")
    print(f"{'='*80}")
    
    checks_passed = 0
    total_checks = 5
    
    # Check 1: Graph has multiple nodes
    if stats['total_nodes'] >= 3:
        print("✓ Graph has sufficient nodes (>= 3)")
        checks_passed += 1
    else:
        print("✗ Graph has too few nodes")
    
    # Check 2: Graph has edges
    if stats['total_edges'] >= 2:
        print("✓ Graph has edges")
        checks_passed += 1
    else:
        print("✗ Graph has too few edges")
    
    # Check 3: At least one node has multiple children
    if len(stats['multi_child_nodes']) > 0:
        print("✓ Found nodes with multiple children (tree structure)")
        checks_passed += 1
    else:
        print("✗ No nodes with multiple children found (may be linear)")
    
    # Check 4: Max children is at least 2
    if stats['max_children'] >= 2:
        print(f"✓ Maximum children count is {stats['max_children']} (>= 2)")
        checks_passed += 1
    else:
        print(f"✗ Maximum children count is {stats['max_children']} (< 2)")
    
    # Check 5: Average outgoing edges indicates branching
    if stats['avg_outgoing'] >= 0.5:
        print(f"✓ Average outgoing edges: {stats['avg_outgoing']:.2f} (indicates branching)")
        checks_passed += 1
    else:
        print(f"✗ Average outgoing edges: {stats['avg_outgoing']:.2f} (may be too linear)")
    
    print(f"\n{'='*80}")
    print(f"Validation: {checks_passed}/{total_checks} checks passed")
    print(f"{'='*80}")
    
    # Save graph for inspection
    with open('test_hierarchical_graph.json', 'w') as f:
        json.dump(graph, f, indent=2)
    print("\n✓ Graph saved to test_hierarchical_graph.json")
    
    return graph, stats


def test_incremental_hierarchical_build():
    """Test building a hierarchical graph incrementally across multiple chunks"""
    print("\n\n")
    print("=" * 80)
    print("Testing Incremental Hierarchical Graph Building")
    print("=" * 80)
    
    # Check for API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("⚠ API key not found! Skipping this test.")
        return None
    
    extractor = FeatureExtractor()
    
    # Start with a root concept
    chunk1 = "We're building a mobile app project."
    print(f"\nChunk 1: {chunk1}")
    graph1 = extractor.generate_graph(chunk1, previous_graph=None, metadata={'chunk_id': 1})
    
    print(f"  Graph 1: {len(graph1.get('nodes', []))} nodes, {len(graph1.get('edges', []))} edges")
    stats1 = analyze_graph_structure(graph1)
    
    # Add multiple components (should connect to the root)
    chunk2 = "The project has three main components: authentication, dashboard, and messaging."
    print(f"\nChunk 2: {chunk2}")
    graph2 = extractor.generate_graph(chunk2, previous_graph=graph1, metadata={'chunk_id': 2})
    
    print(f"  Graph 2: {len(graph2.get('nodes', []))} nodes, {len(graph2.get('edges', []))} edges")
    stats2 = analyze_graph_structure(graph2)
    print(f"  Nodes with multiple children: {len(stats2['multi_child_nodes'])}")
    print(f"  Max children: {stats2['max_children']}")
    
    # Add details to one component (should create children)
    chunk3 = "For authentication, we need login, registration, password reset, and 2FA."
    print(f"\nChunk 3: {chunk3}")
    graph3 = extractor.generate_graph(chunk3, previous_graph=graph2, metadata={'chunk_id': 3})
    
    print(f"  Graph 3: {len(graph3.get('nodes', []))} nodes, {len(graph3.get('edges', []))} edges")
    stats3 = analyze_graph_structure(graph3)
    print(f"  Nodes with multiple children: {len(stats3['multi_child_nodes'])}")
    print(f"  Max children: {stats3['max_children']}")
    
    # Add details to another component
    chunk4 = "The dashboard needs profile, settings, notifications, and analytics pages."
    print(f"\nChunk 4: {chunk4}")
    graph4 = extractor.generate_graph(chunk4, previous_graph=graph3, metadata={'chunk_id': 4})
    
    print(f"  Graph 4: {len(graph4.get('nodes', []))} nodes, {len(graph4.get('edges', []))} edges")
    stats4 = analyze_graph_structure(graph4)
    print(f"  Nodes with multiple children: {len(stats4['multi_child_nodes'])}")
    print(f"  Max children: {stats4['max_children']}")
    
    # Final check
    print(f"\n{'='*80}")
    print("FINAL HIERARCHICAL STRUCTURE")
    print(f"{'='*80}")
    print(f"Total nodes: {stats4['total_nodes']}")
    print(f"Total edges: {stats4['total_edges']}")
    print(f"Nodes with multiple children: {len(stats4['multi_child_nodes'])}")
    print(f"Max children from single node: {stats4['max_children']}")
    
    if stats4['multi_child_nodes']:
        print(f"\nHierarchical structure found:")
        for node_id, children in list(stats4['multi_child_nodes'].items())[:3]:
            node = next((n for n in graph4['nodes'] if n['id'] == node_id), None)
            if node:
                print(f"  {node.get('label')} -> {len(children)} children")
    
    # Save final graph
    with open('test_incremental_hierarchical.json', 'w') as f:
        json.dump(graph4, f, indent=2)
    print("\n✓ Final graph saved to test_incremental_hierarchical.json")
    
    return graph4, stats4


def visualize_graph_structure(graph, max_depth=3):
    """Print a text visualization of the graph structure"""
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    
    # Build tree structure
    node_map = {node['id']: node for node in nodes}
    children_map = defaultdict(list)
    
    for edge in edges:
        source = edge.get('source')
        target = edge.get('target')
        if source in node_map and target in node_map:
            children_map[source].append(target)
    
    # Find root nodes (no incoming edges)
    all_targets = {edge.get('target') for edge in edges}
    root_nodes = [node['id'] for node in nodes if node['id'] not in all_targets]
    
    if not root_nodes:
        root_nodes = [node['id'] for node in nodes[:1]]  # Use first node if no clear root
    
    def print_node(node_id, prefix="", is_last=True, depth=0):
        if depth > max_depth:
            return
        
        node = node_map.get(node_id)
        if not node:
            return
        
        connector = "└── " if is_last else "├── "
        print(f"{prefix}{connector}{node.get('label')} [{node.get('type')}]")
        
        children = children_map.get(node_id, [])
        new_prefix = prefix + ("    " if is_last else "│   ")
        
        for i, child_id in enumerate(children):
            is_last_child = (i == len(children) - 1)
            print_node(child_id, new_prefix, is_last_child, depth + 1)
    
    print(f"\n{'='*80}")
    print("GRAPH STRUCTURE VISUALIZATION")
    print(f"{'='*80}")
    for root_id in root_nodes[:1]:  # Show first root
        print_node(root_id)


if __name__ == "__main__":
    try:
        # Test hierarchical structure in single chunk
        graph1, stats1 = test_hierarchical_structure()
        
        if graph1:
            visualize_graph_structure(graph1)
        
        # Test incremental hierarchical building
        graph2, stats2 = test_incremental_hierarchical_build()
        
        if graph2:
            visualize_graph_structure(graph2)
        
        print("\n\n" + "=" * 80)
        print("ALL HIERARCHICAL TESTS COMPLETED ✓")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

