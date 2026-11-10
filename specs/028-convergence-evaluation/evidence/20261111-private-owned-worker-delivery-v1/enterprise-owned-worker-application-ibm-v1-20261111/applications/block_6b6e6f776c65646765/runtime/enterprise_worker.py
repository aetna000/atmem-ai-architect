"""Dedicated native question worker; no parser process or arbitrary plug-in loader."""
import asyncio
import os
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from enterprise_configuration import deployment,read_deployment,read_owned_json
from enterprise_native import NativeRuntime,DocumentExecutor


def executor_configuration(value,metadata):
    owned=deployment(metadata)
    if (not isinstance(value,dict)or set(value)!={'format','provider','parserRevision','configuration'}or
        value['format']!='enterprise-document-executor-v1'or value['provider']!=owned['provider']or
        value['parserRevision']!=owned['parserRevision']):
        raise ValueError('Document executor must match the owned provider and parser revision')
    if owned['provider']=='aws':
        from enterprise_aws_jobs import configuration
    elif owned['provider']=='gcp':
        from enterprise_google_jobs import configuration
    else:
        raise ValueError('Native document executor implementation is required for this provider')
    return {**value,'configuration':configuration(value['configuration'])}


def read_executor(metadata,environment,*,path=None):
    value=read_owned_json('enterprise-document-executor.json','ENTERPRISE_DOCUMENT_EXECUTOR_JSON','ENTERPRISE_DOCUMENT_EXECUTOR_FILE',environment,path=path)
    return executor_configuration(value,metadata)


def build_executor(metadata,environment,*,path=None):
    value=read_executor(metadata,environment,path=path)
    if value['provider']=='aws':
        from enterprise_aws_jobs import EcsDocuments
        runner=EcsDocuments(value['configuration'])
    elif value['provider']=='gcp':
        from enterprise_google_jobs import GoogleBatchDocuments
        runner=GoogleBatchDocuments(value['configuration'])
    else:raise ValueError('Use an implemented native document executor')
    # Bind before the runtime reads source/encryption secrets or SQL state. The
    # runtime repeats this boundary when accepting its typed executor.
    runner.bind_runtime(value['provider'],environment)
    return DocumentExecutor(value['parserRevision'],runner)


def worker_runtime(metadata,environment,**options):
    if 'executor'in options:raise ValueError('The configured worker constructs its owned native executor')
    return NativeRuntime(metadata,environment,'worker',executor=build_executor(metadata,environment),**options)


async def run_worker(runtime,*,concurrency=2):
    try:await runtime.worker().run(concurrency=concurrency)
    finally:runtime.close()


def main():
    if sys.argv[1:]:raise SystemExit('Use the owned private worker command without arguments')
    try:
        value=os.environ.get('ENTERPRISE_WORKER_CONCURRENCY','2')
        if not isinstance(value,str)or not re.fullmatch('[1-4]',value):raise ValueError('Use bounded worker concurrency')
        runtime=worker_runtime(read_deployment(),os.environ)
        asyncio.run(run_worker(runtime,concurrency=int(value)))
    except KeyboardInterrupt:return
    except Exception:raise SystemExit('Private worker could not start or continue; check its owned configuration and operator readiness.')from None


if __name__=='__main__':main()
