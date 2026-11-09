import base from './runtime/python-container-lock.json' with {type:'json'};

// One reviewed runtime boundary for each generated Python web adapter.
// Keep installer tools out of the delivery image after wheel installation.
export function pythonContainer(module,modules){
 if(!/^[a-z_]+$/.test(module)||modules.some(n=>!/^[a-z_]+\.py$/.test(n)))throw Error('Invalid owned Python runtime module');
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
COPY output-contract.json ./
COPY web/ ./web/
USER 10001:10001
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "${module}:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--no-access-log", "--no-proxy-headers", "--limit-concurrency", "16"]
`;
}
