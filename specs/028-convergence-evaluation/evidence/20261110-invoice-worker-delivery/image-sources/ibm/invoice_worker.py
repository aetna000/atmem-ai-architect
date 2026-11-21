"""Dedicated native queue worker; private process liveness, never a business API."""
import asyncio
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import os
from pathlib import Path
import sys
import threading
sys.path.insert(0,str(Path(__file__).resolve().parent))
from invoice_native import native_database,owned_deployment,destination_contract
from invoice_stage import replay_review
from workflow_process_stage import ProcessStage
from workflow_worker import WorkflowRuntime
from workflow_contract import normalized_contract
from invoice_runtime_secrets import prepare_runtime_environment

COMMON=['DOCUMENT_BUCKET','REGION','PARSER_ENDPOINT','MAX_OUTPUT_TOKENS']
EXTRACT_KEYS={
 'aws':COMMON+['AWS_ACCOUNT_ID','MODEL_ID','AWS_CONTAINER_CREDENTIALS_RELATIVE_URI','AWS_CONTAINER_CREDENTIALS_FULL_URI','AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE','AWS_REGION','AWS_DEFAULT_REGION'],
 'azure':COMMON+['DOCUMENT_ACCOUNT','WORKLOAD_IDENTITY_CLIENT_ID','MANAGED_IDENTITY_CLIENT_ID','MODEL_RESOURCE_ID','MODEL_ENDPOINT','MODEL_DEPLOYMENT','IDENTITY_ENDPOINT','IDENTITY_HEADER','MSI_ENDPOINT','MSI_SECRET'],
 'gcp':COMMON+['PROJECT_ID','MODEL_ID','POLICY_REVIEW_BASE64','PARSER_AUDIENCE'],
 'ibm':COMMON+['IBM_ACCOUNT_ID','WATSONX_PROJECT_ID','RUNTIME_INSTANCE_ID','MODEL_REGION','MODEL_ID','IAM_PROFILE_ID','POLICY_REVIEW_BASE64']}

def stage_environment(environment,names):
    return{'PATH':'/usr/local/bin:/usr/bin:/bin','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1',**{name:environment[name]for name in names if name in environment}}

def create_native_worker(provider,environment,*,connection=None):
    if provider not in EXTRACT_KEYS:raise ValueError('Unsupported owned invoice provider')
    env=prepare_runtime_environment(provider,environment,'worker');contract=destination_contract(env);verified=replay_review(env,contract);stage=Path(__file__).parent/'invoice_stage.py'
    if normalized_contract(env['DESTINATION_ENDPOINT'],env['DESTINATION_SCOPE'])!=contract:raise ValueError('Worker destination differs from the approved integration identity')
    extract=ProcessStage([sys.executable,'-I',str(stage),'extract'],kind='extract',timeout_seconds=180,environment=stage_environment(env,EXTRACT_KEYS[provider]))
    dispatch=ProcessStage([sys.executable,'-I',str(stage),'dispatch'],kind='dispatch',timeout_seconds=45,idempotency_verified=verified,environment=stage_environment(env,['DESTINATION_ENDPOINT','DESTINATION_SCOPE','DESTINATION_TOKEN_FILE','DESTINATION_CONTRACT_BASE64','DESTINATION_REPLAY_REVIEW_BASE64']))
    return WorkflowRuntime(connection if connection is not None else native_database(provider,env,'worker'),extract,dispatch,destination_contract=contract,idempotent_destination=verified,namespace=env['WORKFLOW_NAMESPACE'],lease_seconds=600)

class Liveness(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        self.send_response(200 if self.path=='/healthz'else 404);self.send_header('Content-Length','0');self.end_headers()

def main():
    runtime=create_native_worker(owned_deployment()['provider'],os.environ);port=int(os.environ.get('PORT','8080'))
    if not 1024<=port<=65535:raise ValueError('Use the owned nonprivileged liveness port')
    # Process liveness only. SQL bootstrap/restore and destination acceptance are
    # separate deployment checks; this endpoint claims no business readiness.
    server=ThreadingHTTPServer(('0.0.0.0',port),Liveness);threading.Thread(target=server.serve_forever,daemon=True).start()
    # Default pairs one worker execution with one parser slot. Scale both sides
    # together only after throughput/quotas and backpressure are qualified.
    try:asyncio.run(runtime.run(concurrency=1))
    finally:server.shutdown();server.server_close()

if __name__=='__main__':main()
