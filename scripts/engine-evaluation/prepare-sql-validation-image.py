"""Operator-owned offline SQL/SDK runtime derivation from explicit pinned inputs.

Never builds a model Dockerfile. No account lookup, automatic pull or dependency
resolution. Public base images and exact target wheels must already be cached.
"""
import argparse,hashlib,json,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--postgres-image',required=True);parser.add_argument('--python-image',required=True);parser.add_argument('--wheels',type=Path,required=True);parser.add_argument('--platform',choices=['linux/arm64','linux/amd64'],required=True);parser.add_argument('--provider',choices=['aws','azure','gcp','ibm'],required=True);parser.add_argument('--endpoint',required=True);args=parser.parse_args()
import re
assert all(re.fullmatch(r'docker.io/library/(?:python|postgres)@sha256:[a-f0-9]{64}',image)for image in [args.postgres_image,args.python_image])
assert args.endpoint.startswith('unix:///')and Path(args.endpoint[7:]).is_socket()
out=args.output.resolve();out.mkdir(parents=True,exist_ok=False);context=out/'context';context.mkdir();config=out/'docker-config';config.mkdir();(config/'config.json').write_text('{"auths":{}}\n')
catalog=json.loads((ROOT/'server/engineering_assets/application-runtime.json').read_text());lock=catalog['providers'][args.provider]['testRequirements'];(context/'requirements.lock').write_text(lock);shutil.copytree(args.wheels,context/'wheels');shutil.copyfile(ROOT/'server/engineering_assets/sql_validation.py',context/'sql_validation.py')
source=r'''ARG PG_IMAGE
ARG PYTHON_IMAGE
FROM ${PG_IMAGE} AS postgres
# Public trusted executables only. Keep their non-glibc dynamic dependencies in
# a private directory; never replace the Python base's loader/libc or TLS library.
RUN set -eu; mkdir -p /runtime/pg /runtime/libs /runtime/notices; \
    cp -a /usr/lib/postgresql/17/bin /runtime/pg/bin; \
    cp -aL /usr/share/postgresql/17 /runtime/share; \
    cp -a /usr/lib/postgresql/17/lib /runtime/pg/lib; \
    rm -rf /runtime/pg/lib/bitcode /runtime/pg/lib/llvmjit*; \
    (for executable in /usr/lib/postgresql/17/bin/postgres /usr/lib/postgresql/17/bin/initdb /usr/lib/postgresql/17/bin/pg_ctl /usr/lib/postgresql/17/bin/psql /runtime/pg/lib/*.so; do ldd "$executable"; done) | awk '/=> \// {print $3}' | sort -u > /runtime/library-paths.txt; \
    while IFS= read -r library; do \
      name="$(basename "$library")"; \
      case "$name" in libc.so.*|libm.so.*|libdl.so.*|libpthread.so.*|librt.so.*|ld-linux*) continue;; esac; \
      if [ -e "/runtime/libs/$name" ]; then cmp "$library" "/runtime/libs/$name"; else cp -L "$library" "/runtime/libs/$name"; fi; \
    done < /runtime/library-paths.txt; \
    dpkg-query -W > /runtime/packages.txt; \
    find /usr/share/doc -name copyright -type f -exec cp --parents '{}' /runtime/notices/ ';'; \
    mkdir -p /runtime/wrappers; \
    for executable in /usr/lib/postgresql/17/bin/*; do \
      name="$(basename "$executable")"; \
      printf '#!/bin/sh\nLD_LIBRARY_PATH=/opt/atmem/postgres-libs exec /usr/lib/postgresql/17/bin/%s "$@"\n' "$name" > "/runtime/wrappers/$name"; \
      chmod 0555 "/runtime/wrappers/$name"; \
    done
FROM ${PYTHON_IMAGE} AS sdk
COPY requirements.lock /build/requirements.lock
COPY wheels/ /build/wheels/
RUN python -I -m pip --isolated install --no-cache-dir --no-index --find-links=/build/wheels --require-hashes -r /build/requirements.lock && python -I -m pip check
FROM ${PYTHON_IMAGE}
COPY --from=sdk /usr/local/lib/python3.13/site-packages/ /usr/local/lib/python3.13/site-packages/
COPY --from=postgres /runtime/pg/ /usr/lib/postgresql/17/
COPY --from=postgres /runtime/share/ /usr/share/postgresql/17/
COPY --from=postgres /runtime/libs/ /opt/atmem/postgres-libs/
COPY --from=postgres /runtime/wrappers/ /opt/atmem/pg-bin/
COPY --from=postgres /runtime/library-paths.txt /runtime/packages.txt /opt/atmem/postgres-provenance/
COPY --from=postgres /runtime/notices/ /opt/atmem/postgres-notices/
COPY sql_validation.py /opt/atmem/sql_validation.py
RUN printf 'atmem:x:65532:65532:AtMem isolated checks:/tmp:/usr/sbin/nologin\n' >> /etc/passwd && printf 'atmem:x:65532:\n' >> /etc/group
ENV PATH=/opt/atmem/pg-bin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin PYTHONDONTWRITEBYTECODE=1
'''
(context/'Dockerfile').write_text(source)
prefix=['docker','--host',args.endpoint,'--config',str(config)];env={'PATH':os.environ.get('PATH',''),'DOCKER_CONFIG':str(config),'DOCKER_HOST':args.endpoint}
tag='atmem-local/sql-validation-'+args.provider+':'+out.name
for image in [args.postgres_image,args.python_image]:
 r=subprocess.run([*prefix,'image','inspect','--platform',args.platform,image],env=env,capture_output=True,text=True,check=True);(out/('postgres-base.json'if image==args.postgres_image else'python-base.json')).write_text(r.stdout)
with(out/'build.log').open('wb')as log:
 result=subprocess.run([*prefix,'build','--network','none','--pull=false','--platform',args.platform,'--build-arg','PG_IMAGE='+args.postgres_image,'--build-arg','PYTHON_IMAGE='+args.python_image,'--label','atmem.qualification=isolated-sql-v1','--tag',tag,str(context)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240)
assert result.returncode==0,'Offline runtime build failed; inspect retained build.log'
image=json.loads(subprocess.check_output([*prefix,'image','inspect',tag],env=env,text=True))[0]
assert image['Os']+'/'+image['Architecture']==args.platform,'Built image differs from the explicitly selected platform'
receipt={'imageId':image['Id'],'tag':tag,'platform':args.platform,'providerDependencyLock':args.provider,'postgresImage':args.postgres_image,'pythonImage':args.python_image,'dockerfileSha256':hashlib.sha256(source.encode()).hexdigest(),'lockSha256':hashlib.sha256(lock.encode()).hexdigest(),'driverSha256':hashlib.sha256((context/'sql_validation.py').read_bytes()).hexdigest(),'contextHashes':{str(p.relative_to(context)):hashlib.sha256(p.read_bytes()).hexdigest()for p in context.rglob('*')if p.is_file()},'downloadsDuringBuild':False,'cloudOperations':False,'boundary':'Operator-derived immutable SQL/SDK check image from pinned public code/locks. Requires actual isolated startup/isolation/application qualification; not managed Postgres or security acceptance.'}
(out/'image.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'imageId':image['Id'],'platform':args.platform,'tag':tag}))
