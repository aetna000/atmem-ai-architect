import sources from './runtime/invoice-sources.json' with {type:'json'};
import {approvalProfiles} from './approval-applications.mjs';
import {resourceAddress} from './identifiers.mjs';
import {invoiceDependencies as workflowDependencies} from './invoice-dependencies.mjs';
import {pythonContainer} from './python-container.mjs';
const modules=['workflow_profile.py','workflow_application.py','workflow_configuration.py','workflow_identity.py','workflow_http.py','workflow_payload.py','workflow_contract.py','workflow_connection.py','workflow_errors.py','workflow_database.py','workflow_role_bootstrap.py','workflow_worker.py','durable_workflow.py','approved_http_destination.py','azure_structured.py','gcp_structured.py','ibm_structured.py','structured_output.py','structured_http.py','policy_review.py'];
export function approvalApplicationFiles(project,environment){
 const files={},records=[];
 for(const {node,profile}of approvalProfiles(project)){
  const root='applications/'+resourceAddress(node.id)+'/';
  for(const name of modules){if(typeof sources[name]!=='string')throw Error('Shared application runtime inventory is incomplete: '+name);files[root+name]=sources[name];}
  files[root+'workflow_schema.sql']=sources['workflow_schema.sql'];
  files[root+'application-profile.json']=JSON.stringify(profile,null,2)+'\n';
  files[root+'api.py']='"""Owned native API entrypoint; importing does not connect to a cloud/database."""\nimport os\nfrom pathlib import Path\nfrom workflow_application import load_profile,create_native_api\n\ndef app_factory(*,connection=None,jwks=None):\n    return create_native_api(load_profile(Path(__file__).with_name("application-profile.json")),os.environ,connection=connection,jwks=jwks)\n';
  const runtime=workflowDependencies(profile.provider),testing=workflowDependencies(profile.provider,{tests:true});
  files[root+'requirements.lock']=runtime.requirements;files[root+'test-requirements.lock']=testing.requirements;
  files[root+'dependency-sources.json']=JSON.stringify({sources:runtime.sources,resolutions:runtime.resolutions},null,2)+'\n';
  files[root+'Dockerfile']=pythonContainer('api',[...modules,'api.py'],['application-profile.json'],{web:false,contract:false,assets:['workflow_schema.sql'],concurrency:32});
  files[root+'.dockerignore']='*\n!requirements.lock\n!application-profile.json\n!workflow_schema.sql\n'+[...modules,'api.py'].map(name=>'!'+name+'\n').join('');
  const pending=['Provider API/worker/database/identity resource and environment linkage','Domain processor and reviewed destination mapping with real application acceptance','Explicit SQL initialization, role/membership admission, recovery/retention and operating acceptance'];
  if(profile.environment!==environment)pending.push('Profile environment '+profile.environment+' differs from export environment '+environment+'; retain and reconcile this choice');
  const record={componentId:node.id,provider:profile.provider,profileEnvironment:profile.environment,exportEnvironment:environment,path:root,apiEntrypoint:'api:app_factory',workerEntrypoint:null,sourceStatus:'shared-api-assembly-generated',infrastructureStatus:'not_implemented',applicationStatus:'not_verified',pending,cloudOperations:false};
  records.push(record);files[root+'assembly-status.json']=JSON.stringify(record,null,2)+'\n';
  files[root+'BUILD.md']='# Typed approval application source\n\nRead application-profile.json and assembly-status.json. The shared API entrypoint and exact locked runtime are emitted from this component contract. Build the API image with the included Dockerfile; do not publish/deploy without authorization.\n\nThis does not implement the domain processor or generate provider resources. Preserve all requirements and existing systems. Write the domain stage from the full brief, then use create_native_worker(profile, environment, processor, deliver) in a concrete worker entrypoint. It must retain fixed profile/role/kind/realm/destination bindings; no metadata-driven imports, no dummy processor or unconditional acceptance. Run positive/negative local end-to-end checks before recording implementation.\n\nInitialize SQL only through the reviewed operator role. Enroll approved native users using membership_key(profile, complete_verified_subject); token role claims do not grant membership. Keep API and worker credentials separate and outside source. Verify provider transport/IAM/network, image/source identity, retention/recovery and target environment independently. Schema/compilation or an importable API is not application acceptance. No work gate is cleared by these files.\n';
 }
 if(records.length)files['approval-applications.json']=JSON.stringify({version:1,applications:records,boundary:'Component-selected shared source and explicit pending work; no whole application, infrastructure, account or deployment acceptance'},null,2)+'\n';
 return files;
}
