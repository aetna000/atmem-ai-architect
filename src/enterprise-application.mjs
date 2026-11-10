import sources from'./runtime/enterprise-application-sources.json'with{type:'json'};

// A source package is not a supported complete-project capability. Native hosting,
// account inputs, model/source/SQL configuration and whole-export gates must bind it.
export function enterpriseApplicationFiles(provider,address){
 if(!['aws','azure','gcp','ibm'].includes(provider)||typeof address!=='string'||!/^block_[0-9a-f]+$/.test(address))throw Error('Use the explicit private application provider and canonical address');
 const root='applications/'+address+'/',files={},manifest=sources.manifest;
 const names=[...manifest.files,...manifest.providerFiles[provider]];
 for(const name of names){if(typeof sources.files[name]!=='string')throw Error('Missing private application asset '+name);files[root+'runtime/'+name]=sources.files[name];}
 const lockName='enterprise-runtime-'+provider+'-python-lock.json',lock=JSON.parse(sources.files[lockName]);
 if(lock.provider!==provider||typeof lock.requirements!=='string'||!lock.requirements.includes('--hash=sha256:'))throw Error('Use the exact selected-provider dependency closure');
 files[root+'requirements.lock']=lock.requirements;files[root+'dependency-lock.json']=sources.files[lockName];
 files[root+'Dockerfile']=sources.files['enterprise-runtime.Dockerfile'];
 files[root+'container-base.json']=sources.files['python-container-lock.json'];
 files[root+'application-manifest.json']=JSON.stringify({format:manifest.format,provider,files:names,entrypoints:manifest.entrypoints,
  sourceHashes:Object.fromEntries([...names,'enterprise-runtime.Dockerfile',lockName,'python-container-lock.json'].map(name=>[name,sources.hashes[name]])),
  documentWorkerImplemented:manifest.nativeDocumentWorkerProviders.includes(provider),wholeProjectQualified:false},null,2)+'\n';
 files[root+'.dockerignore']='*\n!Dockerfile\n!requirements.lock\n!runtime/\n'+names.map(name=>'!runtime/'+name+'\n').join('');
 files[root+'configuration-contract.json']=JSON.stringify({format:'enterprise-process-configuration-v1',provider,
  deployment:{direct:'ENTERPRISE_DEPLOYMENT_JSON',mountedFile:'ENTERPRISE_DEPLOYMENT_FILE',defaultFile:'/app/enterprise-deployment.json',schema:'enterprise-knowledge-v1',maximumBytes:32768},
  documentExecutor:{direct:'ENTERPRISE_DOCUMENT_EXECUTOR_JSON',mountedFile:'ENTERPRISE_DOCUMENT_EXECUTOR_FILE',defaultFile:'/app/enterprise-document-executor.json',schema:'enterprise-document-executor-v1',maximumBytes:32768,provider,parserRevision:'Must equal the approved deployment/build receipt; not an invented digest.',nativeConfiguration:'Use the corresponding Terraform document_executor_configuration output.'},
  suppliedSecrets:'Native platform injection or owned mounted files only; no secret values belong in this source package.',wholeProjectQualified:false},null,2)+'\n';
 files[root+'BUILD.md']=BUILD;
 for(const [directory,names,recipe]of [['parser/',manifest.parserFiles,'enterprise-document.Dockerfile'],['parser/pdf/',manifest.pdfParserFiles,'invoice-parser.Dockerfile']]){
  for(const name of names)files[root+directory+(name===recipe?'Dockerfile':name)]=sources.files[name];
  files[root+directory+'.dockerignore']='*\n'+names.filter(name=>name!==recipe).map(name=>'!'+name+'\n').join('');
  files[root+directory+'source-manifest.json']=JSON.stringify({sourceHashes:Object.fromEntries(names.map(name=>[name,sources.hashes[name]])),scope:'Exact parser build sources; not a native isolation or security acceptance receipt.'},null,2)+'\n';
 }
 return files;
}

const BUILD=`# Private application delivery

Build this exact directory as Linux/amd64 with the emitted Dockerfile and hash lock.
The API is the default command. The manifest also records the dedicated worker and
operator commands. Keep parser/OCR tools in their separate reviewed artifact: no
document parser, Java runtime or Docker daemon runs in this credentialed worker.

Build the supplied parser recipes separately, in this order, and record their
actual inspected source/image identities before using them in native configuration:

docker build --platform linux/amd64 -t atmem-private-pdf-base:local parser/pdf
docker build --platform linux/amd64 --build-arg PDF_PARSER_IMAGE=atmem-private-pdf-base:local -t atmem-private-document:local parser
docker build --platform linux/amd64 -t atmem-private-application:local .

Local tags are build handles, not immutable publication evidence. Keep the exact
image IDs/build receipts and obtain authorization before any registry publication.

Supply the approved deployment as ENTERPRISE_DEPLOYMENT_JSON or an absolute
ENTERPRISE_DEPLOYMENT_FILE mount. Supply exactly one form, never conflicting sources.
The API reads only its deployment metadata; it does not construct a parser or model.
For an implemented native worker, supply ENTERPRISE_DOCUMENT_EXECUTOR_JSON or its
absolute FILE mount from the same Terraform output and parser build receipt. The
worker checks provider, parser revision, native destination and worker identity before
reading source/encryption secrets or SQL. No arbitrary plug-in, executable or URL
can be selected through this configuration. Default worker concurrency is two;
ENTERPRISE_WORKER_CONCURRENCY accepts one to four after capacity/quotas are reviewed.

AWS and Google native document loading are implemented locally. Azure/IBM loading
remains an implementation requirement; their application source/dependency emission
does not advertise a complete worker or substitute another cloud. No complete
private capability is promoted by these files.

The configured worker attaches the durable cleanup ledger and runs recovery alongside
question processing. Runtime startup never initializes schemas, adopts existing SQL
state, creates company membership or generates replacement encryption keys. Use the
operator lifecycle with separate existing native SQL identities before enabling it.
Keep corporate OIDC/source registrations and approved directory mappings intact.

Preserve image/source digests, reviewed dependency/security evidence and actual
destination artifact publication records. Parser revision, local image configuration
digest and registry manifest digest are distinct identities; never invent or equate
them. Full application/worker/database/model/source networking, secrets, enrollment,
artifact publication, operations and Spec Kit composition remain mandatory before
whole-project acceptance. No account plan, publication or deployment ran here.
`;
