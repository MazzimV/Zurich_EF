"""
Graph Visualization Script

Visualizes knowledge graphs from JSON files or generated graphs.
Supports multiple visualization formats.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Optional

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch
    import networkx as nx
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("⚠ matplotlib and networkx not installed. Install with: pip install matplotlib networkx")
    print("   Falling back to HTML visualization only.")


def load_graph(file_path: str) -> Dict:
    """Load graph from JSON file"""
    with open(file_path, 'r') as f:
        return json.load(f)


def create_networkx_graph(graph: Dict):
    """Convert graph JSON to NetworkX graph"""
    G = nx.DiGraph()
    
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    
    # Add nodes with attributes
    for node in nodes:
        G.add_node(
            node['id'],
            label=node.get('label', ''),
            type=node.get('type', 'unknown'),
            importance=node.get('importance', 0.5),
            color=node.get('color', '#888888'),
            description=node.get('description', '')
        )
    
    # Add edges with attributes
    for edge in edges:
        G.add_edge(
            edge['source'],
            edge['target'],
            label=edge.get('label', ''),
            type=edge.get('type', 'relates_to'),
            strength=edge.get('strength', 0.5)
        )
    
    return G, nodes, edges


def visualize_with_matplotlib(graph: Dict, output_file: Optional[str] = None, show: bool = True):
    """Visualize graph using matplotlib and networkx"""
    if not HAS_MATPLOTLIB:
        print("Cannot use matplotlib visualization - libraries not installed")
        return
    
    G, nodes, edges = create_networkx_graph(graph)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(16, 12))
    ax.set_facecolor('#f5f5f5')
    
    # Use hierarchical layout if possible, otherwise spring layout
    # Increase k for better spacing between nodes
    num_nodes = len(nodes)
    k_value = max(3, num_nodes ** 0.5)  # Adaptive spacing based on node count
    
    try:
        pos = nx.spring_layout(G, k=k_value, iterations=100, seed=42)
    except:
        pos = nx.spring_layout(G, k=k_value, seed=42)
    
    # Draw edges
    for edge in edges:
        source = edge['source']
        target = edge['target']
        strength = edge.get('strength', 0.5)
        edge_type = edge.get('type', 'relates_to')
        
        if source in pos and target in pos:
            x_coords = [pos[source][0], pos[target][0]]
            y_coords = [pos[source][1], pos[target][1]]
            
            # Color and width based on edge type and strength
            edge_color = {
                'relates_to': '#94a3b8',
                'causes': '#ef4444',
                'supports': '#10b981',
                'contradicts': '#f59e0b',
                'follows': '#3b82f6',
                'elaborates': '#8b5cf6'
            }.get(edge_type, '#94a3b8')
            
            linewidth = 1 + strength * 2
            
            ax.plot(x_coords, y_coords, color=edge_color, linewidth=linewidth, 
                   alpha=0.6, zorder=1)
            
            # Add edge label if space allows
            if edge.get('label'):
                mid_x = (pos[source][0] + pos[target][0]) / 2
                mid_y = (pos[source][1] + pos[target][1]) / 2
                ax.text(mid_x, mid_y, edge['label'], fontsize=8, 
                       ha='center', va='center', 
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                               edgecolor='none', alpha=0.7))
    
    # Draw nodes with size based on importance (much smaller sizes)
    for i, node in enumerate(nodes):
        node_id = node['id']
        if node_id in pos:
            x, y = pos[node_id]
            importance = node.get('importance', 0.5)
            # Reduced radius range: 0.08 to 0.25 (much smaller than before)
            base_radius = 0.08
            max_radius = 0.25
            radius = base_radius + importance * (max_radius - base_radius)
            color = node.get('color', '#888888')
            node_type = node.get('type', 'unknown')
            
            # Draw node circle (much smaller)
            circle = plt.Circle((x, y), radius, color=color, 
                              alpha=0.8, zorder=2)
            ax.add_patch(circle)
            
            # Draw border
            border = plt.Circle((x, y), radius, fill=False, 
                              edgecolor='#1e1e1e', linewidth=1.5, zorder=3)
            ax.add_patch(border)
            
            # Add label (smaller font)
            label = node.get('label', node_id)
            # Truncate long labels
            if len(label) > 25:
                label = label[:22] + '...'
            
            font_size = max(6, 8 + importance * 2)  # Reduced from 8 + importance * 4
            ax.text(x, y, label, fontsize=font_size, 
                   ha='center', va='center', fontweight='bold',
                   color='white' if importance > 0.5 else 'black',
                   zorder=4, wrap=True)
    
    # Set title
    metadata = graph.get('metadata', {})
    summary = metadata.get('summary', 'Knowledge Graph')
    ax.set_title(f'{summary}\n({len(nodes)} nodes, {len(edges)} edges)', 
                fontsize=14, fontweight='bold', pad=20)
    
    ax.axis('off')
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ Graph saved to {output_file}")
    
    if show:
        plt.show()


def visualize_with_html(graph: Dict, output_file: str = 'graph_visualization.html'):
    """Generate an interactive HTML visualization using vis.js"""
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    metadata = graph.get('metadata', {})
    
    # Build nodes array for vis.js (smaller sizes)
    vis_nodes = []
    for node in nodes:
        importance = node.get('importance', 0.5)
        vis_nodes.append({
            'id': node['id'],
            'label': node.get('label', node['id']),
            'title': f"{node.get('description', '')}\nType: {node.get('type', 'unknown')}\nImportance: {importance:.2f}",
            'color': {
                'background': node.get('color', '#888888'),
                'border': '#1e1e1e',
                'highlight': {'background': node.get('color', '#888888'), 'border': '#000000'}
            },
            'size': 15 + importance * 20,  # Reduced from 20 + importance * 40
            'font': {
                'size': 10 + importance * 4,  # Reduced from 12 + importance * 8
                'face': 'Arial',
                'color': 'white' if importance > 0.5 else 'black'
            },
            'shape': 'box',
            'mass': 0.5 + importance  # Reduced from 1 + importance * 2
        })
    
    # Build edges array for vis.js
    vis_edges = []
    for edge in edges:
        strength = edge.get('strength', 0.5)
        vis_edges.append({
            'id': edge['id'],
            'from': edge['source'],
            'to': edge['target'],
            'label': edge.get('label', ''),
            'title': f"{edge.get('type', 'relates_to')}\nStrength: {strength:.2f}\n{edge.get('metadata', {}).get('reason', '')}",
            'width': 1 + strength * 3,
            'color': {
                'color': {
                    'relates_to': '#94a3b8',
                    'causes': '#ef4444',
                    'supports': '#10b981',
                    'contradicts': '#f59e0b',
                    'follows': '#3b82f6',
                    'elaborates': '#8b5cf6'
                }.get(edge.get('type', 'relates_to'), '#94a3b8'),
                'highlight': '#000000'
            },
            'arrows': 'to',
            'smooth': {'type': 'curvedCW', 'roundness': 0.2}
        })
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Knowledge Graph Visualization</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        #graph-container {{
            width: 100%;
            height: 800px;
            border: 2px solid #ddd;
            border-radius: 8px;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .header {{
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stats {{
            display: flex;
            gap: 20px;
            margin-top: 10px;
        }}
        .stat-item {{
            padding: 10px;
            background: #f0f0f0;
            border-radius: 4px;
        }}
        .legend {{
            margin-top: 20px;
            padding: 15px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .legend-item {{
            display: inline-block;
            margin: 5px 15px;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Knowledge Graph Visualization</h1>
        <p><strong>Summary:</strong> {metadata.get('summary', 'N/A')}</p>
        <div class="stats">
            <div class="stat-item"><strong>Nodes:</strong> {len(nodes)}</div>
            <div class="stat-item"><strong>Edges:</strong> {len(edges)}</div>
            <div class="stat-item"><strong>Themes:</strong> {', '.join(metadata.get('main_themes', []))}</div>
            <div class="stat-item"><strong>Complexity:</strong> {metadata.get('graph_complexity', 0):.2f}</div>
        </div>
    </div>
    
    <div id="graph-container"></div>
    
    <div class="legend">
        <h3>Node Types:</h3>
        <span class="legend-item" style="background: #3B82F6; color: white;">Concept</span>
        <span class="legend-item" style="background: #8B5CF6; color: white;">Topic</span>
        <span class="legend-item" style="background: #10B981; color: white;">Decision</span>
        <span class="legend-item" style="background: #F59E0B; color: white;">Question</span>
        <span class="legend-item" style="background: #EF4444; color: white;">Action</span>
        <span class="legend-item" style="background: #6366F1; color: white;">Person</span>
    </div>

    <script type="text/javascript">
        var nodes = new vis.DataSet({json.dumps(vis_nodes)});
        var edges = new vis.DataSet({json.dumps(vis_edges)});

        var container = document.getElementById('graph-container');
        var data = {{
            nodes: nodes,
            edges: edges
        }};
        var options = {{
            nodes: {{
                shape: 'box',
                borderWidth: 2,
                shadow: true,
                font: {{
                    size: 14,
                    face: 'Arial'
                }}
            }},
            edges: {{
                arrows: {{
                    to: {{
                        enabled: true,
                        scaleFactor: 1
                    }}
                }},
                smooth: {{
                    type: 'curvedCW',
                    roundness: 0.2
                }}
            }},
            physics: {{
                enabled: true,
                stabilization: {{
                    enabled: true,
                    iterations: 300
                }},
                barnesHut: {{
                    gravitationalConstant: -8000,
                    centralGravity: 0.05,
                    springLength: 300,
                    springConstant: 0.02,
                    damping: 0.15
                }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 200,
                zoomView: true,
                dragView: true
            }},
            layout: {{
                improvedLayout: true,
                hierarchical: {{
                    enabled: false,
                    direction: 'UD',
                    sortMethod: 'directed'
                }}
            }}
        }};
        
        var network = new vis.Network(container, data, options);
        
        network.on('click', function(params) {{
            if (params.nodes.length > 0) {{
                var nodeId = params.nodes[0];
                var node = nodes.get(nodeId);
                console.log('Selected node:', node);
            }}
        }});
    </script>
</body>
</html>"""
    
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"✓ HTML visualization saved to {output_file}")
    print(f"  Open it in your browser to view the interactive graph")


def main():
    parser = argparse.ArgumentParser(description='Visualize knowledge graphs')
    parser.add_argument('graph_file', nargs='?', 
                       help='Path to graph JSON file (default: test_graph_output.json)',
                       default='test_graph_output.json')
    parser.add_argument('--format', choices=['matplotlib', 'html', 'both'],
                       default='both',
                       help='Visualization format (default: both)')
    parser.add_argument('--output', '-o',
                       help='Output file name (for matplotlib: .png, for html: .html)')
    parser.add_argument('--no-show', action='store_true',
                       help='Don\'t display matplotlib plot (only save)')
    
    args = parser.parse_args()
    
    # Load graph
    graph_path = Path(args.graph_file)
    if not graph_path.exists():
        print(f"❌ Error: Graph file not found: {graph_path}")
        sys.exit(1)
    
    print(f"Loading graph from {graph_path}...")
    graph = load_graph(str(graph_path))
    
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    print(f"Graph loaded: {len(nodes)} nodes, {len(edges)} edges")
    
    # Visualize
    if args.format in ['matplotlib', 'both']:
        if HAS_MATPLOTLIB:
            output_file = args.output or 'graph_visualization.png'
            visualize_with_matplotlib(graph, output_file=output_file, 
                                    show=not args.no_show)
        else:
            print("⚠ Skipping matplotlib visualization (libraries not installed)")
    
    if args.format in ['html', 'both']:
        output_file = args.output or 'graph_visualization.html'
        if args.format == 'both':
            output_file = 'graph_visualization.html'
        visualize_with_html(graph, output_file=output_file)


if __name__ == "__main__":
    main()

