"""Private VM entry point: durable Firebase queue + Unix-socket model broker."""
import asyncio,base64,fcntl,json,os,signal
from pathlib import Path

async def main():
 os.umask(0o077)
 if os.environ.get('ARCHITECT_DATA_ENVIRONMENT')!='production':raise RuntimeError('Configure the explicit production worker environment')
 if any(os.environ.get(key) for key in ['FIRESTORE_EMULATOR_HOST','STORAGE_EMULATOR_HOST','FIREBASE_AUTH_EMULATOR_HOST']):raise RuntimeError('Production workers cannot use emulators')
 root=Path(os.environ['ARCHITECT_WORKER_STATE']).resolve();root.mkdir(parents=True,exist_ok=True,mode=0o700)
 lock=(root/'worker.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 from google.cloud import storage,secretmanager
 from .firestore_store import FirestoreTransactions
 from .projects import Profiles
 from .credits import CreditLedger
 from .storage_projects import StorageProjects
 from .workspace_jobs import WorkspaceJobs
 from .x_access import XWhitelist
 from .credentials import CredentialVault
 from .pilot_settings import PilotSettings,OpenRouterCatalog
 from .model_broker import NativeModelBroker
 from .worker_host import NativeWorkerHost
 project=os.environ['ARCHITECT_GOOGLE_PROJECT'];namespace='architect_pilot_production'
 store=FirestoreTransactions(FirestoreTransactions.configured(project,os.environ['ARCHITECT_FIRESTORE_DATABASE']).client,namespace=namespace)
 profiles=Profiles(store);access=XWhitelist(store,admin_ids=os.environ['ARCHITECT_ADMIN_X_IDS'].split(','),initial_ids=filter(None,os.environ.get('ARCHITECT_ALLOWED_X_IDS','').split(',')))
 settings=PilotSettings(store,access,OpenRouterCatalog());secrets=secretmanager.SecretManagerServiceClient()
 def secret(name):
  if not name.startswith('projects/'+project+'/secrets/'):raise RuntimeError('Use project-scoped secret version names')
  return secrets.access_secret_version(request={'name':name}).payload.data.decode()
 keyring=json.loads(await asyncio.to_thread(secret,os.environ['ARCHITECT_BYOK_KEYRING_VERSION']))
 vault=CredentialVault(store,profiles,keyring={key:base64.b64decode(value,validate=True) for key,value in keyring['keys'].items()},active_key=keyring['activeKey'])
 key=await asyncio.to_thread(secret,os.environ['ARCHITECT_OPENROUTER_KEY_VERSION'])
 bucket=storage.Client(project=project).bucket(os.environ['ARCHITECT_FIREBASE_STORAGE_BUCKET'])
 projects=StorageProjects(store,profiles,bucket,object_prefix=namespace)
 broker=NativeModelBroker(store=store,profiles=profiles,access=access,settings=settings,vault=vault,platform_key=lambda:key,projects=projects)
 jobs=WorkspaceJobs(store,profiles,projects,bucket,prefix=namespace+'_jobs')
 socket=root/'broker.sock'
 if socket.exists():socket.unlink()
 import uvicorn
 server=uvicorn.Server(uvicorn.Config(broker.app,uds=str(socket),access_log=False,log_level='warning'))
 server_task=asyncio.create_task(server.serve())
 for _ in range(100):
  if server_task.done():await server_task
  if server.started:break
  await asyncio.sleep(.05)
 else:raise RuntimeError('Private model broker did not start')
 os.chmod(socket,0o600)
 stop=asyncio.Event();loop=asyncio.get_running_loop()
 for name in [signal.SIGTERM,signal.SIGINT]:loop.add_signal_handler(name,stop.set)
 host=NativeWorkerHost(jobs=jobs,profiles=profiles,settings=settings,broker=broker,bucket=bucket,root=root/'tenants',broker_socket=str(socket))
 try:await host.run(stop)
 finally:server.should_exit=True;await server_task;lock.close()
if __name__=='__main__':asyncio.run(main())
