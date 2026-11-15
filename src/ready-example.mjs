import file from './reference-example/project.json' with {type:'json'};
import {fromProjectFile} from './project-file.mjs';
export const READY_EXAMPLE_ID='atmem-ai-ready-example-v1';
export function readyExample(){const {project}=fromProjectFile(structuredClone(file));return project;}
export function isReadyExample(project){return project?.extensions?.preparedExample?.version===1&&project?.extensions?.preparedExample?.owner==='AtMem example author';}
