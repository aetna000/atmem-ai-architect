// Product-owned build only. Website imports the reviewed output as static data.
import {build} from 'vite';
import {mkdir,writeFile,readdir,readFile} from 'node:fs/promises';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
process.env.VITE_ARCHITECT_HOSTED='1';
// The application downloads PDFs directly. Disable jsPDF's unused remote PDFObject loader.
const remotePreview='https://cdnjs.cloudflare.com/ajax/libs/pdfobject/2.1.1/pdfobject.min.js';
let previewPatched=false;
await build({plugins:[{name:'first-party-pdf-preview',transform(code,id){if(id.includes('jspdf')&&code.includes(remotePreview)){previewPatched=true;return code.replaceAll(remotePreview,'/architect/workspace/pdfobject-preview.js');}}}],base:'/architect/workspace/',build:{outDir:'dist-hosted',emptyOutDir:true,target:'es2022'}});
if(!previewPatched)throw Error('Review the pinned PDF dependency before publishing its hosted bundle');
await writeFile('dist-hosted/pdfobject-preview.js',"document.body.textContent='Use the Download PDF action in Architect.';\n");
const files=[];async function inventory(dir,base=''){for(const entry of await readdir(dir,{withFileTypes:true})){const path=join(dir,entry.name),name=base+entry.name;if(entry.isDirectory())await inventory(path,name+'/');else files.push({path:name,sha256:createHash('sha256').update(await readFile(path)).digest('hex')});}}
await writeFile('dist-hosted/reference-project.json',await readFile('src/reference-example/project.json'));
await inventory('dist-hosted');
const inputs=execFileSync('git',['ls-files','-co','--exclude-standard','--','src','public','package.json','package-lock.json','index.html','vite.config.js','scripts/build-hosted-workspace.mjs'],{encoding:'utf8'}).trim().split('\n');
const source={revision:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),dirty:!!execFileSync('git',['status','--porcelain','--','src','public','package.json','package-lock.json','scripts/build-hosted-workspace.mjs'],{encoding:'utf8'}).trim(),files:[]};
for(const path of [...new Set(inputs)].sort())source.files.push({path,sha256:createHash('sha256').update(await readFile(path)).digest('hex')});
await writeFile('dist-hosted/manifest.json',JSON.stringify({kind:'AtMem AI Architect hosted browser workspace',source,files},null,2)+'\n');
