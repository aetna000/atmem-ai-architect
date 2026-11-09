import fs from 'node:fs';
const names=['bounded_rag','rag_aws_adapter','rag_acceptance','catalog_admin','connector_sync','connector_cli','web_user_admin'];
const sources=Object.fromEntries(names.map(name=>[`${name}.py`,fs.readFileSync(new URL(`../src/runtime/${name}.py`,import.meta.url),'utf8')]));
sources['connector_acceptance.py']=fs.readFileSync(new URL('../server/tests/test_connector_contract.py',import.meta.url),'utf8').replace("parents[2]/'src/runtime'","parents[1]/'connectors'");
fs.writeFileSync(new URL('../src/runtime/rag-sources.json',import.meta.url),JSON.stringify(sources,null,2)+'\n');

fs.writeFileSync(new URL('../src/runtime/structured-source.json',import.meta.url),JSON.stringify(fs.readFileSync(new URL('../src/runtime/structured_output.py',import.meta.url),'utf8'))+'\n');

fs.writeFileSync(new URL('../src/runtime/structured-web-source.json',import.meta.url),JSON.stringify(fs.readFileSync(new URL('../src/runtime/structured-web-app.js',import.meta.url),'utf8'))+'\n');

fs.writeFileSync(new URL('../src/runtime/azure-sources.json',import.meta.url),JSON.stringify(Object.fromEntries(['azure_structured.py','azure_acceptance.py','structured_output.py','structured_http.py','http_acceptance.py','export_contract_acceptance.py'].map(name=>[name,fs.readFileSync(new URL('../src/runtime/'+name,import.meta.url),'utf8')])),null,2)+'\n');

fs.writeFileSync(new URL('../src/runtime/gcp-sources.json',import.meta.url),JSON.stringify(Object.fromEntries(['gcp_structured.py','gcp_acceptance.py','structured_output.py','structured_http.py','http_acceptance.py','export_contract_acceptance.py'].map(name=>[name,fs.readFileSync(new URL('../src/runtime/'+name,import.meta.url),'utf8')])),null,2)+'\n');
fs.writeFileSync(new URL('../src/runtime/iap-web-source.json',import.meta.url),JSON.stringify(fs.readFileSync(new URL('../src/runtime/iap-web-app.js',import.meta.url),'utf8'))+'\n');

fs.writeFileSync(new URL('../src/runtime/ibm-sources.json',import.meta.url),JSON.stringify(Object.fromEntries(['ibm_structured.py','ibm_acceptance.py','structured_output.py','structured_http.py','http_acceptance.py','export_contract_acceptance.py','policy_review.py'].map(name=>[name,fs.readFileSync(new URL('../src/runtime/'+name,import.meta.url),'utf8')])),null,2)+'\n');
