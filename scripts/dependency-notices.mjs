import fs from 'node:fs';
import path from 'node:path';
const lock=JSON.parse(fs.readFileSync('package-lock.json','utf8'));
const report=[];const inventory=[];
for(const [location,entry] of Object.entries(lock.packages)){
 if(!location)continue;
 const pkg=path.join(location,'package.json');if(!fs.existsSync(pkg))continue;
 const metadata=JSON.parse(fs.readFileSync(pkg,'utf8'));
 const files=fs.readdirSync(location).filter(f=>/^(license|licence|copying|notice|ofl)(\.|-|$)/i.test(f));
 inventory.push({name:metadata.name,version:metadata.version,license:metadata.license||'UNKNOWN',dev:!!entry.dev,licenseFiles:files});
 report.push(`\n${'='.repeat(72)}\n${metadata.name}@${metadata.version}\nDeclared licence: ${JSON.stringify(metadata.license||'UNKNOWN')}\n${metadata.homepage||''}\n`);
 for(const file of files){const target=path.join(location,file);if(fs.statSync(target).isFile())report.push(`\n--- ${file} ---\n${fs.readFileSync(target,'utf8')}\n`);}
}
fs.writeFileSync('public/licenses/dependency-notices.txt',report.join('\n').replace(/\r\n?/g,'\n').replace(/[ \t]+$/gm,''));
fs.writeFileSync('docs/dependency-inventory.json',JSON.stringify(inventory,null,2)+'\n');
console.log(JSON.stringify({installedPackages:inventory.length,unknown:inventory.filter(x=>x.license==='UNKNOWN'),withoutRootLicenseFiles:inventory.filter(x=>!x.licenseFiles.length).map(x=>x.name)}));
