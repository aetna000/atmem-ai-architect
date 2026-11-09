// Preserve authoritative records across the bounded API context contract.
export function consultationContext(records){
 const result=[];
 for(const [index,record]of records.entries()){
  const points=Array.from(String(record.text??''));
  if(points.length<=1000){result.push({...record,text:points.join('')});continue;}
  const total=Math.ceil(points.length/850);
  for(let part=0;part<total;part++){
   const text=points.slice(part*850,(part+1)*850).join('');
   result.push(part===0?{...record,text}:{type:'discovery',id:`context-continuation-${index}-${part+1}`,text:`Continuation of ${record.type} ${record.id}, part ${part+1}/${total}: ${text}`});
  }
 }
 if(result.length>300)throw Error('The consultation exceeds 300 context records. Narrow the active consultation or split the project before sending; no records were truncated.');
 return result;
}
