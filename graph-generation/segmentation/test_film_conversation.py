"""
Test script for film discussion conversation

This script tests the graph generation with a conversation about films,
exploring different genres and preferences.
"""

import json
import os
import sys
from pathlib import Path

# Add current directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from graph_generator import generate_graph
from graph_validator import validate_graph


# Film discussion conversation chunks
FILM_CONVERSATION = [
    # Chunk 1: Opening question
    "Hey, what are your favorite films? I'm always looking for recommendations.",
    
    # Chunk 2: First person mentions sci-fi
    "I really love science fiction movies. Things like Blade Runner, The Matrix, and Interstellar really blow my mind. The way they explore complex ideas about humanity and the future is fascinating.",
    
    # Chunk 3: Second person mentions horror
    "Oh interesting! I'm more into horror films actually. I love the psychological thrillers - stuff like The Shining and Hereditary really get under your skin. But I also enjoy classic slashers like Halloween.",
    
    # Chunk 4: Discussion of psychological elements
    "The Shining is amazing! Speaking of psychological elements, have you seen any psychological dramas? Movies like Memento and Black Swan really mess with your head in the best way.",
    
    # Chunk 5: Action movies
    "Yeah, I love those mind-bending films too. What about action movies? I'm a huge fan of the Mission Impossible series. Tom Cruise does all his own stunts which is incredible.",
    
    # Chunk 6: Martial arts as action subcategory
    "Action is great! I prefer martial arts films though - Bruce Lee movies, The Raid, stuff like that. The choreography is just incredible. It's like watching a dance.",
    
    # Chunk 7: Returns to favorite films (should merge with chunk 1)
    "Going back to what you said earlier about favorite films - I think what draws me to sci-fi is the world-building. Directors like Denis Villeneuve create these incredible universes.",
    
    # Chunk 8: Fantasy genre
    "Absolutely! World-building is crucial. That's why I love fantasy films too - Lord of the Rings, The Dark Crystal. They create entire worlds from scratch."
]


def test_film_conversation():
    """Test graph generation with film discussion conversation"""
    print("=" * 80)
    print("Film Discussion Conversation Test")
    print("=" * 80)
    print("\nThis test processes a conversation about films exploring different genres")
    print("split into multiple chunks to test incremental graph updates.\n")
    print("Key things to observe:")
    print("  - Merging similar concepts (e.g., 'favorite films' mentions)")
    print("  - Meaningful relationships between genres, not hub connections")
    print("  - ID stability across chunks")
    print("  - Genre connections (sci-fi → world-building, horror → psychological)")
    print("=" * 80)
    
    graph = None
    all_graphs = []
    
    for i, text_chunk in enumerate(FILM_CONVERSATION, 1):
        print(f"\n{'=' * 80}")
        print(f"CHUNK {i}/{len(FILM_CONVERSATION)}")
        print(f"{'=' * 80}")
        print(f"Text: {text_chunk}")
        print(f"\nProcessing chunk {i}...")
        
        try:
            graph = generate_graph(
                text_chunk, 
                previous_graph=graph, 
                session_id="film-discussion-test"
            )
            
            # Validate
            validate_graph(graph)
            
            # Store graph for comparison
            all_graphs.append({
                'chunk': i,
                'text': text_chunk,
                'graph': graph.copy()
            })
            
            # Display summary
            print(f"\n✓ Graph updated successfully")
            print(f"  Nodes: {len(graph['nodes'])}")
            print(f"  Edges: {len(graph['edges'])}")
            print(f"  Version: {graph.get('version', 'N/A')}")
            
            # Show node labels
            print(f"\n  Nodes:")
            for node in graph['nodes'][:10]:  # Show first 10
                importance = node.get('importance', 0)
                print(f"    - {node['label']} ({node['type']}) [importance: {importance:.2f}]")
            if len(graph['nodes']) > 10:
                print(f"    ... and {len(graph['nodes']) - 10} more nodes")
            
            # Show some edges
            if graph['edges']:
                print(f"\n  Sample edges:")
                for edge in graph['edges'][:5]:  # Show first 5
                    source_label = next((n['label'] for n in graph['nodes'] if n['id'] == edge['source']), edge['source'])
                    target_label = next((n['label'] for n in graph['nodes'] if n['id'] == edge['target']), edge['target'])
                    print(f"    - {source_label} --[{edge.get('type', 'relates_to')}]--> {target_label}")
                if len(graph['edges']) > 5:
                    print(f"    ... and {len(graph['edges']) - 5} more edges")
            
        except Exception as e:
            print(f"\n❌ Error processing chunk {i}: {e}")
            import traceback
            traceback.print_exc()
            break
    
    # Final summary
    print(f"\n\n{'=' * 80}")
    print("FINAL SUMMARY")
    print(f"{'=' * 80}")
    if graph:
        print(f"\nFinal graph statistics:")
        print(f"  Total nodes: {len(graph['nodes'])}")
        print(f"  Total edges: {len(graph['edges'])}")
        print(f"  Final version: {graph.get('version', 'N/A')}")
        
        # Show all nodes
        print(f"\n  All nodes:")
        for node in sorted(graph['nodes'], key=lambda n: n.get('importance', 0), reverse=True):
            importance = node.get('importance', 0)
            node_type = node.get('type', 'unknown')
            print(f"    - {node['label']} ({node_type}) [importance: {importance:.2f}, id: {node['id']}]")
        
        # Show all edges
        if graph['edges']:
            print(f"\n  All edges:")
            for edge in graph['edges']:
                source_label = next((n['label'] for n in graph['nodes'] if n['id'] == edge['source']), edge['source'])
                target_label = next((n['label'] for n in graph['nodes'] if n['id'] == edge['target']), edge['target'])
                edge_type = edge.get('type', 'relates_to')
                print(f"    - {source_label} --[{edge_type}]--> {target_label}")
        
        # Save final graph
        output_path = Path(__file__).parent / 'film_test_graph.json'
        with open(output_path, 'w') as f:
            json.dump(graph, f, indent=2)
        print(f"\n✓ Final graph saved to: {output_path}")
        
        # Save all graphs with chunks
        detailed_output_path = Path(__file__).parent / 'film_test_all_chunks.json'
        with open(detailed_output_path, 'w') as f:
            json.dump(all_graphs, f, indent=2)
        print(f"✓ All chunks with graphs saved to: {detailed_output_path}")
        
        # Check for potential duplicates (similar labels)
        print(f"\n  Checking for potential duplicate concepts...")
        node_labels = [n['label'].lower() for n in graph['nodes']]
        duplicates_found = []
        for i, label1 in enumerate(node_labels):
            for j, label2 in enumerate(node_labels[i+1:], i+1):
                # Simple similarity check - words in common
                words1 = set(label1.split())
                words2 = set(label2.split())
                if words1 and words2:
                    similarity = len(words1 & words2) / len(words1 | words2)
                    if similarity > 0.5 and label1 != label2:
                        duplicates_found.append((graph['nodes'][i]['label'], graph['nodes'][j]['label'], similarity))
        
        if duplicates_found:
            print(f"  ⚠ Found {len(duplicates_found)} potential duplicate pairs:")
            for label1, label2, sim in duplicates_found:
                print(f"    - '{label1}' and '{label2}' (similarity: {sim:.2f})")
        else:
            print(f"  ✓ No obvious duplicates found")
    
    print(f"\n{'=' * 80}")
    print("TEST COMPLETE")
    print(f"{'=' * 80}\n")
    
    return graph


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("Film Discussion Test")
    print("=" * 80)
    print("\nMake sure ANTHROPIC_API_KEY is set in your environment!")
    print("=" * 80 + "\n")
    
    try:
        graph = test_film_conversation()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

