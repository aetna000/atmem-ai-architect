export function capturedDiagramSources(documents){
  return (documents?.files||[]).flatMap(file=>file.path.endsWith('.mmd')?[{name:file.path,source:file.content}]:
    file.path.endsWith('.md')?[...file.content.matchAll(/^```mermaid[ \t]*\r?\n([\s\S]*?)^```[ \t]*$/gm)]
      .map((match,index)=>({name:file.path+'#mermaid-'+(index+1),source:match[1]})):[]);
}

let parser;
export async function validateCapturedDiagrams(documents){
  const diagrams=capturedDiagramSources(documents);
  if(!diagrams.length)return {diagrams:0,status:'no_authored_diagrams'};
  if(diagrams.length>1000)throw Error('Captured diagrams exceed the explicit validation count. The original package is retained.');
  parser??=import('mermaid').then(({default:mermaid})=>mermaid).catch(()=>{
    parser=null;
    const error=Error('Diagram validation is unavailable. Reload the view; the captured package is retained.');
    error.validationUnavailable=true;
    throw error;
  });
  const mermaid=await parser;
  for(const diagram of diagrams){
    try{await mermaid.parse(diagram.source);}
    catch(cause){
      const error=Error(`A captured diagram is invalid: ${diagram.name}. Repair its syntax while preserving scope.`);
      error.canvasDiagnostic=`Invalid Mermaid diagram ${diagram.name}: ${String(cause?.message||cause).slice(0,4000)}`;
      throw error;
    }
  }
  return {diagrams:diagrams.length,status:'syntax_checked',boundary:'Parser evidence only. Architectural correctness and rendering are separate checks.'};
}
