import fs from 'node:fs';
const names=['bounded_rag','rag_aws_adapter','rag_acceptance','catalog_admin','connector_sync','connector_cli','web_user_admin'];
const sources=Object.fromEntries(names.map(name=>[`${name}.py`,fs.readFileSync(new URL(`../src/runtime/${name}.py`,import.meta.url),'utf8')]));
sources['connector_acceptance.py']=fs.readFileSync(new URL('../server/tests/test_connector_contract.py',import.meta.url),'utf8').replace("parents[2]/'src/runtime'","parents[1]/'connectors'");
fs.writeFileSync(new URL('../src/runtime/rag-sources.json',import.meta.url),JSON.stringify(sources,null,2)+'\n');

fs.writeFileSync(new URL('../src/runtime/structured-source.json',import.meta.url),JSON.stringify(fs.readFileSync(new URL('../src/runtime/structured_output.py',import.meta.url),'utf8'))+'\n');

fs.writeFileSync(new URL('../src/runtime/structured-web-source.json',import.meta.url),JSON.stringify(fs.readFileSync(new URL('../src/runtime/structured-web-app.js',import.meta.url),'utf8'))+'\n');
