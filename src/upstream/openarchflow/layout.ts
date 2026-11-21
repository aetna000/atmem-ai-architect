// Derived from OpenArchFlow. Copyright (c) 2026 Rafael Sales. MIT.
// AtForma: type-only imports and rendering-independent integration; see THIRD_PARTY_NOTICES.md.
import dagre from 'dagre';
import type { Node, Edge } from '@xyflow/react';

export type LayoutDirection = 'TB' | 'LR';

export function getLayoutedElements(
    nodes: Node[],
    edges: Edge[],
    direction: LayoutDirection = 'TB'
) {
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));

    // Configure graph layout
    const nodeWidth = 270;  // Width of AWS nodes
    const nodeHeight = 180; // Height of AWS nodes

    dagreGraph.setGraph({
        rankdir: direction,
        nodesep: 100,  // Horizontal spacing between nodes
        ranksep: 150,  // Vertical spacing between ranks
        marginx: 50,
        marginy: 50,
    });

    // Add nodes to the graph
    nodes.forEach((node) => {
        dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
    });

    // Add edges to the graph
    edges.forEach((edge) => {
        dagreGraph.setEdge(edge.source, edge.target);
    });

    // Calculate layout
    dagre.layout(dagreGraph);

    // Apply new positions to nodes
    const layoutedNodes = nodes.map((node) => {
        const nodeWithPosition = dagreGraph.node(node.id);
        return {
            ...node,
            position: {
                x: nodeWithPosition.x - nodeWidth / 2,
                y: nodeWithPosition.y - nodeHeight / 2,
            },
        };
    });

    return { nodes: layoutedNodes, edges };
}
