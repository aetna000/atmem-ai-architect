import verificationCases from './reference-example/verification-cases.json' with {type:'json'};
import file from './reference-example/project.json' with {type:'json'};
import {fromProjectFile} from './project-file.mjs';
export const READY_EXAMPLE_ID='atmem-ai-ready-example-v1';
export function readyExample(){const {project}=fromProjectFile(structuredClone(file));return {...project,name:'AI knowledge assistant — runnable example',revision:project.revision+1,nodes:project.nodes.map(n=>n.id==='rag-fn'?{...n,data:{...n.data,buildSpec:{...n.data.buildSpec,verificationCases:structuredClone(verificationCases)}}}:n)};}
export function isReadyExample(project){return project?.extensions?.preparedExample?.version===1&&project?.extensions?.preparedExample?.owner==='AtMem example author';}
