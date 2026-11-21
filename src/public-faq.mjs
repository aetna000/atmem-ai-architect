import outputSchema from './runtime/faq-output-contract.json' with {type:'json'};
import sources from './runtime/public-faq-sources.json' with {type:'json'};
import awsLock from './runtime/aws-web-python-lock.json' with {type:'json'};
import azureLock from './runtime/azure-python-lock.json' with {type:'json'};
import webLock from './runtime/web-python-lock.json' with {type:'json'};
import ibmLock from './runtime/ibm-python-lock.json' with {type:'json'};
import testLock from './runtime/azure-test-lock.json' with {type:'json'};
import base from './runtime/python-container-lock.json' with {type:'json'};
import {pythonContainer} from './python-container.mjs';
import {existingDeployment} from './deployment-ownership.mjs';

export const PUBLIC_FAQ_SERVICES={aws:'AWS Lambda',azure:'Azure App Service',gcp:'Google Cloud Run',ibm:'IBM Code Engine'};
const locks={aws:awsLock,azure:azureLock,gcp:webLock,ibm:ibmLock};
const adapters={aws:['aws_json_model.py','lambda_faq.py'],azure:['azure_structured.py'],gcp:['gcp_structured.py','policy_review.py'],ibm:['ibm_structured.py','policy_review.py']};

export function publicFaqPlan(project,rows){
 const entries=[];
 for(const node of project.nodes){
  const d=node.data,row=rows.find(r=>r.id===node.id);
  if(!row||d.implementation!=='public-faq-app'||d.service!==PUBLIC_FAQ_SERVICES[d.provider]||existingDeployment(node)||d.origin==='existing')continue;
  if(d.config?.outputContract)throw Error('Public FAQ uses its built-in cited-answer contract; preserve custom operation requirements as separate implementation work.');
  for(const [key,value]of Object.entries({maxInputBytes:2000,maxArticleBytes:30000,maxArticles:100}))if(d.config?.[key]!==undefined&&d.config[key]!==value)throw Error('The public FAQ recipe declares '+key+' = '+value+'; a different explicit limit requires generator implementation, not silent substitution.');
  entries.push({row,provider:d.provider});
 }
 const ids=new Set(entries.map(e=>e.row.id)),browsers=new Set(project.nodes.filter(n=>existingDeployment(n)&&n.data.provider==='tools'&&n.data.binding==='web-browser').map(n=>n.id));
 const editors=new Set(project.nodes.filter(n=>existingDeployment(n)&&n.data.provider==='tools'&&n.data.binding==='public-catalog-editor').map(n=>n.id));
 const editorEdges=project.edges.filter(e=>e.integration==='public-catalog-edit'&&editors.has(e.source)&&ids.has(e.target));
 return {entries,componentIds:[...ids],editorIds:[...new Set(editorEdges.map(e=>e.source))],edgeIds:[...project.edges.filter(e=>e.integration==='browser-https'&&browsers.has(e.source)&&ids.has(e.target)),...editorEdges].map(e=>e.id)};
}

// This emits source, not a coverage claim. Public registration requires each
// provider's complete hosting/storage/identity composition and qualification.
export function publicFaqFiles(provider,address){
 if(!adapters[provider]||!/^block_[0-9a-f]+$/.test(address))throw Error('Invalid owned public FAQ application address/provider');
 const folder='applications/'+address+'/',files={},modules=['public_faq.py','public_catalog_store.py','public_faq_app.py','structured_http.py','structured_output.py',...adapters[provider]];
 for(const name of [...modules,'public_catalog_admin.py'])files[folder+name]=sources[name];
 for(const name of ['web/index.html','web/app.css','web/app.js'])files[folder+name]=sources[name];
 for(const kind of ['core','http','catalog_admin','catalog_store']){
  const name='faq_'+kind+'_acceptance.py';let code=sources[name];
  if(kind==='catalog_store'&&provider!=='aws'){
   const start=code.indexOf('class S3CatalogContractTests('),end=code.indexOf('class ConditionalConcurrencyTests(');
   if(start<0||end<=start)throw Error('Provider-specific test boundary changed; review it before emission');
   code=code.slice(0,start)+code.slice(end);
   code=code.replace(/^import boto3\n/m,'').replace(/^from botocore\.[^\n]+\n/gm,'');
  }
  files[folder+name]=code;
 }
 if(provider==='aws')files[folder+'faq_lambda_acceptance.py']=sources['faq_lambda_acceptance.py'];
 files[folder+'faq_acceptance.py']='"""Local public-only lifecycle/HTTP/transport checks; not cloud IAM or model quality."""\nfrom faq_core_acceptance import PublicFaqCoreTests\nfrom faq_http_acceptance import PublicFaqHttpTests\nfrom faq_catalog_admin_acceptance import CatalogAdminTests\nfrom faq_catalog_store_acceptance import HttpCatalogContractTests,ConditionalConcurrencyTests'+(provider==='aws'?',S3CatalogContractTests':'')+(provider==='aws'?'\nfrom faq_lambda_acceptance import PublicFaqLambdaTests':'')+'\nimport unittest\nif __name__=="__main__":unittest.main()\n';
 const lock=locks[provider];files[folder+'requirements.lock']=lock.requirements;files[folder+'dependency-sources.json']=JSON.stringify(lock.sources,null,2);
 files[folder+'test-requirements.lock']=testLock.requirements;files[folder+'test-dependency-sources.json']=JSON.stringify(testLock.sources,null,2);
 files[folder+'container-base.json']=JSON.stringify(base,null,2);
 files[folder+'output-contract.json']=JSON.stringify(outputSchema,null,2);
 files[folder+'faq-deployment.json']=JSON.stringify({format:'public-faq-v1',provider},null,2);
 files[folder+'Dockerfile']=pythonContainer('public_faq_app',modules,['faq-deployment.json']);
 files[folder+'.dockerignore']='*\n!requirements.lock\n!output-contract.json\n!faq-deployment.json\n'+modules.map(n=>'!'+n+'\n').join('')+'!web/\n!web/*\n';
 files[folder+'BUILD.md']=provider==='aws'?PUBLIC_FAQ_BUILD.replace(/Build this directory as Linux\/amd64[\s\S]*?host applies identical filesystem isolation[.]\n/, 'For AWS deployment, run python3 build-runtime.py from the Terraform root. This builds a deterministic Python 3.13 Linux x86_64 Lambda ZIP with hash-locked wheels, source, owned metadata and browser assets. Retain build/artifact-hashes.json. Test the actual ZIP in the reviewed Lambda Linux runtime and scan its dependencies. The Dockerfile is an optional portable local web-runtime check; it is not the Lambda deployment artifact. No registry publication or image input is required. Obtain explicit cloud authorization before any account plan or deployment.\n'):PUBLIC_FAQ_BUILD;
 return files;
}

export const PUBLIC_FAQ_BUILD=`# Generated public FAQ application

Use an isolated Python 3.13 environment. Install test-requirements.lock with
--only-binary=:all: --require-hashes, then run faq_acceptance.py -v. The source
tests use synthetic public articles and explicit transport fixtures. They do not
establish real IAM, model quality, service availability or deployment behavior.

Build this directory as Linux/amd64 with its emitted Dockerfile, run startup and
acceptance checks on the exact image, scan it and retain source/image digests.
Obtain authorization before authenticating to a registry or publishing an image.
Supply the reviewed immutable release inputs required by this provider's Terraform.
The runtime runs nonroot; use a read-only filesystem and writable temporary space
where the destination supports it. Local read-only checks do not prove the cloud
host applies identical filesystem isolation.

The anonymous API can only read the dedicated public catalog and invoke the
reviewed regional model. It has no HTTP editing endpoint. Never grant the runtime
catalog write, private-source, account-admin or model-policy-write permissions.
Review inherited destination IAM in addition to the emitted grants. An explicit
public marker does not automatically classify or approve document content: the
authorized editor is responsible for selecting genuinely public help articles.

Authorize the separate editor using the emitted native role and a short-lived
credential. Keep credentials and article files outside this source bundle. Use
public_catalog_admin.py --help, then inspect, init, upsert or delete as appropriate.
Initial creation requires --expected-version create. Later edits require the exact
observed version and --confirm-write. The native conditional write must succeed;
conflicts require reloading and reviewing the change. Never retry a write blindly
after an unconfirmed response. Editor flags express intent; the cloud IAM role
remains the authorization boundary. Do not pass a browser user token as an editor
credential. Token files must be operator-owned and private.

Seed the catalog explicitly before allowing traffic. Initialization reads every
file in a dedicated public .txt/.md directory, supports spaces/Unicode names and
creates stable distinct source IDs. It rejects symlinks, invalid UTF-8, oversized
files or unsupported entries rather than silently omitting articles. Later updates
and deletions change the current manifest; any retained backup versions require a
separately reviewed operator recovery path. The API never falls back to cached or
inaccessible source data. A changed source during inference withholds that answer.

The bounded lexical retriever admits up to 100 articles of 30000 UTF-8 bytes each;
the acceptance project starts with twenty. It supplies at most two full relevant
articles, without cutting sentences. Citation IDs and quotes are independently
verified against that exact evidence. URLs/titles come from the approved catalog,
not the model. Syntax and quote membership do not prove factual entailment: run a
representative real-model answer/citation/abstention evaluation before deployment.

The provider schema remains stable across queries to avoid a new grammar for every
source combination. The bounded synchronous AWS adapter uses independently decoded
JSON, not a claimed provider-constrained grammar: Bedrock's new-schema compilation
can take around 90 seconds and cannot silently fit a 29-second HTTP path. Other
adapters use their documented output modes with the same independent decoder.
Unsupported model/output responses fail closed; no model or region is silently
substituted. The browser does not retry model calls automatically.

Verify current regional model support, data handling, identity/control-plane
processing, quotas and prices with retained evidence. Limits on input, output,
concurrency and instance count are not an invoice cap, availability or latency SLA.
No question/answer persistence or content-bearing application logs are implemented;
review provider/platform logging and retention separately. Private enterprise
connectors, user tenancy, payments and durable workflows are different capabilities.
`;
