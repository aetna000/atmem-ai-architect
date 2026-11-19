export const systemDiagramKinds = {
  components: 'Logical components',
  functions: 'Functional flow',
  sequence: 'Sequence scenario',
};

const portOwners = { functionPort: ['function'], componentPort: ['component', 'actor'] };
export const diagramElements = { components: ['component', 'actor'], functions: ['function'], sequence: ['component', 'actor'] };
const stableId = /^[a-z0-9][a-z0-9_-]{0,99}$/i;
const elementKinds = new Set(['actor', 'component', 'function', ...Object.keys(portOwners)]);
const fail = message => { throw new Error('System model: ' + message); };
const validText = (value, max) => typeof value === 'string' && value.trim() && value.length <= max;

function fields(value, required, optional = []) {
  if (!value || typeof value !== 'object' || Array.isArray(value) ||
      required.some(key => !Object.hasOwn(value, key)) ||
      Object.keys(value).some(key => !required.includes(key) && !optional.includes(key))) {
    fail('missing or unsupported fields in a model record.');
  }
}

function rows(value, limit, label, min = 0) {
  if (!Array.isArray(value) || value.length > limit || value.length < min) fail(label + ' is outside its collection bounds.');
  return value;
}

export function validateSystemModel(model, project) {
  fields(model, ['format', 'version', 'id', 'elements', 'exchanges', 'diagrams'], ['authoring']);
  if(model.authoring!==undefined&&model.authoring!=='manual')fail('unsupported authoring mode.');
  const draft=model.authoring==='manual'&&!project;
  if (model.format !== 'atmem.system-model' || model.version !== 1) fail('unsupported format or version.');
  const ids = new Set();
  const elements = new Map();
  const exchanges = new Map();
  const blocks = project && new Map(project.nodes.filter(node => node.data.kind !== 'note').map(node => [node.id, node]));
  const interfaces = project && new Map(project.edges.map(edge => [edge.id, edge]));
  const requirements = project && new Set((project.needs || []).map(row => row.id));

  function identity(record) {
    if (typeof record.id !== 'string' || !stableId.test(record.id) || record.id in Object.prototype || ids.has(record.id)) {
      fail('each record needs a unique, safe ID.');
    }
    ids.add(record.id);
  }

  function refs(value, limit, label) {
    const result = rows(value, limit, label);
    if (result.some(id => !validText(id, 100)) || new Set(result).size !== result.length) fail(label + ' needs unique reference IDs.');
    return result;
  }

  function provenance(record) {
    if (!validText(record.name, 150) || !validText(record.description, 2000)) fail('names and responsibility descriptions are required.');
    const trace = refs(record.requirementIds, 50, 'requirement trace');
    if (requirements && trace.some(id => !requirements.has(id))) fail(record.id + ' references an unknown requirement.');
    if (!['source', 'proposed'].includes(record.basis) || (record.basis === 'source' && !trace.length)) {
      fail(record.id + ' needs a design basis and a requirement trace for source-backed claims.');
    }
  }

  identity(model);
  for (const element of rows(model.elements, 800, 'elements', draft?0:1)) {
    if (!elementKinds.has(element?.kind)) fail('unknown element kind.');
    const common = ['id', 'name', 'kind', 'description', 'basis', 'requirementIds'];
    if (Object.hasOwn(portOwners, element.kind)) {
      fields(element, [...common, 'ownerId', 'direction']);
      if (!['in', 'out', 'inout'].includes(element.direction)) fail('invalid port direction.');
    } else {
      fields(element, common, element.kind === 'function' ? ['parentId', 'allocatedTo'] :
        element.kind === 'component' ? ['parentId', 'blockId'] : []);
      if (element.blockId !== undefined && (!validText(element.blockId, 100) || (blocks && !blocks.has(element.blockId)))) {
        fail(element.id + ' references an unknown implementation block.');
      }
    }
    identity(element);
    provenance(element);
    elements.set(element.id, element);
  }

  for (const element of elements.values()) {
    if (Object.hasOwn(portOwners, element.kind) && !portOwners[element.kind].includes(elements.get(element.ownerId)?.kind)) {
      fail(element.id + ' has an invalid port owner.');
    }
    if (element.allocatedTo !== undefined && !['component', 'actor'].includes(elements.get(element.allocatedTo)?.kind)) {
      fail(element.id + ' has an invalid function allocation.');
    }
    const seen = new Set([element.id]);
    for (let id = element.parentId; id !== undefined; id = elements.get(id).parentId) {
      if (elements.get(id)?.kind !== element.kind || seen.has(id)) fail(element.id + ' has invalid or cyclic nesting.');
      seen.add(id);
    }
  }

  for (const exchange of rows(model.exchanges, 1200, 'exchanges', draft?0:1)) {
    const common = ['id', 'name', 'kind', 'description', 'basis', 'requirementIds', 'source', 'target', 'items'];
    const functional = exchange?.kind === 'functional';
    if (!functional && exchange?.kind !== 'component') fail('unknown exchange kind.');
    fields(exchange, common, functional ? ['componentExchangeId'] : ['interfaceId']);
    identity(exchange);
    provenance(exchange);
    if (rows(exchange.items, 30, 'exchange items', 1).some(item => !validText(item, 150)) ||
        new Set(exchange.items).size !== exchange.items.length) fail(exchange.id + ' needs named, unique exchange items.');
    const source = elements.get(exchange.source);
    const target = elements.get(exchange.target);
    const portKind = functional ? 'functionPort' : 'componentPort';
    if (source?.kind !== portKind || target?.kind !== portKind || source.ownerId === target.ownerId ||
        source.direction === 'in' || target.direction === 'out') fail(exchange.id + ' has incompatible port endpoints.');
    if (exchange.interfaceId !== undefined) {
      const edge = interfaces?.get(exchange.interfaceId);
      if (!validText(exchange.interfaceId, 100) || (interfaces && (!edge ||
          elements.get(source.ownerId).blockId !== edge.source || elements.get(target.ownerId).blockId !== edge.target))) {
        fail(exchange.id + ' must bind to a board interface with the same allocated endpoints.');
      }
    }
    exchanges.set(exchange.id, exchange);
  }

  const owner = portId => elements.get(elements.get(portId).ownerId);
  for (const exchange of exchanges.values()) {
    if (exchange.componentExchangeId === undefined) continue;
    const component = exchanges.get(exchange.componentExchangeId);
    if (component?.kind !== 'component' || owner(exchange.source).allocatedTo !== owner(component.source).id ||
        owner(exchange.target).allocatedTo !== owner(component.target).id) {
      fail(exchange.id + ' and its component exchange disagree on function allocations.');
    }
  }

  const kinds = new Set();
  for (const diagram of rows(model.diagrams, 120, 'diagrams', draft?0:1)) {
    if (!Object.hasOwn(diagramElements, diagram?.kind)) fail('unknown diagram kind.');
    fields(diagram, ['id', 'name', 'kind', 'elementIds', 'exchangeIds'], ['positions']);
    identity(diagram);
    if (!validText(diagram.name, 150)) fail('diagram needs a name.');
    const sequence = diagram.kind === 'sequence';
    const visible = new Set(refs(diagram.elementIds, sequence ? 12 : 40, 'diagram elements'));
    if ((!draft&&!visible.size) || [...visible].some(id => !diagramElements[diagram.kind].includes(elements.get(id)?.kind))) {
      fail(diagram.id + ' has invalid diagram elements.');
    }
    if(diagram.positions!==undefined){
      if(sequence||!diagram.positions||typeof diagram.positions!=='object'||Array.isArray(diagram.positions))fail('invalid view positions.');
      for(const [id,point] of Object.entries(diagram.positions)){
        fields(point,['x','y']);
        if(!visible.has(id)||![point.x,point.y].every(value=>Number.isFinite(value)&&value>=0&&value<=100000))fail('invalid diagram position.');
      }
    }
    const links = sequence ? rows(diagram.exchangeIds, 60, 'ordered scenario exchanges', draft?0:1) :
      refs(diagram.exchangeIds, 100, 'diagram exchanges');
    for (const id of links) {
      const exchange = exchanges.get(id);
      if (exchange?.kind !== (diagram.kind === 'functions' ? 'functional' : 'component') ||
          !visible.has(owner(exchange.source).id) || !visible.has(owner(exchange.target).id)) {
        fail(diagram.id + ' has an exchange without two visible, compatible participants.');
      }
    }
    kinds.add(diagram.kind);
  }
  if (!draft&&!Object.keys(systemDiagramKinds).every(kind => kinds.has(kind))) {
    fail('include logical component, functional flow and sequence views.');
  }
  return model;
}

export function reconcileSystemModel(previous, proposed, project) {
  if (proposed === undefined) return previous;
  validateSystemModel(proposed, project);
  if (!previous) return proposed;
  if (previous.id !== proposed.id) fail('a refinement must preserve the model ID.');
  const records = new Map([...proposed.elements, ...proposed.exchanges].map(record => [record.id, record]));
  for (const before of [...previous.elements, ...previous.exchanges]) {
    const after = records.get(before.id);
    if (!after || before.kind !== after.kind || before.ownerId !== after.ownerId ||
        (before.blockId !== undefined && before.blockId !== after.blockId)) {
      fail('a refinement cannot remove or silently reassign ' + before.id + '.');
    }
  }
  const manualLayouts=new Map(previous.diagrams.filter(view=>view.positions).map(view=>[view.id,view]));
  if(!manualLayouts.size)return proposed;
  return {...proposed,diagrams:proposed.diagrams.map(view=>{
    const previousView=manualLayouts.get(view.id);
    if(previousView?.kind!==view.kind)return view;
    const positions=Object.fromEntries(Object.entries(previousView.positions).filter(([id])=>view.elementIds.includes(id)));
    return {...view,positions};
  })};
}

export function systemModelIndex(model) {
  const elements = new Map(model.elements.map(row => [row.id, row]));
  const exchanges = new Map(model.exchanges.map(row => [row.id, row]));
  function participants(exchange) {
    return [elements.get(exchange.source).ownerId, elements.get(exchange.target).ownerId];
  }
  return { elements, exchanges, participants };
}

export function systemModelAssignment(model, blockId) {
  const owned = new Set(model.elements.filter(element => element.blockId === blockId).map(element => element.id));
  for (const element of model.elements) if (owned.has(element.allocatedTo)) owned.add(element.id);
  for (const element of model.elements) if (owned.has(element.ownerId)) owned.add(element.id);
  const index = systemModelIndex(model);
  const exchangeIds = model.exchanges.filter(exchange => index.participants(exchange).some(id => owned.has(id))).map(exchange => exchange.id);
  return {
    elementIds: [...owned],
    exchangeIds,
    diagramIds: model.diagrams.filter(diagram => diagram.elementIds.some(id => owned.has(id))).map(diagram => diagram.id),
  };
}

// A saved model retains traceability. The canvas only displays live board bindings.
export function systemModelOnBoard(model, project) {
  const blocks = new Set(project.nodes.filter(node => node.data.kind !== 'note').map(node => node.id));
  const interfaces = new Set(project.edges.map(edge => edge.id));
  const excluded = new Set(model.elements.filter(element => element.blockId && !blocks.has(element.blockId)).map(element => element.id));
  if (!excluded.size && model.exchanges.every(exchange => !exchange.interfaceId || interfaces.has(exchange.interfaceId))) return model;

  for (const element of model.elements) {
    if (element.allocatedTo && excluded.has(element.allocatedTo)) excluded.add(element.id);
  }
  for (const element of model.elements) {
    if (element.ownerId && excluded.has(element.ownerId)) excluded.add(element.id);
  }
  const elements = model.elements.filter(element => !excluded.has(element.id)).map(element => {
    if (!excluded.has(element.parentId)) return element;
    const {parentId, ...rest} = element;
    return rest;
  });
  const retained = model.exchanges.filter(exchange =>
    !excluded.has(exchange.source) && !excluded.has(exchange.target) &&
    (!exchange.interfaceId || interfaces.has(exchange.interfaceId)));
  const exchangeIds = new Set(retained.map(exchange => exchange.id));
  const exchanges = retained.map(exchange => {
    if (!exchange.componentExchangeId || exchangeIds.has(exchange.componentExchangeId)) return exchange;
    const {componentExchangeId, ...rest} = exchange;
    return rest;
  });
  const diagrams = model.diagrams.map(diagram => ({
    ...diagram,
    elementIds: diagram.elementIds.filter(id => !excluded.has(id)),
    exchangeIds: diagram.exchangeIds.filter(id => exchangeIds.has(id)),
  })).filter(diagram => model.authoring==='manual'||(diagram.elementIds.length && (diagram.kind !== 'sequence' || diagram.exchangeIds.length)));
  return {...model, elements, exchanges, diagrams};
}

export function removeModelRecord(model, id, diagramId) {
  const index=systemModelIndex(model);
  const removedElements=new Set();
  const removedExchanges=new Set();
  if(index.elements.has(id)){
    removedElements.add(id);
    if(!diagramId)for(const element of model.elements)if(element.ownerId===id)removedElements.add(element.id);
    for(const exchange of model.exchanges){
      if(removedElements.has(exchange.source)||removedElements.has(exchange.target)||
        index.participants(exchange).some(owner=>removedElements.has(owner)))removedExchanges.add(exchange.id);
    }
  }else if(index.exchanges.has(id))removedExchanges.add(id);
  const diagrams=model.diagrams.map(diagram=>{
    if(diagramId&&diagram.id!==diagramId)return diagram;
    const {positions,...view}=diagram;
    return {...view,
      ...(positions?{positions:Object.fromEntries(Object.entries(positions).filter(([id])=>!removedElements.has(id)))}:{}),
      elementIds:diagram.elementIds.filter(id=>!removedElements.has(id)),
      exchangeIds:diagram.exchangeIds.filter(id=>!removedExchanges.has(id)),
    };
  });
  if(diagramId)return {...model,diagrams};
  const elements=model.elements.filter(element=>!removedElements.has(element.id)).map(original=>{
    const element={...original};
    for(const key of ['parentId','allocatedTo'])if(removedElements.has(element[key]))delete element[key];
    return element;
  });
  const exchanges=model.exchanges.filter(exchange=>!removedExchanges.has(exchange.id)).map(original=>{
    if(!removedExchanges.has(original.componentExchangeId))return original;
    const {componentExchangeId,...exchange}=original;
    return exchange;
  });
  return {...model,elements,exchanges,diagrams};
}
