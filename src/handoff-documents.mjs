import {marked} from 'marked';
import {html,websiteShell} from './handoff-presentation.mjs';

// Resolve paths inside an archive, including references relative to authored
// Markdown. Never guess a figure by its basename or request a remote image.
function archivePath(document,href){
  let path;
  try{path=decodeURIComponent(href.split(/[?#]/)[0]);}catch{return null;}
  if(!path||/^(?:[a-z][a-z0-9+.-]*:|\/)|[\\\u0000-\u001f]/i.test(path))return null;
  const parts=document.split('/').slice(0,-1);
  for(const part of path.split('/')){
    if(part==='..'){if(!parts.length)return null;parts.pop();}
    else if(part&&part!=='.')parts.push(part);
  }
  return parts.join('/');
}
export function rasterType(bytes){
  if(!(bytes instanceof Uint8Array))return null;
  const starts=(...prefix)=>prefix.every((b,i)=>bytes[i]===b);
  if(starts(137,80,78,71,13,10,26,10))return '.png';
  if(starts(255,216,255))return '.jpg';
  if(starts(71,73,70,56))return '.gif';
  if(starts(82,73,70,70)&&String.fromCharCode(...bytes.slice(8,12))==='WEBP')return '.webp';
  return null;
}
function embeddedRaster(href){
  const match=/^data:image\/(?:png|jpe?g|gif|webp);base64,([a-z\d+/=\s]+)$/i.exec(href);
  if(!match)return;
  try{return Uint8Array.from(atob(match[1]),char=>char.charCodeAt(0));}catch{return;}
}
function imageAttributes(tag){
  const attrs={};
  for(const m of tag.matchAll(/\s(src|alt)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/gi))attrs[m[1].toLowerCase()]=m[2]??m[3]??m[4];
  return attrs;
}
// Decode source media before promising a usable illustration. SVG is opened in
// the browser's inert image context, then rasterized for portable offline viewing.
async function readableImage(bytes,path){
  const extension=rasterType(bytes),svg=/\.svg$/i.test(path||'');
  if((!extension&&!svg)||bytes==null)return {};
  if(typeof Image==='undefined')return extension?{extension,bytes}:{};
  if(svg&&!extension){
    const xml=typeof bytes==='string'?bytes:new TextDecoder().decode(bytes);
    const doc=new DOMParser().parseFromString(xml,'image/svg+xml');
    if(doc.documentElement.localName!=='svg'||doc.documentElement.namespaceURI!=='http://www.w3.org/2000/svg'||doc.querySelector('parsererror'))return {reason:'Invalid SVG image'};
    for(const el of doc.querySelectorAll('*')){
      for(const attr of el.attributes){
        if(el.localName!=='a'&&attr.localName==='href'&&attr.value&&!/^(?:#|data:image\/)/i.test(attr.value))return {reason:'SVG requires an external resource'};
      }
    }
    if(/@import\b|<\?xml-stylesheet\b/i.test(xml)||doc.doctype?.systemId||
      [...xml.matchAll(/\burl\(\s*['"]?([^)'"]+)/gi)].some(([,ref])=>!/^(?:#|data:image\/)/i.test(ref.trim())))return {reason:'SVG requires an external resource'};
  }
  const type=extension==='.jpg'?'image/jpeg':extension?'image/'+extension.slice(1):'image/svg+xml';
  const url=URL.createObjectURL(new Blob([bytes],{type})),image=new Image();
  try{
    image.src=url;await image.decode();
    if(!image.naturalWidth||!image.naturalHeight)return {reason:'Image has no visible dimensions'};
    if(extension)return {extension,bytes};
    const scale=Math.min(1,2400/Math.max(image.naturalWidth,image.naturalHeight));
    const canvas=document.createElement('canvas');
    canvas.width=Math.max(1,Math.round(image.naturalWidth*scale));canvas.height=Math.max(1,Math.round(image.naturalHeight*scale));
    canvas.getContext('2d').drawImage(image,0,0,canvas.width,canvas.height);
    const png=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));
    if(png)return {extension:'.png',bytes:new Uint8Array(await png.arrayBuffer())};
    return {reason:'Image preview unavailable'};
  }catch{return {reason:'Image could not be decoded'};}
  finally{URL.revokeObjectURL(url);}
}
export async function teamDocuments(project,raw,output,namedFile,knownImages){
  const authored=project.extensions?.architectureDocuments?.files||[];
  const guides=new Map(),images=new Map(),missing=[];let displayed=0;
  for(const doc of authored){
    if(!/\.(md|txt)$/i.test(doc.path))continue;
    const tokens=/\.md$/i.test(doc.path)?marked.lexer(doc.content):[{type:'code',text:doc.content}];
    const name=tokens.find(t=>t.type==='heading')?.text||doc.path.split('/').at(-1).replace(/\.[^.]+$/,'').replace(/[-_]/g,' ');
    guides.set(doc.path,{tokens,name,path:namedFile(output,'documents',name,'.html','')});
  }
  for(const [original,guide]of guides){
    const references=[];
    function imageTag(href,alt,linked=false){
      references.push({href,alt,linked});
      return '<template data-picture="'+(references.length-1)+'"></template>';
    }
    async function resolvePicture({href,alt,linked}){
      href=String(href||'');const label=alt||href.split('/').at(-1)||'Source illustration';
      const path=archivePath(original,href);
      const key=path||href,bytes=path&&Object.hasOwn(raw,path)?raw[path]:embeddedRaster(href);
      let file=knownImages.get(path);
      if(!file&&!images.has(key)){
        const media=await readableImage(bytes,path);
        const file=media.extension?namedFile(output,'source-images',label,media.extension,media.bytes):null;
        images.set(key,{file,reason:media.reason});
      }
      file||=images.get(key)?.file;
      if(file){
        displayed++;
        return linked?'<a class="inline-link" href="../'+html(file)+'">'+html(label)+'</a>':'<img class="source-image" loading="lazy" src="../'+html(file)+'" alt="'+html(label)+'">';
      }
      const reason=images.get(key)?.reason||(path&&bytes!=null?'Original format retained in engineering package':/^https?:\/\//i.test(href)?'External image requires an offline copy':'Referenced image unavailable');
      missing.push({name:label,document:guide.name,reason,reference:href.startsWith('data:')?'Inline image':href});
      return '<span class="note image-gap">'+html(reason)+' · '+html(label)+'</span>';
    }
    function render(t){
      const children=()=>t.tokens?.map(render).join('')??html(t.text??t.raw);
      switch(t.type){
        case 'space':case 'def':return '';
        case 'text':case 'escape':return children();
        case 'paragraph':return '<p>'+children()+'</p>';
        case 'heading':{const level=Math.min(6,t.depth+1);return '<h'+level+'>'+children()+'</h'+level+'>';}
        case 'strong':case 'em':case 'del':return '<'+t.type+'>'+children()+'</'+t.type+'>';
        case 'br':return '<br>';
        case 'hr':return '<hr>';
        case 'codespan':return '<code>'+html(t.text)+'</code>';
        case 'code':return '<pre><code>'+html(t.text)+'</code></pre>';
        case 'blockquote':return '<blockquote>'+children()+'</blockquote>';
        case 'list':{const type=t.ordered?'ol':'ul';return '<'+type+'>'+t.items.map(item=>'<li>'+item.tokens.map(render).join('')+'</li>').join('')+'</'+type+'>';}
        case 'table':{const row=(cells,tag)=>'<tr>'+cells.map(c=>'<'+tag+'>'+c.tokens.map(render).join('')+'</'+tag+'>').join('')+'</tr>';return '<div class="table-scroll"><table><thead>'+row(t.header,'th')+'</thead><tbody>'+t.rows.map(c=>row(c,'td')).join('')+'</tbody></table></div>';}
        case 'link':{
          const target=guides.get(archivePath(original,t.href));
          if(target)return '<a href="../'+html(target.path)+'">'+children()+'</a>';
          if(/^https?:\/\//i.test(t.href))return '<a rel="noreferrer" href="'+html(t.href)+'">'+children()+'</a>';
          if(/\.(?:png|jpe?g|gif|webp|svg)(?:[?#].*)?$/i.test(t.href))return imageTag(t.href,t.text,true);
          return children();
        }
        case 'image':return imageTag(t.href,t.text);
        case 'html':{
          const tags=[...t.raw.matchAll(/<img\b(?:"[^"]*"|'[^']*'|[^'">])*>/gi)];
          if(!tags.length)return html(t.raw);
          let start=0,result='';
          for(const m of tags){const attrs=imageAttributes(m[0]);result+=html(t.raw.slice(start,m.index))+imageTag(attrs.src,attrs.alt);start=m.index+m[0].length;}
          return result+html(t.raw.slice(start));
        }
        default:return children();
      }
    }
    const back='<a class="inline-link" href="../index.html#files">← Project files</a>';
    const head=guide.tokens.find(t=>t.type!=='space');
    const template=guide.tokens.filter(t=>t!==head||head.type!=='heading').map(render).join('');
    const replacements=[];
    for(const reference of references)replacements.push(await resolvePicture(reference));
    const content=template.replace(/<template data-picture="(\d+)"><\/template>/g,(_,index)=>replacements[index]);
    output[guide.path]=websiteShell({name:guide.name,title:'Source document',revision:project.revision,root:'..',sections:[
      {id:'document',label:'Document',glyph:'files',body:back+'<h1>'+html(guide.name)+'</h1>'+content+back}
    ]});
  }
  return {guides:[...guides.values()].map(({name,path})=>({name,path})),missing,displayed};
}
