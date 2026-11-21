import fs from 'node:fs';
const names=['bounded_rag','rag_aws_adapter','rag_acceptance','catalog_admin','connector_sync','connector_cli','web_user_admin'];
const sources=Object.fromEntries(names.map(name=>[`${name}.py`,fs.readFileSync(new URL(`../src/runtime/${name}.py`,import.meta.url),'utf8')]));
sources['connector_acceptance.py']=fs.readFileSync(new URL('../server/tests/test_connector_contract.py',import.meta.url),'utf8').replace("parents[2]/'src/runtime'","parents[1]/'connectors'");
fs.writeFileSync(new URL('../src/runtime/rag-sources.json',import.meta.url),JSON.stringify(sources,null,2)+'\n');

fs.writeFileSync(new URL('../src/runtime/structured-source.json',import.meta.url),JSON.stringify(fs.readFileSync(new URL('../src/runtime/structured_output.py',import.meta.url),'utf8'))+'\n');

fs.writeFileSync(new URL('../src/runtime/structured-web-source.json',import.meta.url),JSON.stringify(fs.readFileSync(new URL('../src/runtime/structured-web-app.js',import.meta.url),'utf8'))+'\n');

fs.writeFileSync(new URL('../src/runtime/azure-sources.json',import.meta.url),JSON.stringify(Object.fromEntries(['azure_structured.py','azure_acceptance.py','structured_output.py','structured_http.py','http_acceptance.py','export_contract_acceptance.py'].map(name=>[name,fs.readFileSync(new URL('../src/runtime/'+name,import.meta.url),'utf8')])),null,2)+'\n');

fs.writeFileSync(new URL('../src/runtime/gcp-sources.json',import.meta.url),JSON.stringify(Object.fromEntries(['gcp_structured.py','gcp_acceptance.py','structured_output.py','structured_http.py','policy_review.py','http_acceptance.py','export_contract_acceptance.py'].map(name=>[name,fs.readFileSync(new URL('../src/runtime/'+name,import.meta.url),'utf8')])),null,2)+'\n');
fs.writeFileSync(new URL('../src/runtime/iap-web-source.json',import.meta.url),JSON.stringify(fs.readFileSync(new URL('../src/runtime/iap-web-app.js',import.meta.url),'utf8'))+'\n');

fs.writeFileSync(new URL('../src/runtime/ibm-sources.json',import.meta.url),JSON.stringify(Object.fromEntries(['ibm_structured.py','ibm_acceptance.py','structured_output.py','structured_http.py','http_acceptance.py','export_contract_acceptance.py','policy_review.py'].map(name=>[name,fs.readFileSync(new URL('../src/runtime/'+name,import.meta.url),'utf8')])),null,2)+'\n');

const faqNames=['public_faq.py','public_catalog_store.py','public_catalog_admin.py','public_faq_app.py','lambda_faq.py','aws_json_model.py','azure_structured.py','gcp_structured.py','ibm_structured.py','policy_review.py','structured_http.py','structured_output.py'];
const faqSources=Object.fromEntries(faqNames.map(name=>[name,fs.readFileSync(new URL('../src/runtime/'+name,import.meta.url),'utf8')]));
for(const [destination,source] of Object.entries({'web/index.html':'faq-web.html','web/app.css':'faq-web.css','web/app.js':'faq-web-app.js'}))faqSources[destination]=fs.readFileSync(new URL('../src/runtime/'+source,import.meta.url),'utf8');
for(const kind of ['core','http','catalog_admin','catalog_store']){
 const source=fs.readFileSync(new URL('../server/tests/test_public_'+(kind==='core'?'faq_core':kind==='http'?'faq_http':kind)+'.py',import.meta.url),'utf8');
 faqSources['faq_'+kind+'_acceptance.py']=source.replace("str(Path(__file__).resolve().parents[2]/'src/runtime')","str(Path(__file__).resolve().parent)");
}
faqSources['faq_lambda_acceptance.py']=fs.readFileSync(new URL('../server/tests/test_public_faq_lambda.py',import.meta.url),'utf8').replace("str(Path(__file__).resolve().parents[2]/'src/runtime')","str(Path(__file__).resolve().parent)");
fs.writeFileSync(new URL('../src/runtime/public-faq-sources.json',import.meta.url),JSON.stringify(faqSources,null,2)+'\n');

const invoiceNames=['durable_workflow.py','workflow_connection.py','workflow_contract.py','workflow_database.py','workflow_errors.py','workflow_process_stage.py','workflow_role_bootstrap.py','workflow_worker.py','workflow_schema.sql','invoice_document.py','invoice_extraction.py','invoice_object_store.py','invoice_http.py','invoice_identity.py','invoice_native.py','invoice_runtime_secrets.py','invoice_processing.py','invoice_parser_service.py','invoice_parser_transport.py','invoice_parser_cli.py','invoice_stage.py','invoice_worker.py','invoice_web.py','approved_http_destination.py','structured_output.py','structured_http.py','policy_review.py','aws_json_model.py','azure_structured.py','gcp_structured.py','ibm_structured.py','invoice-web.html','invoice-web.css','invoice-web.js','invoice-parser.Dockerfile','invoice-parser-lock.json'];
invoiceNames.push('invoice_parser_identity.py','invoice-parser-python-lock.json','parser-requirements.lock','rds-global-ca.pem','rds-ca-source.json','invoice_retention.py','invoice_operations.py','invoice_operator.py','invoice_operator_core.py','invoice_configuration.py','invoice_maintenance.py','invoice_operator_job.py');
fs.writeFileSync(new URL('../src/runtime/invoice-sources.json',import.meta.url),JSON.stringify(Object.fromEntries(invoiceNames.map(name=>[name,fs.readFileSync(new URL('../src/runtime/'+name,import.meta.url),'utf8')])),null,2)+'\n');
const invoiceTests=['invoice_extraction_acceptance.py','invoice_storage_acceptance.py','invoice_http_acceptance.py','invoice_web_acceptance.py','invoice_identity_acceptance.py','invoice_parser_rpc_acceptance.py','invoice_parser_identity_acceptance.py','invoice_worker_acceptance.py','invoice_operations_acceptance.py','invoice_operator_acceptance.py','invoice_operator_job_acceptance.py','durable_postgres_acceptance.py','durable_privileges_acceptance.py','durable_fixture_tasks.py','workflow_tls_destination_fixture.py'];
const invoiceTestSources=Object.fromEntries(invoiceTests.map(name=>[name,fs.readFileSync(new URL('../tests/runtime/'+name,import.meta.url),'utf8')]));
invoiceTestSources['start-durable-fixture.py']=fs.readFileSync(new URL('./start-durable-fixture.py',import.meta.url),'utf8');
invoiceTestSources['postgres-qualification-lock.json']=fs.readFileSync(new URL('../src/runtime/postgres-qualification-lock.json',import.meta.url),'utf8');
invoiceTestSources['invoice-text.pdf.base64']=fs.readFileSync(new URL('../benchmarks/convergence/fixtures/invoices/invoice-text.pdf',import.meta.url)).toString('base64');
fs.writeFileSync(new URL('../src/runtime/invoice-test-sources.json',import.meta.url),JSON.stringify(invoiceTestSources,null,2)+'\n');
