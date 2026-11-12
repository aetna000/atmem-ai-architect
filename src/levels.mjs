// Zoom levels for AtMem AI Architect: System (layers) → Flow (blocks) → Block (detail).
// Explicit responsibility groups share the same underlying component graph; legacy behavior groups remain supported.
import { orderProject } from "./core.mjs";

export const LAYERS = [
  { id: "data", label: "Data", kinds: ["source", "stream", "history"] },
  { id: "ml", label: "ML pipeline", kinds: ["features", "train", "registry", "monitor"] },
  { id: "integration", label: "Integration", kinds: ["tool"] },
  { id: "intelligence", label: "Intelligence", kinds: ["predict", "agent"] },
  { id: "governance", label: "Governance", kinds: ["guard"] },
  { id: "delivery", label: "Delivery", kinds: ["output"] },
];

export function layerOf(node) {
  const group=String(node.data.topologyGroup||'').trim();
  if(group)return {id:'responsibility:'+encodeURIComponent(group),label:group,explicit:true};
  if(node.id&&node.data.kind==='resource'&&!node.data.category)return {id:'component:'+node.id,label:node.data.label,ungrouped:true};
  const layer = LAYERS.find((l) => l.kinds.includes(node.data.kind));
  if (layer) return { id: layer.id, label: layer.label };
  const category = String(node.data.category || "Infrastructure").trim();
  // Sketch blocks name the layer they belong to.
  const named = LAYERS.find((l) => l.label.toLowerCase() === category.toLowerCase());
  if (named) return { id: named.id, label: named.label };
  return { id: `infra:${category.toLowerCase()}`, label: category };
}

function depths(p) {
  const depth = {};
  let order;
  try {
    order = orderProject(p);
  } catch {
    order = p.nodes;
  }
  for (const n of order)
    depth[n.id] = Math.max(
      0,
      ...p.edges
        .filter((e) => e.target === n.id && depth[e.source] !== undefined)
        .map((e) => depth[e.source] + 1),
    );
  return depth;
}

function aggregate(states) {
  if (!states.length) return "idle";
  if (states.includes("failed")) return "failed";
  if (states.includes("running")) return "running";
  if (states.includes("cancelled")) return "cancelled";
  if (states.every((s) => s === "passed")) return "passed";
  if (states.every((s) => s === "skipped")) return "skipped";
  return "partial";
}

export function systemView(p, runStates = {}) {
  const depth = depths(p);
  const groups = new Map();
  for (const n of p.nodes.filter((x) => x.data.kind !== "note")) {
    const layer = layerOf(n);
    if (!groups.has(layer.id))
      groups.set(layer.id, { ...layer, blocks: [], providers: new Set() });
    const g = groups.get(layer.id);
    g.blocks.push(n.id);
    g.providers.add(n.data.provider);
  }
  const owner = Object.fromEntries(
    p.nodes.filter((x) => x.data.kind !== "note").map((n) => [n.id, layerOf(n).id]),
  );
  const columns = new Map();
  const ranked = [...groups.values()]
    .map((g) => ({ ...g, rank: Math.min(...g.blocks.map((id) => depth[id] ?? 0)) }))
    .sort((a, b) => a.rank - b.rank);
  const dense = [...new Set(ranked.map((g) => g.rank))];
  const nodes = ranked
    .map((g) => ({ ...g, rank: dense.indexOf(g.rank) }))
    .map((g) => {
      const row = columns.get(g.rank) || 0;
      columns.set(g.rank, row + 1);
      const states = g.blocks.map((id) => runStates[id]).filter(Boolean);
      return {
        id: `layer:${g.id}`,
        type: "layer",
        position: { x: g.rank * 320, y: row * 180 },
        data: {
          layer: g.id,
          label: g.label,
          explicit:!!g.explicit,
          ungrouped:!!g.ungrouped,
          blocks: g.blocks,
          providers: [...g.providers],
          status: aggregate(states),
          done: states.filter((s) => s === "passed").length,
        },
      };
    });
  const wires = new Map();
  for (const e of p.edges) {
    const a = owner[e.source],
      b = owner[e.target];
    if (!a || !b || a === b) continue;
    const id = `${a}->${b}`;
    if (!wires.has(id))
      wires.set(id, {
        id: `layer-wire:${id}`,
        source: `layer:${a}`,
        target: `layer:${b}`,
        type: "smoothstep",
        data: { sources: [], labels: [] },
      });
    const w = wires.get(id);
    w.data.sources.push(e.source);
    if (e.label) w.data.labels.push(e.label);
  }
  const edges = [...wires.values()].map((w) => ({
    ...w,
    label: [...new Set(w.data.labels)].slice(0,2).join(' · ') + (new Set(w.data.labels).size>2?' …':''),
  }));
  return { nodes, edges };
}

// Summarise what a proposal changes relative to the current design.
export function proposalDiff(current, next) {
  const before = new Set(current.nodes.map((n) => n.id));
  const after = new Set(next.nodes.map((n) => n.id));
  const wiresBefore = new Set(current.edges.map((e) => `${e.source}>${e.target}`));
  const wiresAfter = new Set(next.edges.map((e) => `${e.source}>${e.target}`));
  const labels = Object.fromEntries(current.nodes.map((n) => [n.id, n.data]));
  return {
    added: next.nodes.filter((n) => !before.has(n.id)).map((n) => n.data.label),
    changed: next.nodes
      .filter(
        (n) =>
          before.has(n.id) &&
          (labels[n.id].label !== n.data.label ||
            labels[n.id].provider !== n.data.provider ||
            labels[n.id].kind !== n.data.kind),
      )
      .map((n) => n.data.label),
    removed: current.nodes
      .filter((n) => !after.has(n.id))
      .map((n) => n.data.label),
    wiresAdded: [...wiresAfter].filter((w) => !wiresBefore.has(w)).length,
    wiresRemoved: [...wiresBefore].filter((w) => !wiresAfter.has(w)).length,
  };
}
