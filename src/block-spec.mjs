import {validateVerificationCases} from './verification-cases.mjs';
const sections = {
  inputs: 'Inputs and preconditions',
  outputs: 'Outputs and postconditions',
  behavior: 'Responsibilities and state',
  failures: 'Failure and recovery',
  implementation: 'Implementation',
  infrastructure: 'Infrastructure',
  operations: 'CI, release and operations',
  tests: 'Acceptance tests',
};
const validText = (value, max) => typeof value === 'string' && value.trim() && Array.from(value).length <= max;
const object = value => value && typeof value === 'object' && !Array.isArray(value);

export function validateBlockSpecs(nodes) {
  const byId = new Map(nodes.map(node => [node.id, node]));
  for (const node of nodes) {
    const { parentBlockId, buildSpec, kind } = node.data;
    if (kind === 'note' && (parentBlockId != null || buildSpec != null)) throw Error('Notes cannot have block specifications or parents.');
    const visited = new Set([node.id]);
    for (let parent = parentBlockId; parent != null; parent = byId.get(parent).data.parentBlockId) {
      if (!validText(parent, 100) || !byId.has(parent) || byId.get(parent).data.kind === 'note') throw Error('A block parent must be an existing component.');
      if (visited.has(parent)) throw Error('Block nesting contains a cycle.');
      visited.add(parent);
    }
    if (buildSpec == null) continue;
    if (!object(buildSpec) || Object.keys(buildSpec).some(key => !Object.hasOwn(sections, key) && key !== 'scenarios' && key !== 'verificationCases')) throw Error('Invalid block specification fields.');
    for (const key of Object.keys(sections)) {
      if (Object.hasOwn(buildSpec, key) && !validText(buildSpec[key], 4000)) throw Error('Invalid block specification section. Content was preserved.');
    }
    if (!Object.keys(buildSpec).length) throw Error('A block specification needs at least one section.');
    if (Object.hasOwn(buildSpec, 'scenarios')) validateScenarios(buildSpec.scenarios);
    validateVerificationCases(buildSpec.verificationCases);
  }
}

export function validateScenarios(scenarios, limit=24) {
  if (!Array.isArray(scenarios) || !scenarios.length || scenarios.length > limit) throw Error(`Provide 1–${limit} named scenarios.`);
  for (const scenario of scenarios) {
    if (!object(scenario) || Object.keys(scenario).length !== 2 || !validText(scenario.name, 150) || !Array.isArray(scenario.steps) || !scenario.steps.length || scenario.steps.length > 30) throw Error('A scenario needs a name and 1–30 ordered steps.');
    for (const step of scenario.steps) {
      const fields=['sender','receiver','action','messageKind','senderBlockId','receiverBlockId','interfaceId','requirementIds','operationId'];
      if (!object(step) || Object.keys(step).some(key=>!fields.includes(key)) || !validText(step.sender, 150) || !validText(step.receiver, 150) || !validText(step.action, 400)) throw Error('A scenario step needs a sender, receiver and action.');
      if(step.messageKind!=null&&!['command','event','query','result'].includes(step.messageKind))throw Error('Use an explicit command, event, query or result message kind.');
      for(const key of ['senderBlockId','receiverBlockId','interfaceId','operationId'])if(step[key]!=null&&!validText(step[key],100))throw Error('Scenario reference IDs need 1–100 characters.');
      if(step.requirementIds!=null&&(!Array.isArray(step.requirementIds)||!step.requirementIds.length||step.requirementIds.length>50||new Set(step.requirementIds).size!==step.requirementIds.length||step.requirementIds.some(id=>!validText(id,100))))throw Error('Scenario requirements need 1–50 unique IDs.');
    }
  }
}

export function blockChildren(nodes, parent = null) {
  return nodes.filter(node => node.data.kind !== 'note' && (node.data.parentBlockId ?? null) === parent);
}

export function removeBlocks(nodes, ids) {
  const byId = new Map(nodes.map(node => [node.id, node]));
  return nodes.filter(node => !ids.has(node.id)).map(node => {
    if (!ids.has(node.data.parentBlockId)) return node;
    let parent = node.data.parentBlockId;
    while (ids.has(parent)) parent = byId.get(parent)?.data.parentBlockId;
    const { parentBlockId, ...data } = node.data;
    return { ...node, data: { ...data, ...(parent ? { parentBlockId: parent } : {}) } };
  });
}

export function blockSpecSections(spec) {
  return Object.entries(sections).map(([key, title]) => ({ key, title, content: spec?.[key] }));
}

// Only generated aliases enter Mermaid syntax. Encode source text as labels.
export function diagramText(text) {
  return [...text.replace(/\s+/g, ' ')].map(char => /[\p{L}\p{N} .,_-]/u.test(char) ? char : `#${char.codePointAt(0)};`).join('');
}
export function scenarioDiagrams(scenario) {
  const actors = [...new Set(scenario.steps.flatMap(step => [step.sender, step.receiver]))];
  const alias = new Map(actors.map((name, index) => [name, `actor${index}`]));
  const sequence = [
    'sequenceDiagram',
    ...actors.map(name => `  participant ${alias.get(name)} as ${diagramText(name)}`),
    ...scenario.steps.map(step => `  ${alias.get(step.sender)}${step.messageKind==='result'?'-->>':'->>'}${alias.get(step.receiver)}: ${diagramText((step.messageKind?step.messageKind+': ':'Unclassified: ')+step.action)}`),
  ];
  const functional = [
    'flowchart TD',
    ...scenario.steps.map((step, index) => `  step${index}["${diagramText(`${step.sender} to ${step.receiver} — ${step.action}`)}"]`),
    ...scenario.steps.slice(1).map((_, index) => `  step${index} --> step${index + 1}`),
  ];
  const events = [
    'flowchart LR',
    ...actors.map(name=>`  ${alias.get(name)}["${diagramText(name)}"]`),
    ...scenario.steps.flatMap((step,index)=>[
      `  ${alias.get(step.sender)} --> event${index}${step.messageKind==='event'?'{{':'['}"${diagramText((step.messageKind||'Unclassified interaction')+': '+step.action)}"${step.messageKind==='event'?'}}':']'}`,
      `  event${index} --> ${alias.get(step.receiver)}`,
    ]),
  ];
  return { sequence: sequence.join('\n'), functional: functional.join('\n'), events: events.join('\n') };
}

export const interfaceFields = {
  transport: 'Transport and version', input: 'Request or event', output: 'Response or result',
  authorization: 'Identity and authority', failure: 'Failure and retry', verification: 'Contract tests',
};

export function validateInterfaceSpec(spec) {
  if (spec == null) return;
  const keys = Object.keys(interfaceFields);
  if (!object(spec) || Object.keys(spec).length !== keys.length || keys.some(key => !validText(spec[key], 4000))) {
    throw Error('A proposed interface needs all six contract sections.');
  }
}
