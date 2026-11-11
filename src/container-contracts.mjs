import ibmProviderLock from './runtime/invoice-ibm-provider-lock.json' with {type:'json'};
import {existingDeployment} from './deployment-ownership.mjs';
export const CONTAINER_SERVICES={aws:{service:'Amazon ECS Fargate',type:'aws_ecs_service',source:'hashicorp/aws',version:'~> 6.0',provider:'aws'},azure:{service:'Azure Container Apps',type:'azurerm_container_app',source:'hashicorp/azurerm',version:'4.81.0',provider:'azurerm'},gcp:{service:'Google Cloud Run',type:'google_cloud_run_v2_service',source:'hashicorp/google',version:'7.46.2',provider:'google'},ibm:{service:'IBM Code Engine',type:'ibm_code_engine_app',source:'IBM-Cloud/ibm',version:ibmProviderLock.version,provider:'ibm'}};
export function containerContract(node){const d=node.data,c=CONTAINER_SERVICES[d.provider];return !existingDeployment(node)&&d.implementation==='container-service'&&d.service===c?.service?c:null;}
export const hasContainers=p=>p.nodes.some(containerContract);
