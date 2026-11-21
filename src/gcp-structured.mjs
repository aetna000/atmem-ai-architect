import {pythonContainer} from './python-container.mjs';
import sources from './runtime/gcp-sources.json' with {type:'json'};
import lock from './runtime/web-python-lock.json' with {type:'json'};
import testLock from './runtime/azure-test-lock.json' with {type:'json'};
import base from './runtime/python-container-lock.json' with {type:'json'};
import webSource from './runtime/iap-web-source.json' with {type:'json'};
import {STRUCTURED_WEB_HTML,STRUCTURED_WEB_CSS} from './structured-web.mjs';
import {structuredContract} from './structured-contract.mjs';
import {existingDeployment} from './deployment-ownership.mjs';
import {existingReferenceFiles} from './existing-references.mjs';
import {CLOUD_PROVIDER_LOCKS} from './cloud-provider-locks.mjs';

export function gcpStructuredPlan(project,rows){
 const entries=[];
 for(const node of project.nodes){
  if(node.data.provider!=='gcp'||node.data.implementation!=='gcp-structured-app'||node.data.service!=='Google Cloud Run'||existingDeployment(node))continue;
  const contract=structuredContract(node.data.config?.outputContract);if(!contract)continue;
  const maxInput=node.data.config?.maxInputBytes??20000,maxTokens=node.data.config?.maxOutputTokens??1024;
  if(!Number.isInteger(maxInput)||maxInput<1||maxInput>20000||!Number.isInteger(maxTokens)||maxTokens<32||maxTokens>4096)throw Error('Google structured application limits must be 1–20000 input bytes and 32–4096 output tokens.');
  entries.push({row:rows.find(r=>r.id===node.id),contract,maxInput,maxTokens});
 }
 const ids=new Set(entries.map(e=>e.row.id)),browsers=new Set(project.nodes.filter(n=>existingDeployment(n)&&n.data.provider==='tools'&&n.data.binding==='web-browser').map(n=>n.id));
 return {entries,componentIds:[...ids],edgeIds:project.edges.filter(e=>e.integration==='browser-https'&&browsers.has(e.source)&&ids.has(e.target)).map(e=>e.id)};
}
const v=n=>'${var.'+n+'}',ref=(type,n,key)=>'${'+type+'.'+n+'.'+key+'}';
export function gcpStructuredTerraform(project,plan,environment='staging'){
 const entries=plan.gcpStructuredPlan.entries;if(!entries.length)throw Error('No Google structured application composition.');
 const variable={review_approved:{type:'bool',default:false}},examples={review_approved:false},resource={},output={},files={},tests=[];
 const input=(name,description,example,pattern)=>{variable[name]={type:'string',nullable:false,description,validation:{condition:'${can(regex('+JSON.stringify(pattern)+', var.'+name+'))}',error_message:'Supply the reviewed '+name+' value.'}};examples[name]=example;return v(name);};
 const destination=input('project_id','Existing reviewed organization-owned Google Cloud project with billing. No project is recreated.','reviewed-project','^[a-z][a-z0-9-]{4,28}[a-z0-9]$');
 const registryLocation=input('registry_location','Location of the existing Artifact Registry Docker repository.','australia-southeast1','^[a-z]+(?:-[a-z]+[0-9])?$');
 const registry=input('registry_repository','Existing Docker repository in the selected project; no registry is recreated.','reviewed-images','^[a-z][a-z0-9-]{1,61}[a-z0-9]$');
 const gaps=[...plan.gapDetails.map(g=>g.id),...(environment==='production'?['production-state-backup-and-operating-review-required']:[])];
 resource.terraform_data={review_gate:{input:{design_revision:project.revision,environment},lifecycle:{precondition:[{condition:'${var.review_approved && length(local.unfinished_work) == 0}',error_message:'Review the destination, code, access, policy, costs and unresolved scope before planning deployment.'}]}}};
 const add=(type,name,body)=>((resource[type]||={})[name]={...body,depends_on:['terraform_data.review_gate',...(body.depends_on||[])]});
 for(const [name,service]of Object.entries({run:'run.googleapis.com',iap:'iap.googleapis.com',model:'aiplatform.googleapis.com',registry:'artifactregistry.googleapis.com'}))add('google_project_service','required_'+name,{project:destination,service,disable_on_destroy:false});
 for(const name of ['run','iap'])add('google_project_service_identity','required_'+name,{provider:'google-beta',project:destination,service:name+'.googleapis.com',depends_on:['google_project_service.required_'+name]});
 add('google_artifact_registry_repository_iam_member','image_pull',{project:destination,location:registryLocation,repository:registry,role:'roles/artifactregistry.reader',member:ref('google_project_service_identity','required_run','member'),depends_on:['google_project_service.required_registry']});
 const number='${data.google_project.destination.number}';
 for(const {row,contract,maxInput,maxTokens}of entries){
  const n=row.address;
  const name=input(n+'_name','Cloud Run service and dedicated runtime service-account name, kept short for the deterministic URL.','reviewed-ai-app','^[a-z][a-z0-9-]{4,28}[a-z0-9]$');
  const region=input(n+'_region','Explicit regional application/model location. No global model fallback. Verify selected model support and quota.','australia-southeast1','^[a-z]+-[a-z]+[0-9]$');
  if(/^[a-z]+-[a-z]+[0-9]$/.test(row.region)){variable[n+'_region'].default=row.region;examples[n+'_region']=row.region;}
  const imageRepository=input(n+'_image_repository','Repository path for building/publishing this emitted application source.','architect/app','^[a-z0-9]+(?:[._/-][a-z0-9]+)*$');
  const digest=input(n+'_image_digest','Digest from the built, scanned and tested emitted source, pushed with authorization to the existing registry.','sha256:'+'0'.repeat(64),'^sha256:[0-9a-f]{64}$');
  const model=input(n+'_model_id','Reviewed compatible regional Gemini model/version; check lifecycle and quotas. No model availability or price is invented.','gemini-reviewed-version','^gemini-[a-z0-9.-]{1,80}$');
  const group=input(n+'_access_group','Existing authorized company Google group email. IAP manages membership authorization; no group/users are created.','architect-staff@example.test','^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$');
  const reviewName=n+'_policy_review';
  variable[reviewName]={type:'object({ projectId = string, region = string, model = string, abuseLogging = string, approvedBy = string, evidenceSha256 = string, expiresAt = string })',nullable:false,description:'Destination owner review of actual abuse-monitoring terms/exemption, with retained evidence digest and expiry within 31 days. This is operator-attested evidence, not a fabricated provider approval API. The runtime separately reads caching/logging controls before inference.'};
  examples[reviewName]={projectId:'reviewed-project',region:examples[n+'_region'],model:'gemini-reviewed-version',abuseLogging:'REVIEW_REQUIRED',approvedBy:'REVIEW_REQUIRED',evidenceSha256:'0'.repeat(64),expiresAt:'REPLACE_AFTER_REVIEW'};
  const origin='https://'+name+'-'+number+'.'+region+'.run.app';
  add('google_service_account',n,{project:destination,account_id:name,display_name:'Structured AI application runtime'});
  add('google_project_iam_custom_role',n,{project:destination,role_id:'${replace(var.'+n+'_name, "-", "_")}_runtime',title:'Structured application model and policy reader',permissions:['aiplatform.endpoints.predict','aiplatform.cacheConfigs.get','aiplatform.endpoints.fetchPublisherModelConfig'],stage:'GA'});
  add('google_project_iam_member',n,{project:destination,role:ref('google_project_iam_custom_role',n,'name'),member:'serviceAccount:'+ref('google_service_account',n,'email'),depends_on:['google_project_service.required_model']});
  const settings={PROJECT_ID:destination,PROJECT_NUMBER:number,REGION:region,SERVICE_NAME:name,MODEL_ID:model,PUBLIC_ORIGIN:origin,MAX_INPUT_BYTES:String(maxInput),MAX_OUTPUT_TOKENS:String(maxTokens),OUTPUT_CONTRACT_BASE64:btoa(unescape(encodeURIComponent(JSON.stringify(contract)))),POLICY_REVIEW_BASE64:'${base64encode(jsonencode(var.'+reviewName+'))}'};
  const image=registryLocation+'-docker.pkg.dev/'+destination+'/'+registry+'/'+imageRepository+'@'+digest;
  add('google_cloud_run_v2_service',n,{project:destination,name,location:region,deletion_protection:true,ingress:'INGRESS_TRAFFIC_ALL',iap_enabled:true,invoker_iam_disabled:false,labels:{managed_by:'atmem-ai-architect',environment},template:{service_account:ref('google_service_account',n,'email'),timeout:'30s',max_instance_request_concurrency:5,scaling:{min_instance_count:0,max_instance_count:2},containers:{name:'application',image,ports:{container_port:8080},resources:{limits:{cpu:'1',memory:'512Mi'},cpu_idle:true,startup_cpu_boost:true},env:Object.entries(settings).map(([name,value])=>({name,value})),startup_probe:{http_get:{path:'/healthz',port:8080},initial_delay_seconds:0,period_seconds:5,timeout_seconds:2,failure_threshold:12}}},depends_on:['google_project_service.required_run','google_project_service_identity.required_iap','google_project_service_identity.required_run','google_artifact_registry_repository_iam_member.image_pull','google_project_iam_member.'+n]});
  add('google_cloud_run_v2_service_iam_member',n,{project:destination,location:region,name:ref('google_cloud_run_v2_service',n,'name'),role:'roles/run.invoker',member:ref('google_project_service_identity','required_iap','member')});
  add('google_iap_web_cloud_run_service_iam_member',n,{project:destination,location:region,cloud_run_service_name:ref('google_cloud_run_v2_service',n,'name'),role:'roles/iap.httpsResourceAccessor',member:'group:'+group});
  output[n+'_url']={value:origin};
  const folder='applications/'+n+'/';
  for(const [path,body]of Object.entries(sources))files[folder+path]=body;
  files[folder+'web/index.html']=STRUCTURED_WEB_HTML.replace('<button id="sign-in">Sign in</button><button id="sign-out" hidden>Sign out</button>','<button id="clear" type="button">Clear input and result</button>');
  files[folder+'web/app.css']=STRUCTURED_WEB_CSS;files[folder+'web/app.js']=webSource;
  files[folder+'output-contract.json']=JSON.stringify(contract,null,2);
  files[folder+'requirements.lock']=lock.requirements;files[folder+'dependency-sources.json']=JSON.stringify(lock.sources,null,2);
  files[folder+'test-requirements.lock']=testLock.requirements;files[folder+'test-dependency-sources.json']=JSON.stringify(testLock.sources,null,2);
  files[folder+'container-base.json']=JSON.stringify(base,null,2);
  files[folder+'Dockerfile']=pythonContainer('gcp_structured',['gcp_structured.py','structured_output.py','structured_http.py','policy_review.py']);
  files[folder+'.dockerignore']='*\n!requirements.lock\n!output-contract.json\n!gcp_structured.py\n!structured_output.py\n!structured_http.py\n!policy_review.py\n!web/\n!web/*\n';
  files[folder+'BUILD.md']=`# Generated Cloud Run application\n\nIn this directory, create an isolated Python 3.13 environment, install test-requirements.lock with --only-binary=:all: --require-hashes, then run gcp_acceptance.py -v. Tests use ephemeral signed JWTs and scripted transport fixtures. They do not contact Google Cloud.\n\nBuild this source with docker build --platform linux/amd64 --pull -t REVIEWED_LOCATION-docker.pkg.dev/REVIEWED_PROJECT/REVIEWED_REPOSITORY/REVIEWED_IMAGE:REVIEWED_BUILD . ; scan, run container startup/acceptance checks and retain source/image digests. Obtain authorization before authenticating to the existing Artifact Registry and pushing. Supply that exact registry digest as ${n}_image_digest. Terraform does not run build/publish provisioners.\n\nProvide the reviewed project/model/region and destination-owner policy evidence using ${reviewName}; the supplied example is intentionally unapproved. Runtime verifies its scope/expiry, reads disabled project caching and model logging/sharing settings, and blocks before inference if any check is unknown. The owner review covers abuse-monitoring terms/exemption that this application cannot discover through a reliable API. It is an attestation, not independent proof of approval. The application never modifies those project/account-wide controls.\n`;
  tests.push(`run "${n}_identity" {\n command = plan\n assert {\n condition = google_cloud_run_v2_service.${n}.iap_enabled && !google_cloud_run_v2_service.${n}.invoker_iam_disabled\n error_message = "IAP and Cloud Run IAM must remain enabled."\n }\n assert {\n condition = google_cloud_run_v2_service_iam_member.${n}.member == google_project_service_identity.required_iap.member && google_iap_web_cloud_run_service_iam_member.${n}.member == "group:\${var.${n}_access_group}"\n error_message = "Only the IAP agent invokes the service; only the reviewed group receives IAP access."\n }\n assert {\n condition = length(google_project_iam_custom_role.${n}.permissions) == 3 && !contains(google_project_iam_custom_role.${n}.permissions, "aiplatform.endpoints.setPublisherModelConfig")\n error_message = "Runtime must not modify project/account-wide model policy."\n }\n}\nrun "${n}_reject_mutable_image" {\n command = plan\n variables { ${n}_image_digest = "latest" }\n expect_failures = [var.${n}_image_digest]\n}`);
 }
 const config={terraform:{required_version:'>= 1.17.1, < 2.0.0',required_providers:{google:{source:'hashicorp/google',version:'7.46.2'},'google-beta':{source:'hashicorp/google-beta',version:'7.46.2'}}},provider:{google:{project:destination},'google-beta':{project:destination}},data:{google_project:{destination:{project_id:destination}}},variable,locals:{unfinished_work:gaps},resource,output};
 const values=Object.entries({...examples,review_approved:true}).map(([k,value])=>k+' = '+JSON.stringify(value)).join('\n');
 return {...files,...existingReferenceFiles(project),'.terraform.lock.hcl':CLOUD_PROVIDER_LOCKS.gcp+'\n'+CLOUD_PROVIDER_LOCKS.gcpBeta,'main.tf.json':JSON.stringify(config,null,2),'resource-schedule.json':JSON.stringify(plan,null,2),'deployment.tfvars.json.example':JSON.stringify(examples,null,2),'.gitignore':'.terraform/\n*.tfstate*\n*.tfplan\n*.tfvars\n*.tfvars.json\n!deployment.tfvars.json.example\n.venv/\n__pycache__/\n','tests/gcp-structured.tftest.hcl':`mock_provider "google" {\n override_during = plan\n mock_data "google_project" { defaults = { number = "123456789012" } }\n mock_resource "google_service_account" { defaults = { email = "runtime@reviewed-project.iam.gserviceaccount.com" } }\n}\nmock_provider "google-beta" {\n override_during = plan\n mock_resource "google_project_service_identity" { defaults = { email = "service-123456789012@gcp-sa-iap.iam.gserviceaccount.com", member = "serviceAccount:service-123456789012@gcp-sa-iap.iam.gserviceaccount.com" } }\n}\nvariables {\n${values}\n}\n${tests.join('\n')}\nrun "unapproved_blocked" {\n command = plan\n variables { review_approved = false }\n expect_failures = [terraform_data.review_gate]\n}\n`,'README.md':GCP_STRUCTURED_GUIDE};
}

export const GCP_STRUCTURED_GUIDE=`# Google Cloud structured AI application

An explicit gcp-structured-app block composes a Cloud Run browser/API, dedicated keyless runtime service account, narrow project-level model/policy-read role, IAP service identity and company-group access. The Google beta provider is used only for generating Google-managed IAP/Cloud Run service identities; these identities cannot be destroyed through that resource. Existing projects, groups and Artifact Registry repositories are preserved. Required APIs are enabled but never disabled on destroy. Unrelated services/connections remain gaps.

IAP is enabled directly on Cloud Run with IAM checks retained. Only its service agent receives the emitted run.invoker grant. The existing company group receives IAP access; no allUsers/allAuthenticatedUsers grant is emitted. Use an organization-owned project with the Google-managed OAuth client; first-time nonorganization/external-identity OAuth flows require a separately reviewed configuration. Reconcile inherited IAM permissions and organizational policies in the real account.

The app verifies every non-health request using the signed ES256 IAP JWT, fixed Google key endpoint, exact service audience, issuer, lifetime and user identity. Unsigned identity headers, a caller Authorization header and service-account identities grant no application access. API requests additionally require the exact same-origin browser Origin. The deterministic run.app URL is used deliberately; the service name stays short enough for its DNS limit. Do not use the alternate hashed URL for this browser without updating the reviewed origin contract. IAP membership/organization session policy is the authorization boundary. This is not a continuous directory check or proof of MFA/revocation behavior; issued IAP headers remain valid until expiry/skew. The browser clears input/result without claiming to sign out of the company session.

Workload tokens come only from Cloud Run's fixed metadata endpoint with Metadata-Flavor verification, no inherited proxy/netrc configuration, redirects or static key file. A custom role admits prediction and read-only cache/model-policy queries in the selected project. It is project-scoped, not an invented per-publisher-model IAM restriction. The application selects only the reviewed regional Gemini model. Only the Cloud Run platform agent receives reader access on the exact existing image repository.

No application input/result is persisted. Before inference, a scoped, expiring destination-owner review must cover actual abuse-monitoring terms/exemption, with retained evidence digest. This is operator-attested evidence, not a provider approval API. Runtime separately reads disabled project caching and disabled model request/response logging and sharing. Unknown/denied controls stop inference. A documented model-policy 404 NOT_FOUND indicates default disabled configuration; other failures do not. The global project caching read uses Google's documented us-central1 control endpoint, sends no ticket input and never changes settings. Review that metadata location, IAP/global identity processing, actual model geography/availability and provider terms against residency requirements. The app does not claim universal zero retention. No tools, grounding, cachedContent or stateful interactions API is used.

Build/scan/test emitted applications/* source and the pinned Linux/amd64 image, then obtain authorization to publish to the existing Artifact Registry. Supply the exact image digest and reviewed destination/model/group/policy inputs. The example policy is intentionally unapproved. Protect Terraform state and private variable files. Terraform never builds, publishes, executes a provisioner or authorizes its own policy changes.

Use Terraform 1.17.1 or newer (the locally qualified CLI; tests use plan-time mock values). Run terraform init -backend=false, terraform validate and terraform test. Mock plans inspect configuration, not Google account behavior. Run real IAP sign-in/group/expiry tests, metadata identity exchange, policy/model-quality tests, image startup/scan, authorized account plan and operational review before deployment. Scaling/concurrency and token bounds are not invoice caps or availability/latency SLAs. Production remains blocked pending state, backup and operations review. No export proves deployment.

References:
- https://docs.cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run
- https://docs.cloud.google.com/iap/docs/signed-headers-howto
- https://docs.cloud.google.com/run/docs/securing/service-identity
- https://docs.cloud.google.com/run/docs/triggering/https-request
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/zero-data-retention
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/request-response-logging
- https://registry.terraform.io/providers/hashicorp/google/7.46.2/docs/resources/cloud_run_v2_service
`;
