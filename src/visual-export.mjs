// Offline exports from the saved project snapshot, independent of viewport and active tab.
import { jsPDF } from 'jspdf';
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
const plain=value=>String(value??'').replace(/\*\*|`/g,'').replace(/\[([^\]]+)\]\([^)]+\)/g,'$1');
let fontPromise;
async function font(){
  fontPromise ||= fetch((import.meta.env?.BASE_URL||'/')+'fonts/NotoSans-Regular.ttf').then(async r=>{if(!r.ok)throw Error('PDF font could not be loaded. Please retry the download.');const bytes=new Uint8Array(await r.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(binary);}).catch(e=>{fontPromise=null;throw e;});
  return fontPromise;
}
function pdf(fontData,options={}){const doc=new jsPDF({compress:true,...options});doc.addFileToVFS('NotoSans.ttf',fontData);doc.addFont('NotoSans.ttf','NotoSans','normal');doc.setFont('NotoSans');return doc;}
export function specificationPdf(markdown,fontData,diagramImage=null){
  const doc=pdf(fontData),width=170;let y=24;
  function line(text,size=10,color='#263345'){
    doc.setFontSize(size);doc.setTextColor(color);
    const lines=doc.splitTextToSize(plain(text),width);
    const height=size*0.48;
    for(const part of lines){if(y+height>276){doc.addPage();y=24;}doc.text(part,20,y);y+=height;}
  }
  let headers=[],codeBlock=false;
  for(const raw of markdown.split('\n')){
    const text=raw.trim();
    if(text.startsWith('```')){
      codeBlock=!codeBlock;
      if(codeBlock&&diagramImage){
        const h=Math.min(105,170*diagramImage.height/diagramImage.width),w=h*diagramImage.width/diagramImage.height;
        if(y+h>270){doc.addPage();y=24;}
        doc.addImage(diagramImage.png,'PNG',20,y,w,h);y+=h+8;
      }
      continue;
    }
    if(codeBlock)continue;
    if(!text){y+=3;continue;}
    if(/^\|[- :|]+\|$/.test(text))continue;
    if(text.startsWith('|')){
      const cells=text.slice(1,-1).split(/(?<!\\)\|/).map(c=>c.trim().replace(/\\\|/g,'|'));
      if(!headers.length){headers=cells;continue;}
      cells.forEach((cell,i)=>{if(cell&&cell!=='—')line(`${headers[i]||'Detail'}: ${cell}`,9);});y+=4;continue;
    }
    headers=[];
    const heading=text.match(/^(#{1,6})\s+(.+)/);
    if(heading){if(y>250){doc.addPage();y=24;}y+=5;line(heading[2],heading[1].length===1?20:heading[1].length===2?14:11,'#173e65');y+=3;}
    else line(text.replace(/^[-*] /,'• ').replace(/^_([\s\S]+)_$/,'$1'));
  }
  const count=doc.getNumberOfPages();
  for(let i=1;i<=count;i++){doc.setPage(i);doc.setFontSize(8);doc.setTextColor('#627080');doc.text('AtMem AI Architect · Working specification',20,287);doc.text(`${i} / ${count}`,190,287,{align:'right'});}
  return new Uint8Array(doc.output('arraybuffer'));
}
function wrap(ctx,text,width){
  const lines=[];
  for(const paragraph of String(text??'').split('\n')){
    let line='';
    for(const char of paragraph){if(line&&ctx.measureText(line+char).width>width){lines.push(line);line='';}line+=char;}lines.push(line);
  }
  return lines;
}
export function diagramSvg(project){
  const ctx=document.createElement('canvas').getContext('2d');ctx.font='14px sans-serif';
  const byId=new Map(project.nodes.map(n=>[n.id,n]));
  function position(n,seen=new Set()){
    if(seen.has(n.id))return {x:0,y:0};seen.add(n.id);
    const parent=byId.get(n.parentId),offset=parent?position(parent,seen):{x:0,y:0};
    return {x:offset.x+(Number(n.position?.x)||0),y:offset.y+(Number(n.position?.y)||0)};
  }
  const nodes=project.nodes.map(n=>{const w=Math.max(240,n.measured?.width||n.width||0),lines=wrap(ctx,[...new Set([n.data.label,n.data.service,n.data.description,n.data.config?.region].filter(Boolean))].join('\n'),w-32);return {...n,...position(n),w,h:Math.max(n.measured?.height||n.height||0,lines.length*20+32),lines};});
  let minX=Math.min(0,...nodes.map(n=>n.x))-50,minY=Math.min(0,...nodes.map(n=>n.y))-90;
  let width=Math.max(640,...nodes.map(n=>n.x+n.w-minX+50)),height=Math.max(360,...nodes.map(n=>n.y+n.h-minY+50));
  ctx.font='18px sans-serif';const titleLines=wrap(ctx,`${project.name} · r${project.revision}`,width-60);
  const extraTitleHeight=(titleLines.length-1)*24;minY-=extraTitleHeight;height+=extraTitleHeight;
  const map=new Map(nodes.map(n=>[n.id,n]));
  const edges=project.edges.map(e=>{const a=map.get(e.source),b=map.get(e.target);if(!a||!b)return '';
    const forward=b.x>=a.x, x1=a.x+(forward?a.w:0),x2=b.x+(forward?0:b.w),y1=a.y+a.h/2,y2=b.y+b.h/2;
    const labelLines=wrap(ctx,e.label||'',200),x=(x1+x2)/2,y=Math.min(a.y,b.y)-24-labelLines.length*18;
    return `<path d="M${x1},${y1} C${(x1+x2)/2},${y1} ${(x1+x2)/2},${y2} ${x2},${y2}" fill="none" stroke="#63758b" stroke-width="2" marker-end="url(#arrow)"/>${e.label?`<rect x="${x-105}" y="${y-18}" width="210" height="${labelLines.length*18+8}" fill="white"/><text x="${x}" y="${y}" text-anchor="middle" font-size="12">${labelLines.map((l,i)=>`<tspan x="${x}" dy="${i?18:0}">${esc(l)}</tspan>`).join('')}</text>`:''}`;
  }).join('');
  const boxes=nodes.map(n=>`<g><rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="10" fill="${n.data.kind==='note'?'#fff5bd':'#edf4fb'}" stroke="#7290ad"/><text x="${n.x+16}" y="${n.y+26}" font-size="14">${n.lines.map((l,i)=>`<tspan x="${n.x+16}" dy="${i?20:0}">${esc(l)}</tspan>`).join('')}</text></g>`).join('');
  return {width,height,svg:`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="${minX} ${minY} ${width} ${height}"><rect x="${minX}" y="${minY}" width="${width}" height="${height}" fill="white"/><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#63758b"/></marker></defs><g font-family="sans-serif" fill="#1c3045"><text x="${minX+30}" y="${minY+35}" font-size="18">${titleLines.map((l,i)=>`<tspan x="${minX+30}" dy="${i?24:0}">${esc(l)}</tspan>`).join('')}</text>${edges}${boxes}${nodes.length?'':`<text x="0" y="80">No components drawn yet.</text>`}</g></svg>`};
}
export async function pngOf({svg,width,height}){
  const url=URL.createObjectURL(new Blob([svg],{type:'image/svg+xml'}));
  try{const img=new Image();img.src=url;await img.decode();const canvas=document.createElement('canvas');
    const scale=Math.min(2,8192/width,8192/height,Math.sqrt(24_000_000/(width*height)));
    canvas.width=Math.ceil(width*scale);canvas.height=Math.ceil(height*scale);canvas.getContext('2d').drawImage(img,0,0,canvas.width,canvas.height);
    const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));if(!blob)throw Error('Diagram PNG could not be generated.');return new Uint8Array(await blob.arrayBuffer());
  }finally{URL.revokeObjectURL(url);}
}
export async function visualFiles(project,markdown,implementationMarkdown,renderedBoard){
  const [{renderDiagramSvg},{boardGraph}]=await Promise.all([import('./drawio-render.mjs'),import('./drawio-model.mjs')]);
  const data=await font(),diagram=renderedBoard??await renderDiagramSvg(boardGraph(project.nodes,project.edges),{
    name:project.name,revision:project.revision,
  }),png=await pngOf(diagram);
  const doc=pdf(data,{orientation:diagram.width>=diagram.height?'landscape':'portrait',unit:'mm',format:'a3'});
  const width=doc.internal.pageSize.getWidth()-20,height=doc.internal.pageSize.getHeight()-20,scale=Math.min(width/diagram.width,height/diagram.height);
  doc.addImage(png,'PNG',10+(width-diagram.width*scale)/2,10,diagram.width*scale,diagram.height*scale);
  return {...(implementationMarkdown?{'spec-kit/implementation-spec.pdf':specificationPdf(implementationMarkdown,data)}:{}),'specification.pdf':specificationPdf(markdown,data,{png,width:diagram.width,height:diagram.height}),'diagram.svg':diagram.svg,'diagram.png':png,'diagram.pdf':new Uint8Array(doc.output('arraybuffer'))};
}
