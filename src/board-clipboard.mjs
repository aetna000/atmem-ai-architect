// The clipboard contains a design selection, independent of React Flow state.
export function copyBoardItems(project, selection) {
  const selected = new Set(selection);
  const children = new Map();
  for (const node of project.nodes) {
    const parent = node.data.parentBlockId;
    if (!children.has(parent)) children.set(parent, []);
    children.get(parent).push(node.id);
  }
  for (const id of selected) {
    for (const child of children.get(id) || []) selected.add(child);
  }
  const nodes = project.nodes.filter(node => selected.has(node.id));
  if (!nodes.length) return null;
  if (nodes.some(node => node.data.approvalProfile)) {
    throw Error('Blocks with a bound approval workflow need a new workflow configuration before duplication.');
  }
  return structuredClone({
    projectId: project.id,
    nodes,
    edges: project.edges.filter(edge => selected.has(edge.source) && selected.has(edge.target)),
  });
}

export function pasteBoardItems(project, clipboard, position, parentId) {
  if (clipboard.projectId !== project.id) throw Error('Paste blocks into the project they were copied from.');
  const copy = structuredClone(clipboard);
  const ids = new Map(copy.nodes.map(node => [node.id, crypto.randomUUID()]));
  const edgeIds = new Map(copy.edges.map(edge => [edge.id, crypto.randomUUID()]));
  const currentIds = new Set(project.nodes.map(node => node.id));
  const requirements = new Set((project.needs || []).map(row => row.id));
  const origin = {
    x: Math.min(...copy.nodes.map(node => node.position.x)),
    y: Math.min(...copy.nodes.map(node => node.position.y)),
  };
  const mapBlock = id => ids.get(id) || (currentIds.has(id) ? id : undefined);
  const nodes = copy.nodes.map(({ id, type, data, position: previous }) => {
    if (data.kind !== 'note') data.parentBlockId = ids.get(data.parentBlockId) || parentId;
    for (const scenario of data.buildSpec?.scenarios || []) {
      for (const step of scenario.steps) {
        step.senderBlockId = mapBlock(step.senderBlockId);
        step.receiverBlockId = mapBlock(step.receiverBlockId);
        step.interfaceId = edgeIds.get(step.interfaceId);
        delete step.operationId;
        for (const key of ['senderBlockId', 'receiverBlockId', 'interfaceId']) {
          if (!step[key]) delete step[key];
        }
        step.requirementIds = step.requirementIds?.filter(id => requirements.has(id));
        if (!step.requirementIds?.length) delete step.requirementIds;
      }
    }
    if (data.buildSpec?.verificationCases) {
      const cases = data.buildSpec.verificationCases.filter(row => row.requirementIds.every(id => requirements.has(id)));
      for (const row of cases) {
        delete row.operationId;
        if (edgeIds.has(row.interfaceId)) row.interfaceId = edgeIds.get(row.interfaceId);
        else delete row.interfaceId;
      }
      if (cases.length) data.buildSpec.verificationCases = cases;
      else delete data.buildSpec.verificationCases;
      if (!Object.keys(data.buildSpec).length) delete data.buildSpec;
    }
    return {
      id: ids.get(id), type, data,
      position: { x: position.x + previous.x - origin.x, y: position.y + previous.y - origin.y },
    };
  });
  const edges = copy.edges.map(({ selected, ...edge }) => ({
    ...edge, id: edgeIds.get(edge.id), source: ids.get(edge.source), target: ids.get(edge.target),
  }));
  return { nodes, edges };
}
