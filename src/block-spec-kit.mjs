import {verificationCaseMarkdown} from './verification-cases.mjs';
import { blockChildren, blockSpecSections, scenarioDiagrams, interfaceFields } from './block-spec.mjs';
import {validateEngineeringModel} from './engineering-model.mjs';
import {systemModelAssignment,validateSystemModel} from './system-model.mjs';

const list = rows => rows.length ? rows.map(row => `- ${row}`).join('\n') : 'None recorded.';
const slug = id => Array.from(new TextEncoder().encode(id), byte => byte.toString(16).padStart(2, '0')).join('');
export const blockSpecPath = id => `spec-kit/blocks/block-${slug(id)}`;

export function blockSpecKit(project, stamp, tasks) {
  const files = {};
  const model=project.extensions?.engineeringModel;
  const systemModel=project.extensions?.systemModel;
  if(systemModel){
    validateSystemModel(systemModel);
    files['spec-kit/system/system-model.json']=JSON.stringify(systemModel,null,2)+'\n';
  }
  if(model){
    validateEngineeringModel(model);
    files['spec-kit/system/engineering-model.json']=JSON.stringify(model,null,2)+'\n';
  }
  const components = [];
  const byId = new Map(project.nodes.map(node => [node.id, node]));
  function visit(parent, depth) {
    for (const node of blockChildren(project.nodes, parent)) {
      const { id, data } = node;
      const path = blockSpecPath(id);
      const systemAssignment=systemModel&&systemModelAssignment(systemModel,id);
      if(systemAssignment?.elementIds.length){
        files[`${path}/system-model-assignment.json`]=JSON.stringify({modelPath:'../../system/system-model.json',blockId:id,...systemAssignment},null,2)+'\n';
      }
      if(model){
        const assigned=model.elements.filter(element=>element.blockId===id).map(element=>element.id);
        const assignedIds=new Set(assigned);
        const views=model.diagrams.filter(view=>view.placements.some(p=>assignedIds.has(p.elementId))).map(view=>view.id);
        files[`${path}/engineering-model.json`]=JSON.stringify({format:'atmem.engineering-model-assignment',version:1,blockId:id,modelPath:'../../system/engineering-model.json',assignedElementIds:assigned,diagramIds:views,contextOnly:true,boundary:'Only assigned elements belong to this module. Other elements and diagram participants are shared context. Model presence does not prove implementation or design acceptance.'},null,2)+'\n';
      }
      const children = blockChildren(project.nodes, id);
      const requirements = (project.needs || []).filter(row => row.links?.includes(id));
      const questions = (project.openQuestions || []).filter(row => row.status === 'open' && row.links?.includes(id));
      const edges = project.edges.filter(edge => edge.source === id || edge.target === id);
      const section = key => blockSpecSections(data.buildSpec).find(row => row.key === key)?.content || 'Open engineering work. Specify this section before accepting implementation.';
      const blockTasks = tasks.filter(task => task.componentIds?.includes(id));
      const taskIds = blockTasks.map(task => task.id);
      const missing = blockSpecSections(data.buildSpec).filter(row => !row.content).map(row => row.key);
      if (!data.buildSpec?.scenarios) missing.push('scenarios');
      components.push({ id, label: data.label, parent, depth, path, missing, taskIds, requirementIds: requirements.map(row => row.id), questionIds: questions.map(row => row.id) });
      files[`${path}/spec.md`] = [
        `# ${data.label}\n\n${stamp}`,
        'Status: proposed design. Check open sections and source requirements before implementing.',
        ...(model?['Read [the engineering model assignment](engineering-model.json) and [shared typed model](../../system/engineering-model.json). Preserve element identities across views; adjacent elements remain context.']:[]),
        ...(systemAssignment?.elementIds.length?['Read [the logical model assignment](system-model-assignment.json) and [shared system model](../../system/system-model.json) for allocated functions, ports, exchanges and scenarios.']:[]),
        `## Responsibility\n\n${data.description || 'Clarify the block responsibility.'}\n\n${section('behavior')}`,
        `## Decomposition\n\nParent: ${parent ? byId.get(parent).data.label : 'System'}\n\n${list(children.map(child => `[${child.data.label}](../block-${slug(child.id)}/spec.md)`))}`,
        `## Inputs and preconditions\n\n${section('inputs')}`,
        `## Outputs and postconditions\n\n${section('outputs')}`,
        `## Boundaries\n\n${list(edges.map(edge => `${edge.id} · ${byId.get(edge.source).data.label} → ${byId.get(edge.target).data.label} · ${edge.label}`))}`,
        ...edges.filter(edge => edge.interfaceSpec).map(edge => `### Proposed interface ${edge.id}\n\n${Object.entries(interfaceFields).map(([key, title]) => `#### ${title}\n\n${edge.interfaceSpec[key]}`).join('\n\n')}`),
        `## Failure and recovery\n\n${section('failures')}`,
        `## Implementation\n\n${section('implementation')}`,
        `## Traceability\n\n${list(requirements.map(row => `${row.id} · ${row.statement}`))}\n\nTasks: ${taskIds.join(', ') || 'Open engineering work.'}\n\n${list(questions.map(row => `${row.id} · ${row.question}`))}`,
        '[Implementation plan](plan.md) · [Infrastructure and operations](infrastructure-devops.md) · [Testing](testing.md) · [Scenarios](scenarios.md) · [Assigned tasks](tasks.json)',
      ].join('\n\n') + '\n';
      files[`${path}/infrastructure-devops.md`] = `# ${data.label} infrastructure and operations\n\n${stamp}\n\n## Infrastructure\n\n${section('infrastructure')}\n\n## CI, release and operations\n\n${section('operations')}\n`;
      files[`${path}/tasks.json`]=JSON.stringify({componentId:id,requirementIds:requirements.map(row=>row.id),masterTaskFile:'../../tasks.json',tasks:blockTasks},null,2)+'\n';
      const prerequisites=phases=>[...new Set(blockTasks.filter(task=>phases.includes(task.phase)).flatMap(task=>task.dependsOn).filter(dependency=>!taskIds.includes(dependency)))];
      const externalDependencies=prerequisites(['Contracts','Components']);
      files[`${path}/plan.md`]=[
        `# Implementation plan for ${data.label}\n\n${stamp}`,
        `## Scope and responsibility\n\n${data.description||'Define responsibility before implementation.'}\n\n${section('implementation')}`,
        `## Local build prerequisites\n\nRead [the master task graph](../../tasks.json). These prerequisites apply to local contracts and component implementation.\n\n${list(externalDependencies)}`,
        `## Integration prerequisites\n\nAdjacent implementations are needed for connected integration evidence, not for local work using explicit contract doubles.\n\n${list(prerequisites(['Integration']))}`,
        `## Qualification prerequisites\n\nThese gate the full requirement or live counterpart evidence. They do not establish that local code must wait for staging.\n\n${list(prerequisites(['Acceptance','Staging verification']))}`,
        `## Work sequence\n\n${blockTasks.map(task=>`### ${task.id} · ${task.title}\n\nDependencies · ${task.dependsOn.join(', ')||'None'}\n\n${list(task.steps||[])}\n\nCompletion evidence\n\n${list(task.acceptance||[])}`).join('\n\n')||'Implementation tasks remain open.'}`,
        `## Integration boundaries\n\n${list(edges.map(edge=>`${edge.id} · ${byId.get(edge.source).data.label} → ${byId.get(edge.target).data.label}`))}`,
        `## Release and rollback\n\n${section('operations')}`,
      ].join('\n\n')+'\n';
      files[`${path}/WORK_ORDER.md`]=`# Work order for ${data.label}\n\n${stamp}\n\nRead [the block spec](spec.md), [implementation plan](plan.md), [infrastructure and operations](infrastructure-devops.md), [acceptance tests](testing.md), and [assigned tasks](tasks.json). Find shared dependencies in [the master task graph](../../tasks.json).\n\nImplement the assigned responsibility in its agreed deployment unit. Keep adjacent interfaces stable and qualify each integration with its owner. Record requirements addressed, changed files, commands, observed results, remaining decisions and rollback steps in the master progress journal. Confirm shared contract changes before integrating the work.\n`;
      files[`${path}/testing.md`] = `# ${data.label} acceptance tests\n\n${stamp}\n\n${section('tests')}\n\nRecord the test environment, command, input, expected result and observed evidence. Execution status: pending.\n`;
      const cases=data.buildSpec?.verificationCases||[];
      if(cases.length){
        files[`${path}/verification-cases.json`]=JSON.stringify({format:'atmem.verification-cases',version:1,blockId:id,execution:'not_run',cases},null,2)+'\n';
        files[`${path}/testing.md`]+='\n'+cases.map(verificationCaseMarkdown).join('\n\n')+'\n';
      }
      const scenarios = (data.buildSpec?.scenarios || []).map((scenario, index) => {
        const diagrams = scenarioDiagrams(scenario);
        for (const [view, diagram] of Object.entries(diagrams)) files[`${path}/${index + 1}-${view}.mmd`] = diagram + '\n';
        const bindings=scenario.steps.flatMap((step,i)=>step.operationId?[`${i+1}. ${step.operationId}`]:[]);
        return `## ${scenario.name}\n\n${bindings.length?'### Model operation bindings\n\n'+bindings.join('\n')+'\n\n':''}### Functional flow\n\n\`\`\`mermaid\n${diagrams.functional}\n\`\`\`\n\n### Sequence\n\n\`\`\`mermaid\n${diagrams.sequence}\n\`\`\`\n\n### Event flow\n\n\`\`\`mermaid\n${diagrams.events}\n\`\`\``;
      });
      files[`${path}/scenarios.md`] = `# ${data.label} scenarios\n\n${stamp}\n\n${scenarios.join('\n\n') || 'Open engineering work. Specify the main and exception paths.'}\n`;
      visit(id, depth + 1);
    }
  }
  visit(null, 0);
  files['spec-kit/blocks/index.json'] = JSON.stringify({ version: 1, designRevision: project.revision, components }, null, 2);
  files['spec-kit/blocks/README.md'] = `# Component Spec Kits\n\n${stamp}\n\n${components.map(row => `${'  '.repeat(row.depth)}- [${row.label}](block-${slug(row.id)}/spec.md)${row.missing.length ? ` · ${row.missing.length} open sections` : ''}`).join('\n')}\n`;
  return files;
}
