"""
Graph Schema Validator

Validates graph JSON against expected schema and business rules.
"""

from typing import Dict, List, Any
from datetime import datetime


class GraphValidationError(Exception):
    """Raised when graph validation fails"""
    pass


def validate_graph(graph: Dict[str, Any]) -> None:
    """
    Validate graph against schema and business rules.
    
    Args:
        graph: Graph dictionary to validate
        
    Raises:
        GraphValidationError: If graph is invalid
    """
    errors = []
    
    # Check required top-level fields
    if 'nodes' not in graph:
        errors.append("Missing 'nodes' field")
    if 'edges' not in graph:
        errors.append("Missing 'edges' field")
    
    if errors:
        raise GraphValidationError(f"Schema validation failed: {', '.join(errors)}")
    
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    
    # Validate nodes
    node_ids = []
    for i, node in enumerate(nodes):
        # Check required fields (minimal schema)
        if 'id' not in node:
            errors.append(f"Node {i} missing 'id' field")
        elif not isinstance(node['id'], str):
            errors.append(f"Node {i} has invalid 'id' (must be string)")
        
        if 'label' not in node:
            errors.append(f"Node {i} missing 'label' field")
        elif not isinstance(node['label'], str):
            errors.append(f"Node {i} has invalid 'label' (must be string)")
        
        # Importance is required for minimal schema
        if 'importance' not in node:
            errors.append(f"Node {i} missing 'importance' field")
        elif not isinstance(node['importance'], (int, float)):
            errors.append(f"Node {i} has invalid 'importance' (must be number)")
        elif not (0 <= node['importance'] <= 1):
            errors.append(f"Node {i} has 'importance' out of range (0-1): {node['importance']}")
        
        # Collect node IDs for edge validation
        if 'id' in node:
            node_ids.append(node['id'])
    
    # Check for duplicate node IDs
    if len(node_ids) != len(set(node_ids)):
        duplicates = [nid for nid in node_ids if node_ids.count(nid) > 1]
        errors.append(f"Duplicate node IDs found: {set(duplicates)}")
    
    # Validate edges (minimal schema)
    edge_ids = []
    for i, edge in enumerate(edges):
        # Check required fields
        if 'id' not in edge:
            errors.append(f"Edge {i} missing 'id' field")
        elif not isinstance(edge['id'], str):
            errors.append(f"Edge {i} has invalid 'id' (must be string)")
        
        if 'source' not in edge:
            errors.append(f"Edge {i} missing 'source' field")
        elif edge['source'] not in node_ids:
            errors.append(f"Edge {i} references non-existent source node: {edge['source']}")
        
        if 'target' not in edge:
            errors.append(f"Edge {i} missing 'target' field")
        elif edge['target'] not in node_ids:
            errors.append(f"Edge {i} references non-existent target node: {edge['target']}")
        
        # Collect edge IDs
        if 'id' in edge:
            edge_ids.append(edge['id'])
    
    # Check for duplicate edge IDs
    if len(edge_ids) != len(set(edge_ids)):
        duplicates = [eid for eid in edge_ids if edge_ids.count(eid) > 1]
        errors.append(f"Duplicate edge IDs found: {set(duplicates)}")
    
    # Business rules
    if len(nodes) > 50:
        errors.append(f"Graph has too many nodes ({len(nodes)}). Maximum is 50.")
    
    if errors:
        raise GraphValidationError(f"Graph validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

