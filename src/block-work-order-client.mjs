const uuid=/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;
export const blockOrderKey=projectId=>'atmem-block-order-v1:'+projectId;
export function validatePendingBlockOrder(value,projectId){
 if(!value||value.version!==1||value.projectId!==projectId||typeof value.sessionId!=='string'||!uuid.test(value.sessionId)||!uuid.test(value.requestId)||typeof value.blockId!=='string'||!value.blockId.length||value.blockId.length>100||!(/^[a-f0-9]{64}$/).test(value.contextSha256)||Object.keys(value).some(key=>!['version','projectId','sessionId','requestId','blockId','contextSha256'].includes(key)))throw Error('The retained block request is invalid. Keep its record for inspection.');
 return value;
}
export function pendingBlockOrder(projectId,sessionId,blockId,contextSha256,requestId=crypto.randomUUID()){
 return validatePendingBlockOrder({version:1,projectId,sessionId,requestId,blockId,contextSha256},projectId);
}
export function loadBlockOrder(storage,projectId){
 try{const raw=storage.getItem(blockOrderKey(projectId));return {pending:raw?validatePendingBlockOrder(JSON.parse(raw),projectId):null,error:''};}
 catch{return {pending:null,error:'The retained block request could not be read. Its saved record was preserved.'};}
}
export function saveBlockOrder(storage,projectId,value){
 if(value)storage.setItem(blockOrderKey(projectId),JSON.stringify(validatePendingBlockOrder(value,projectId)));
 else storage.removeItem(blockOrderKey(projectId));
}
export function blockOrderPayload(order){
 const {projectId,sessionId,requestId,blockId,contextSha256}=validatePendingBlockOrder(order,order.projectId);
 return {projectId,sessionId,requestId,blockId,contextSha256};
}
export function verifyBlockOrderAcceptance(order,result){
 if(result.acceptedRunId!==order.requestId||result.workOrder?.kind!=='build_block'||result.workOrder.blockId!==order.blockId||result.workOrder.contextSha256!==order.contextSha256)throw Error('The block request acknowledgement did not match. Recover this saved request before starting another.');
 return result;
}
