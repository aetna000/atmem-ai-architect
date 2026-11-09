// Concrete links are derived from emitted files, not fabricated repository paths.
export function implementationMap(project,plan,files){
 const config=JSON.parse(files['main.tf.json']);
 const components=plan.rows.map(row=>{
  const addresses=Object.entries(config.resource||{}).flatMap(([type,items])=>Object.keys(items).filter(name=>name===row.address||name.startsWith(row.address+'_')).map(name=>type+'.'+name));
  const generatedFiles=Object.entries(files).filter(([name,body])=>name!=='resource-schedule.json'&&(name.includes(row.address)||body.includes(row.address))).map(([name])=>'terraform/'+name);
  const variables=Object.keys(config.variable||{}).filter(name=>name.startsWith(row.address+'_'));
  return {id:row.id,ownership:row.existing?'existing':row.sourceExisting?'existing_source_new_deployment':'proposed',terraformAddresses:addresses,generatedFiles,requiredInputs:variables,requirements:(project.needs||[]).filter(r=>r.links?.includes(row.id)).map(r=>r.id),applicationImplementation:row.containerContract?'supplied_image_required':row.existing?'external_behavior_unverified':generatedFiles.some(p=>p.includes('/handlers/'))?'generated_runtime_unverified':'not_established'};
 });
 const interfaces=project.edges.map(edge=>({id:edge.id,source:edge.source,target:edge.target,purpose:edge.label||'',integration:edge.integration||null,access:edge.access||null,generated:!!plan.connections.find(e=>e.id===edge.id)?.generated,requiredContractFields:['request/event schema','response/result schema','identity and authorization','timeout','retry and idempotency','error and recovery','observability','acceptance fixtures'],status:'runtime_contract_evidence_required'}));
 return {version:1,designRevision:project.revision,components,interfaces,commands:['terraform init -backend=false','terraform validate','terraform test'],evidenceBoundary:'File and resource links are generated artifact facts; runtime behavior and destination account validation require separate evidence.'};
}
