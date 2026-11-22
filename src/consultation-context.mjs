// Preserve every authoritative record; chunk individual text fields for the API contract.
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
 return result;
}
