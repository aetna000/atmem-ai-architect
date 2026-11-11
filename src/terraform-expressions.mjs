// Relocate variable traversals inside Terraform templates. Quoted literal text,
// escaped interpolation and object attributes are never treated as references.
export function relocateTerraformTemplate(source,names){
 if(typeof source!=='string')return source;
 let i=0;
 function template(endQuote=false){
  let out='';
  while(i<source.length){
   if(endQuote&&source[i]==='"'){out+=source[i++];return out;}
   if(endQuote&&source[i]==='\\'){out+=source.slice(i,i+2);i+=2;continue;}
   if(source.startsWith('$${',i)||source.startsWith('%%{',i)){out+=source.slice(i,i+3);i+=3;continue;}
   if(source.startsWith('${',i)||source.startsWith('%{',i)){out+=source.slice(i,i+2);i+=2;out+=expression();continue;}
   out+=source[i++];
  }
  if(endQuote)throw Error('Unterminated Terraform expression string.');
  return out;
 }
 function expression(){
  let out='',depth=0;
  while(i<source.length){
   const c=source[i];
   if(source.startsWith('<<',i))throw Error('Heredoc relocation requires a reviewed expression adapter.');
   if(c==='"'){out+=source[i++]+template(true);continue;}
   if(c==='{'){depth++;out+=source[i++];continue;}
   if(c==='}'){out+=source[i++];if(depth--===0)return out;continue;}
   if(/[A-Za-z_]/.test(c)){
    const start=i;while(i<source.length&&/[A-Za-z0-9_-]/.test(source[i]))i++;
    const word=source.slice(start,i);
    if(word==='var'&&!/[A-Za-z0-9_.-]/.test(source[start-1]||'')){
     const match=/^(\s*\.\s*)([A-Za-z_][A-Za-z0-9_-]*)/.exec(source.slice(i));
     if(match){if(!Object.hasOwn(names,match[2]))throw Error('Undeclared Terraform variable traversal: '+match[2]);out+='var'+match[1]+names[match[2]];i+=match[0].length;continue;}
    }
    out+=word;continue;
   }
   out+=source[i++];
  }
  throw Error('Unterminated Terraform template expression.');
 }
 return template();
}
export function relocateTerraformValues(value,names){
 if(typeof value==='string')return relocateTerraformTemplate(value,names);
 if(Array.isArray(value))return value.map(v=>relocateTerraformValues(v,names));
 if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([k,v])=>[k,relocateTerraformValues(v,names)]));
 return value;
}
