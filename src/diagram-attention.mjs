// Presentation-only IDs: never write attention state into the project or its history.
export function diagramAttention(before, after) {
  const nodes = new Set(), edges = new Set();
  const oldNodes = new Map(before.nodes.map(n => [n.id, n]));
  const newNodes = new Set(after.nodes.map(n => n.id));
  const oldEdges = new Map(before.edges.map(e => [e.id, e]));
  const newEdges = new Set(after.edges.map(e => e.id));
  for (const n of after.nodes) {
    const old = oldNodes.get(n.id);
    if (!old || JSON.stringify([old.data, old.position, old.type]) !== JSON.stringify([n.data, n.position, n.type])) nodes.add(n.id);
  }
  for (const e of after.edges) {
    if (JSON.stringify(oldEdges.get(e.id)) !== JSON.stringify(e)) {
      edges.add(e.id); nodes.add(e.source); nodes.add(e.target);
    }
  }
  for (const e of before.edges) {
    if (!newEdges.has(e.id) || !newNodes.has(e.source) || !newNodes.has(e.target)) {
      if (newNodes.has(e.source)) nodes.add(e.source);
      if (newNodes.has(e.target)) nodes.add(e.target);
    }
  }
  return { nodes: [...nodes].filter(id => newNodes.has(id)), edges: [...edges] };
}
