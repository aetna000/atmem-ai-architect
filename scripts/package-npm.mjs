// Build a minimal allowlisted npm distribution. Never package local projects or credentials.
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
const root=process.cwd(),output=path.resolve(process.env.ATMEM_NPM_OUTPUT||'.local/npm-release'),stage=path.join(output,'package');
if(stage===root||root.startsWith(stage+path.sep))throw Error('Refusing to replace the source repository.');
const meta=JSON.parse(fs.readFileSync('package.json','utf8'));
if(!fs.existsSync('dist/index.html'))throw Error('Build the frontend before packaging.');
fs.mkdirSync(output,{recursive:true});fs.rmSync(stage,{recursive:true,force:true});fs.mkdirSync(stage);
function copy(name){
 const source=path.join(root,name),target=path.join(stage,name);
 fs.mkdirSync(path.dirname(target),{recursive:true});
 fs.cpSync(source,target,{recursive:true,filter:file=>{
  const rel=path.relative(source,file),parts=rel.split(path.sep),base=path.basename(file);
  if(parts.some(p=>['tests','__pycache__','.git','.local','node_modules','.venv','.memory-venv'].includes(p))||base.startsWith('.env')||base.endsWith('.pyc'))return false;
  if(fs.lstatSync(file).isSymbolicLink())throw Error('Refusing symlink in npm distribution: '+file);
  return true;
 }});
}
for(const name of ['LICENSE','NOTICE','CONSTITUTION.md','dist','src','server','agent-skills','knowledge','cli','packaging/uv-release-lock.json','scripts/terraform-render.mjs','docs/upstream-lock.json','public/licenses'])copy(name);
const knowledge=JSON.parse(fs.readFileSync('knowledge/engineering-practices.json','utf8'));
for(const record of knowledge.records){if(record.localVerification){const name=record.localVerification.receipt;if(!name.startsWith('specs/')||name.includes('..'))throw Error('Invalid evidence path.');copy(name);}}
fs.copyFileSync('packaging/README.npm.md',path.join(stage,'README.md'));
const packageJson={name:'@atmem/architect',version:meta.version,description:'AtMem AI Architect: design, requirements, review and verified project handoff',type:'module',bin:{'atmem-architect':'cli/architect.mjs'},engines:{node:'>=22.0.0'},license:'Apache-2.0',repository:{type:'git',url:'git+https://github.com/aetna000/atmem-ai-architect.git'},publishConfig:{access:'public',tag:'preview'},dependencies:meta.dependencies};
fs.writeFileSync(path.join(stage,'package.json'),JSON.stringify(packageJson,null,2)+'\n');fs.chmodSync(path.join(stage,'cli/architect.mjs'),0o755);
const result=spawnSync(process.platform==='win32'?'npm.cmd':'npm',['pack','--json','--ignore-scripts','--pack-destination',output],{cwd:stage,encoding:'utf8',shell:process.platform==='win32'});
if(result.status!==0)throw Error(result.stderr||'npm pack failed');
const packed=JSON.parse(result.stdout)[0];
const publicCa='src/runtime/rds-global-ca.pem';
const certificate=fs.readFileSync(path.join(stage,publicCa),'utf8');if(!certificate.includes('BEGIN CERTIFICATE')||certificate.includes('PRIVATE KEY'))throw Error('Expected the public RDS CA certificate bundle.');
const forbidden=packed.files.filter(file=>file.path!==publicCa&&/(?:^|\/)(?:\.env[^/]*|\.git|\.local|node_modules|\.venv|\.memory-venv|__pycache__)(?:\/|$)|\.(?:sqlite|db|pem|key|pyc)$/.test(file.path));
if(forbidden.length)throw Error('Private/local files in package: '+forbidden.map(f=>f.path).join(', '));
fs.writeFileSync(path.join(output,'pack-receipt.json'),JSON.stringify(packed,null,2)+'\n');console.log(JSON.stringify({name:packageJson.name,version:meta.version,tarball:path.join(output,packed.filename),bytes:packed.size,unpackedBytes:packed.unpackedSize,files:packed.files.length}));
