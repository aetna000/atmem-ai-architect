import sources from './runtime/invoice-sources.json' with{type:'json'};
import {invoiceDependencies}from'./invoice-dependencies.mjs';
import {pythonContainer}from'./python-container.mjs';
import base from'./runtime/python-container-lock.json'with{type:'json'};

// Application emission alone is not a supported/cloud-qualified project. Native
// provider compilers and independent whole-export checks must admit composition.
export function invoiceApplicationFiles(provider,address){
 if(!['aws','azure','gcp','ibm'].includes(provider)||!/^block_[0-9a-f]+$/.test(address))throw Error('Use the exact owned invoice provider and address');
 const root='applications/'+address+'/',files={},modules=Object.keys(sources).filter(name=>name.endsWith('.py')&&name!=='invoice_parser_service.py'&&name!=='invoice_parser_cli.py');
 const assets=['workflow_schema.sql','invoice-web.html','invoice-web.css','invoice-web.js',...(provider==='aws'?['rds-global-ca.pem']:[])];
 for(const name of [...modules,...assets])files[root+name]=sources[name];
 const runtime=invoiceDependencies(provider),testing=invoiceDependencies(provider,{tests:true});
 files[root+'requirements.lock']=runtime.requirements;files[root+'dependency-sources.json']=JSON.stringify({sources:runtime.sources,resolutions:runtime.resolutions},null,2)+'\n';
 files[root+'test-requirements.lock']=testing.requirements;files[root+'test-dependency-sources.json']=JSON.stringify({sources:testing.sources,resolutions:testing.resolutions},null,2)+'\n';
 files[root+'invoice-deployment.json']=JSON.stringify({format:'invoice-workflow-v1',provider},null,2)+'\n';
 files[root+'container-base.json']=JSON.stringify(base,null,2)+'\n';
 if(provider==='aws')files[root+'rds-ca-source.json']=sources['rds-ca-source.json'];
 files[root+'Dockerfile']=pythonContainer('invoice_native',modules,['invoice-deployment.json'],{web:false,contract:false,assets,concurrency:32});
 files[root+'.dockerignore']='*\n!requirements.lock\n!invoice-deployment.json\n'+[...modules,...assets].map(name=>'!'+name+'\n').join('');
 const parserRoot=root+'parser/';for(const name of ['invoice_document.py','invoice_extraction.py','structured_output.py','invoice_parser_cli.py','invoice_parser_service.py','invoice_parser_identity.py','parser-requirements.lock','invoice-parser-python-lock.json','invoice-parser-lock.json'])files[parserRoot+name]=sources[name];
 files[parserRoot+'Dockerfile']=sources['invoice-parser.Dockerfile'];
 files[parserRoot+'.dockerignore']='*\n!invoice_document.py\n!invoice_extraction.py\n!structured_output.py\n!invoice_parser_cli.py\n!invoice_parser_service.py\n!invoice_parser_identity.py\n!parser-requirements.lock\n';
 files[root+'BUILD.md']=INVOICE_BUILD;
 return files;
}

export const INVOICE_BUILD=`# Invoice application images

This directory contains API/worker source and a separate bounded PDF/OCR image.
Build both as Linux/amd64 and retain source/image digests and security reports.
Use only the emitted exact wheel/native-package hashes and pinned container bases.
The IBM lock deliberately uses dateutil 3.0.0 required by its SDK; the composed queue
must be qualified with this dependency set, rather than borrowing another provider's
test result. Installer tools are removed from the application delivery image.

The API command is the image default. The dedicated worker command is
python -I /app/invoice_worker.py. Parser hosting overrides its default CLI with
python -I /app/invoice_parser_service.py. Do not run a Docker daemon in the worker.
Keep the parser in a separate workload with no database, model, object-store or
outbound action authority. Its private TLS ingress/caller restrictions are required
native infrastructure, not an anonymous public HTTP service. Runtime identities,
network and destination acceptance require separate destination checks.

The API never receives a model credential or outbound action secret. The worker
splits extraction and delivery into bounded child processes without database
configuration in their environments. The 180-second extraction deadline includes
object retrieval, up to 110 seconds of parsing/OCR and model/commit overhead inside
a 600-second domain lease. Delivery is bounded to 45 seconds; unknown external
outcomes require a verified same-key/same-payload idempotency contract or operator
reconciliation. A failed new attempt cannot erase an older uncertain side effect.
Child deadlines are not an OS sandbox; untrusted PDF parsing stays separate.

Default worker concurrency is one, matched to one parser slot. Twenty uploads
are admitted into the durable queue; they do not become twenty simultaneous OCR
processes. Scale worker/parser capacity together only after throughput, model quotas
and backpressure are tested. Capacity settings are not a price cap or SLA.

Keep credentials outside this directory and source control. Mount native CA and
secret files and supply the generated deployment environment. SQL role/bootstrap,
membership, retention/restore and reviewed external accounting contract are required
operational steps. Building this application does not prove those resources exist
or declare the complete project ready. Obtain authorization before publication,
account plans or deployment. Local checks do not establish cloud IAM or availability.
`;
