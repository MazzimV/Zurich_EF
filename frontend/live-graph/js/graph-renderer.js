/**
 * Graph Renderer with D3 Force Simulation
 *
 * Renders node-edge network graphs with smooth transitions
 */

class GraphRenderer {
  constructor(containerId, options = {}) {
    this.containerId = containerId;
    this.container = d3.select(`#${containerId}`);

    // Configuration
    this.width = options.width || 600;
    this.height = options.height || 500;
    this.nodeRadiusScale = options.nodeRadiusScale || [5, 30];
    this.edgeWidthScale = options.edgeWidthScale || [1, 5];

    // Graph data
    this.nodes = [];
    this.edges = [];
    this.currentVersion = 0;

    // D3 selections
    this.svg = null;
    this.simulation = null;
    this.linkGroup = null;
    this.nodeGroup = null;

    // Node expansion
    this.isPaused = false;
    this.onNodeClick = options.onNodeClick || null;

    // Initialize
    this._initSVG();
    this._initSimulation();
  }

  /**
   * Initialize SVG canvas
   */
  _initSVG() {
    // Clear any existing SVG
    this.container.selectAll('svg').remove();

    // Create SVG
    this.svg = this.container
      .append('svg')
      .attr('width', this.width)
      .attr('height', this.height)
      .attr('viewBox', [0, 0, this.width, this.height]);

    // Add zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        this.svg.select('g').attr('transform', event.transform);
      });

    this.svg.call(zoom);

    // Main group for zoom/pan
    const g = this.svg.append('g');

    // Add arrow marker definition for directed edges
    this.svg.append('defs').append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '-0 -5 10 10')
      .attr('refX', 20)
      .attr('refY', 0)
      .attr('orient', 'auto')
      .attr('markerWidth', 8)
      .attr('markerHeight', 8)
      .append('path')
      .attr('d', 'M 0,-5 L 10,0 L 0,5')
      .attr('fill', '#3B82F6')  // Blue to match theme
      .attr('opacity', 0.8);  // Slightly transparent for elegance

    // Create groups for edges and nodes (order matters for layering)
    this.linkGroup = g.append('g').attr('class', 'links');
    this.nodeGroup = g.append('g').attr('class', 'nodes');
  }

  /**
   * Initialize D3 force simulation
   */
  _initSimulation() {
    this.simulation = d3.forceSimulation()
      .force('link', d3.forceLink()
        .id(d => d.id)
        .distance(d => 100 / (d.strength || 0.5))  // Stronger edges = shorter distance
      )
      .force('charge', d3.forceManyBody()
        .strength(-300)  // Repulsion between nodes
      )
      .force('center', d3.forceCenter(this.width / 2, this.height / 2))
      .force('collision', d3.forceCollide()
        .radius(d => this._getNodeRadius(d) + 5)  // Prevent overlap
      )
      .alphaDecay(0.02)  // Slower cooling for smoother animation
      .on('tick', () => this._onTick());
  }

  /**
   * Update graph with new data
   * @param {Object} graphData - Graph data from orchestrator
   */
  updateGraph(graphData) {
    if (!graphData || !graphData.nodes) {
      console.error('Invalid graph data:', graphData);
      return;
    }

    console.log(`Updating graph to version ${graphData.version || 'N/A'}`);
    console.log(`Nodes: ${graphData.nodes.length}, Edges: ${graphData.edges?.length || 0}`);

    this.currentVersion = graphData.version || 0;

    // Update data (deep copy to preserve D3's internal state)
    this.nodes = this._mergeNodes(graphData.nodes);
    this.edges = graphData.edges ? this._prepareEdges(graphData.edges) : [];

    // IMPORTANT: Tell simulation about nodes and edges FIRST
    // This allows D3 to convert edge source/target strings to node object references
    this.simulation.nodes(this.nodes);
    this.simulation.force('link').links(this.edges);

    console.log('Simulation nodes:', this.simulation.nodes().length);
    console.log('Simulation links:', this.simulation.force('link').links().length);
    console.log('First edge after force link:', this.edges[0]);
    console.log('Edge 0 source type:', typeof this.edges[0]?.source, this.edges[0]?.source);
    console.log('Edge 0 target type:', typeof this.edges[0]?.target, this.edges[0]?.target);

    // NOW update visualization (edges will have proper source/target references)
    this._updateLinks();
    this._updateNodes();

    // Restart simulation
    this.simulation.alpha(0.3).restart();  // Gentle restart
  }

  /**
   * Merge new nodes with existing ones to preserve positions
   */
  _mergeNodes(newNodes) {
    const existingNodesMap = new Map(this.nodes.map(n => [n.id, n]));

    return newNodes.map(node => {
      const existing = existingNodesMap.get(node.id);
      if (existing) {
        // Preserve position and velocity
        return {
          ...node,
          x: existing.x,
          y: existing.y,
          vx: existing.vx,
          vy: existing.vy
        };
      }
      // New node - will be positioned by force simulation
      return { ...node };
    });
  }

  /**
   * Prepare edges with source/target references
   */
  _prepareEdges(edges) {
    return edges.map(edge => ({
      ...edge,
      source: edge.source,  // D3 will replace with node object reference
      target: edge.target
    }));
  }

  /**
   * Update link elements (edges)
   */
  _updateLinks() {
    console.log(`Updating ${this.edges.length} edges`);

    // Data join with key function for stable identity
    const link = this.linkGroup
      .selectAll('line')
      .data(this.edges, d => d.id);

    // EXIT: Remove old edges
    link.exit()
      .transition()
      .duration(500)
      .style('opacity', 0)
      .remove();

    // ENTER: Add new edges
    const linkEnter = link.enter()
      .append('line')
      .attr('stroke', '#3B82F6')  // Blue to match theme
      .attr('stroke-opacity', 1)  // Fully opaque
      .attr('stroke-width', d => this._getEdgeWidth(d))
      .attr('marker-end', 'url(#arrowhead)')  // Add arrow marker
      .attr('opacity', 1);  // Start fully visible (no transition needed for edges)

    // UPDATE: Merge enter + update selections
    this.linkSelection = linkEnter.merge(link);

    // Ensure all edges are visible
    this.linkSelection.attr('opacity', 1);

    // Update edge properties
    this.linkSelection
      .transition()
      .duration(500)
      .attr('stroke-width', d => this._getEdgeWidth(d));
  }

  /**
   * Update node elements
   */
  _updateNodes() {
    // Data join with key function for stable identity
    const node = this.nodeGroup
      .selectAll('g.node')
      .data(this.nodes, d => d.id);

    // EXIT: Remove old nodes
    node.exit()
      .transition()
      .duration(500)
      .style('opacity', 0)
      .remove();

    // ENTER: Add new nodes
    const nodeEnter = node.enter()
      .append('g')
      .attr('class', 'node')
      .style('opacity', 0)
      .style('cursor', d => this.isPaused ? 'pointer' : 'default')
      .call(this._addDragBehavior())
      .call(this._addClickBehavior());

    // Add circle
    nodeEnter.append('circle')
      .attr('r', d => this._getNodeRadius(d))
      .attr('fill', d => d.color || '#3B82F6');

    // Add label
    nodeEnter.append('text')
      .attr('dx', d => this._getNodeRadius(d) + 5)
      .attr('dy', '.35em')
      .attr('font-size', '12px')
      .attr('fill', '#1E3A8A')
      .text(d => d.label);

    // Add title for hover tooltip
    nodeEnter.append('title')
      .text(d => `${d.label}\nImportance: ${d.importance?.toFixed(2) || 'N/A'}`);

    // Transition in new nodes
    nodeEnter
      .transition()
      .duration(500)
      .style('opacity', 1);

    // UPDATE: Merge enter + update selections
    this.nodeSelection = nodeEnter.merge(node);

    // Update node properties with transition
    this.nodeSelection
      .style('cursor', d => this.isPaused ? 'pointer' : 'default')
      .call(this._addClickBehavior());

    this.nodeSelection.select('circle')
      .transition()
      .duration(500)
      .attr('r', d => this._getNodeRadius(d))
      .attr('fill', d => d.color || '#3B82F6');

    this.nodeSelection.select('text')
      .transition()
      .duration(500)
      .attr('dx', d => this._getNodeRadius(d) + 5)
      .text(d => d.label);

    this.nodeSelection.select('title')
      .text(d => `${d.label}\nImportance: ${d.importance?.toFixed(2) || 'N/A'}${this.isPaused ? '\n(Click to expand)' : ''}`);
  }

  /**
   * Force simulation tick handler
   */
  _onTick() {
    // Debug: log first few ticks
    if (!this._tickCount) this._tickCount = 0;
    this._tickCount++;
    if (this._tickCount <= 3) {
      console.log(`Tick ${this._tickCount}: linkSelection exists:`, !!this.linkSelection,
                  'edges:', this.edges.length);
    }

    // Update edge positions
    if (this.linkSelection) {
      this.linkSelection
        .attr('x1', d => {
          if (!d.source || !d.source.x) {
            console.warn('Edge missing source position:', d);
            return 0;
          }
          return d.source.x;
        })
        .attr('y1', d => d.source ? d.source.y : 0)
        .attr('x2', d => d.target ? d.target.x : 0)
        .attr('y2', d => d.target ? d.target.y : 0);
    }

    // Update node positions
    if (this.nodeSelection) {
      this.nodeSelection
        .attr('transform', d => `translate(${d.x}, ${d.y})`);
    }
  }

  /**
   * Add drag behavior to nodes
   */
  _addDragBehavior() {
    const dragStarted = (event, d) => {
      if (!event.active) this.simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    };

    const dragged = (event, d) => {
      d.fx = event.x;
      d.fy = event.y;
    };

    const dragEnded = (event, d) => {
      if (!event.active) this.simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    };

    return d3.drag()
      .on('start', dragStarted)
      .on('drag', dragged)
      .on('end', dragEnded);
  }

  /**
   * Add click behavior to nodes (only when paused)
   */
  _addClickBehavior() {
    return selection => {
      selection.on('click', (event, d) => {
        // Only handle clicks when paused and callback is set
        if (this.isPaused && this.onNodeClick) {
          event.stopPropagation();
          console.log(`Node clicked: ${d.id} - ${d.label}`);
          this.onNodeClick(d);
        }
      });
    };
  }

  /**
   * Set pause state (enables/disables node clicking)
   */
  setPaused(isPaused) {
    this.isPaused = isPaused;
    
    // Update cursor and tooltip on existing nodes
    if (this.nodeSelection) {
      this.nodeSelection
        .style('cursor', d => this.isPaused ? 'pointer' : 'default');
      
      this.nodeSelection.select('title')
        .text(d => `${d.label}\nImportance: ${d.importance?.toFixed(2) || 'N/A'}${this.isPaused ? '\n(Click to expand)' : ''}`);
    }
  }

  /**
   * Set callback for node clicks
   */
  setOnNodeClick(callback) {
    this.onNodeClick = callback;
  }

  /**
   * Calculate node radius based on importance
   */
  _getNodeRadius(node) {
    const importance = node.importance || 0.5;
    const [minRadius, maxRadius] = this.nodeRadiusScale;
    return minRadius + (maxRadius - minRadius) * importance;
  }

  /**
   * Calculate edge width based on strength
   */
  _getEdgeWidth(edge) {
    const strength = edge.strength || 0.5;
    const [minWidth, maxWidth] = this.edgeWidthScale;
    return minWidth + (maxWidth - minWidth) * strength;
  }

  /**
   * Clear the graph
   */
  clear() {
    this.nodes = [];
    this.edges = [];
    this.linkGroup.selectAll('*').remove();
    this.nodeGroup.selectAll('*').remove();
    this.simulation.stop();
  }

  /**
   * Resize canvas
   */
  resize(width, height) {
    this.width = width;
    this.height = height;
    this.svg
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', [0, 0, width, height]);

    this.simulation
      .force('center', d3.forceCenter(width / 2, height / 2))
      .alpha(0.3)
      .restart();
  }

  /**
   * Get current graph stats
   */
  getStats() {
    return {
      version: this.currentVersion,
      nodeCount: this.nodes.length,
      edgeCount: this.edges.length
    };
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = GraphRenderer;
}
