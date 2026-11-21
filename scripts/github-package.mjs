// Mirror the qualified payload into the repository owner's GitHub npm namespace.
import fs from'node:fs';import path from'node:path';import{spawnSync}from'node:child_process';import{createHash}from'node:crypto';
const [input,output]=process.argv.slice(2),owner=process.env.GITHUB_REPOSITORY_OWNER;
if(!input||!output||!owner||!/^[a-z0-9-]+$/i.test(owner))throw Error('Provide candidate directory, output directory and GitHub repository owner.');
const source=path.resolve(input),target=path.resolve(output),archives=fs.readdirSync(source).filter(name=>name.endsWith('.tgz'));
if(archives.length!==1||target===process.cwd()||process.cwd().startsWith(target+path.sep))throw Error('Expected one qualified package and an isolated output directory.');
fs.mkdirSync(target,{recursive:true});if(fs.existsSync(path.join(target,'package')))throw Error('Mirror directory already exists. Use a fresh directory.');
const result=spawnSync('tar',['-xzf',path.join(source,archives[0]),'-C',target],{encoding:'utf8'});if(result.status!==0)throw Error('Could not extract the qualified package.');
const folder=path.join(target,'package'),meta=JSON.parse(fs.readFileSync(path.join(folder,'package.json'),'utf8'));
if(meta.name!=='@atmem/architect'||meta.repository?.url!==`git+https://github.com/${process.env.GITHUB_REPOSITORY}.git`)throw Error('Candidate repository does not match this GitHub workflow.');
function inventory(root,prefix=''){return Object.fromEntries(fs.readdirSync(path.join(root,prefix),{withFileTypes:true}).flatMap(entry=>{const name=path.join(prefix,entry.name);if(entry.isSymbolicLink())throw Error('Symlinks are not permitted.');return entry.isDirectory()?Object.entries(inventory(root,name)):name==='package.json'?[]:[[name,createHash('sha256').update(fs.readFileSync(path.join(root,name))).digest('hex')]];}));}
const before=inventory(folder);meta.name=`@${owner.toLowerCase()}/architect`;meta.publishConfig={access:'public',tag:'latest',registry:'https://npm.pkg.github.com'};
fs.writeFileSync(path.join(folder,'package.json'),JSON.stringify(meta,null,2)+'\n');if(JSON.stringify(before)!==JSON.stringify(inventory(folder)))throw Error('The qualified payload changed.');
fs.writeFileSync(path.join(target,'mirror-receipt.json'),JSON.stringify({name:meta.name,version:meta.version,qualifiedPayloadUnchanged:true,files:Object.keys(before).length},null,2)+'\n');console.log(JSON.stringify({name:meta.name,version:meta.version,qualifiedPayloadUnchanged:true}));
