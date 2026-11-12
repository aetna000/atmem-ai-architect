import base from './runtime/python-container-lock.json' with {type:'json'};

// One reviewed runtime boundary for each generated Python web adapter.
// Keep installer tools out of the delivery image after wheel installation.
export function pythonContainer(module,modules,extraJson=[],options={}){
 if(!/^[a-z_]+$/.test(module)||modules.some(n=>!/^[a-z_]+\.py$/.test(n)))throw Error('Invalid owned Python runtime module');
 if(extraJson.some(n=>! /^[a-z][a-z0-9_-]*\.json$/.test(n)))throw Error('Invalid owned runtime metadata');
 const {web=true,contract=true,assets=[],concurrency=16}=options;
 if(Object.keys(options).some(k=>!['web','contract','assets','concurrency'].includes(k))||typeof web!=='boolean'||typeof contract!=='boolean'||!Array.isArray(assets)||assets.some(n=>! /^[a-z][a-z0-9_-]*\.(?:html|css|js|sql|pem)$/.test(n))||!Number.isInteger(concurrency)||concurrency<1||concurrency>100)throw Error('Invalid owned runtime assets or capacity');
 const patch=base.securityPackages;
 if(!Array.isArray(patch)||patch.length!==1||patch[0].name!=='zlib1g')throw Error('Missing reviewed runtime security package');
 const p=patch[0];
 return `FROM ${base.image}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ADD --checksum=sha256:${p.sha256} ${p.url} /tmp/runtime-security.deb
RUN dpkg -i /tmp/runtime-security.deb && rm /tmp/runtime-security.deb
WORKDIR /app
COPY requirements.lock .
RUN python -I -m pip --isolated install --no-cache-dir --only-binary=:all: --require-hashes -r requirements.lock && python -I -m pip --isolated uninstall --yes pip && rm -rf /usr/local/lib/python3.13/ensurepip
COPY ${modules.join(' ')} ./
${contract?'COPY output-contract.json ./\n':''}${extraJson.length?'COPY '+extraJson.join(' ')+' ./\n':''}${assets.length?'COPY '+assets.join(' ')+' ./\n':''}${web?'COPY web/ ./web/\n':''}USER 10001:10001
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "${module}:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--no-access-log", "--no-proxy-headers", "--limit-concurrency", "${concurrency}"]
`;
}
