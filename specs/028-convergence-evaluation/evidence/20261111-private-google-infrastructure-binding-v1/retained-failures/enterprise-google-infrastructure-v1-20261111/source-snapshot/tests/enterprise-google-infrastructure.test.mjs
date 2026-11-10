import test from 'node:test';
import assert from 'node:assert/strict';
import {googleDocumentJobTerraform} from '../src/enterprise-google-infrastructure.mjs';

const project={id:'private-knowledge-qualification',revision:7};
const row={id:'knowledge',address:'block_6b6e6f776c65646765',provider:'gcp',region:'australia-southeast1'};
const compile=()=>googleDocumentJobTerraform(project,row,'qualification');

test('Google document substrate preserves design ownership and selected placement without mutating inputs',()=>{
 const before=JSON.stringify({project,row});
 for(const region of ['australia-southeast1','australia-southeast2','us-central1']){
  const selected={...row,region},files=googleDocumentJobTerraform(project,selected),tf=JSON.parse(files['main.tf.json']);
  assert.equal(tf.variable.region.default,region);assert.equal(JSON.parse(files['document-job-boundary.json']).region,region);
 }
 assert.equal(JSON.stringify({project,row}),before);
});

test('Google document compiler refuses cloud substitution and unresolved or injected location',()=>{
 for(const selected of [{...row,provider:'aws'},{...row,region:'Australia'},{...row,region:'${file("/private")}'},{...row,region:['australia-southeast1']},{...row,address:'${unowned}'}]){
  assert.throws(()=>googleDocumentJobTerraform(project,selected));
 }
 assert.throws(()=>googleDocumentJobTerraform({...project,revision:'7'},row));
});

test('Temporary document identities have only concrete controller and bucket permissions',()=>{
 const tf=JSON.parse(compile()['main.tf.json']),r=tf.resource,n=row.address;
 assert.deepEqual(r.google_project_iam_custom_role[n+'_control'].permissions,['batch.jobs.create','batch.jobs.get','batch.jobs.delete','batch.operations.get']);
 assert.deepEqual(r.google_project_iam_custom_role[n+'_transfer_objects'].permissions,['storage.objects.get','storage.objects.create']);
 assert.deepEqual(r.google_project_iam_custom_role[n+'_worker_objects'].permissions,['storage.objects.get','storage.objects.create','storage.objects.delete']);
 assert.equal(r.google_service_account_iam_member[n+'_worker_act_as'].service_account_id,'${google_service_account.'+n+'_vm.name}');
 assert.ok(Object.values(r.google_storage_bucket_iam_member).every(value=>value.bucket==='${google_storage_bucket.'+n+'.name}'));
 assert.ok(!JSON.stringify(r).includes('allUsers'));assert.ok(!JSON.stringify(r).includes('roles/editor'));
 assert.ok(!Object.keys(r).some(type=>/sql|secret_manager|cloud_run/.test(type)));
});

test('Parser substrate emits explicit private API paths and never a NAT or default internet route',()=>{
 const r=JSON.parse(compile()['main.tf.json']).resource,n=row.address;
 assert.equal(r.google_compute_subnetwork[n].private_ip_google_access,true);
 assert.equal(r.google_compute_network[n].delete_default_routes_on_create,true);
 assert.deepEqual(Object.values(r.google_compute_route).map(value=>value.dest_range),['199.36.153.8/30','34.126.0.0/18']);
 assert.ok(!Object.keys(r).some(type=>/router_nat|compute_instance/.test(type)));
 assert.deepEqual(r.google_compute_firewall[n+'_allow_api'].allow,[{protocol:'tcp',ports:['443']}]);
 assert.deepEqual(r.google_dns_record_set[n+'_registry_wildcard'].rrdatas,['private.googleapis.com.']);
 assert.equal(r.google_storage_bucket[n].versioning.enabled,false);assert.equal(r.google_storage_bucket[n].soft_delete_policy.retention_duration_seconds,0);
});

test('Runtime configuration covers the exact adapter fields after the complete substrate dependency graph',()=>{
 const tf=JSON.parse(compile()['main.tf.json']);
 assert.deepEqual(Object.keys(tf.locals.document_job_configuration).sort(),['format','projectId','region','bucket','parserImage','transferImage','workerServiceAccount','vmServiceAccount','network','subnetwork'].sort());
 assert.equal(tf.variable.images_ready.default,false);assert.equal(tf.output.document_job_configuration.value,'${var.images_ready ? local.document_job_configuration : null}');
 assert.equal(tf.output.document_job_configuration.depends_on.length,Object.values(tf.resource).reduce((sum,group)=>sum+Object.keys(group).length,0));
 const preconditions=tf.resource.terraform_data[row.address+'_review'].lifecycle.precondition;
 assert.ok(preconditions.every(item=>!item.condition.includes('google_service_account.')),'No review-gate cycle through owned resources');
});

test('Shipped mock plans and release boundary retain unfinished crash recovery and complete project scope',()=>{
 const files=compile(),boundary=JSON.parse(files['document-job-boundary.json']);
 assert.equal((files['tests/document-jobs.tftest.hcl'].match(/run "/g)||[]).length,11);
 assert.equal(boundary.productionQualified,false);assert.match(boundary.crashRecovery,/Unfinished/);
 assert.match(files['README.md'],/not a complete project/);assert.match(files['README.md'],/asynchronous/);
 assert.equal(JSON.parse(files['deployment.tfvars.json.example']).parser_image,'');
});
