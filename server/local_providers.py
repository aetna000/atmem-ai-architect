"""Supported local CLI account adapters. No account token extraction or custom OAuth."""
import asyncio, base64, json, os, shutil, signal, sys, tempfile
from pathlib import Path
from .settings import home

SIGN_IN={'claude-code':('claude','claude auth login'),'codex':('codex','codex login'),'gemini-cli':('gemini','gemini'),'copilot':('copilot','copilot login')}

PROFILE_KEYS = {'codex': 'CODEX_HOME', 'claude-code': 'CLAUDE_CONFIG_DIR'}

def profile_dir(provider):
    return home().resolve() / 'provider-accounts' / provider

def provider_binary(binary):
    found = shutil.which(binary)
    if found or binary not in ('codex', 'claude'):
        return found
    # Desktop launchers often omit the user's installation directory from PATH.
    locations = [Path.home() / '.local/bin', Path('/opt/homebrew/bin'), Path('/usr/local/bin')]
    if os.name == 'nt':
        locations = [Path.home() / '.local/bin']
        if os.environ.get('APPDATA'):
            locations.append(Path(os.environ['APPDATA']) / 'npm')
    for location in locations:
        found = shutil.which(binary, path=str(location))
        if found:
            return found
    return None

def cli_command(argv):
    """Resolve PATHEXT shims explicitly; CreateProcess does not search .cmd names."""
    return [provider_binary(argv[0]) or argv[0], *argv[1:]]

def account_environment(provider=None):
    env=dict(os.environ)
    for key in ['ANTHROPIC_API_KEY','ANTHROPIC_AUTH_TOKEN','OPENAI_API_KEY','CODEX_API_KEY','GEMINI_API_KEY','GOOGLE_API_KEY','GITHUB_TOKEN','GH_TOKEN','COPILOT_GITHUB_TOKEN']:
        env.pop(key,None)
    if provider in PROFILE_KEYS and profile_dir(provider).is_dir():
        env[PROFILE_KEYS[provider]] = str(profile_dir(provider))
        for key in ('CLAUDE_CODE_OAUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR',
                    'CODEX_ACCESS_TOKEN', 'CODEX_AUTH_JSON'):
            env.pop(key, None)
    return env

# Official sign-in, started from the app: each CLI opens its provider's own page in the browser.
LOGIN={'claude-code':['claude','auth','login','--claudeai'],'codex':['codex','login'],'copilot':['copilot','login']}
STATUS={'claude-code':['claude','auth','status','--json'],'codex':['codex','login','status']}
LOGINS={}
LOGIN_LOCKS={}

def signed_in(provider):
    """True/False when the CLI can tell us, None when it can't."""
    argv=STATUS.get(provider)
    if not argv or not provider_binary(argv[0]):return None
    import subprocess
    try:
        done=subprocess.run(cli_command(argv),capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=8,stdin=subprocess.DEVNULL,env=account_environment(provider))
    except Exception:
        return None
    if provider=='claude-code':
        try:return bool(json.loads(done.stdout).get('loggedIn'))
        except Exception:return None
    return done.returncode == 0 and 'logged in using chatgpt' in (done.stdout + done.stderr).lower()

def capabilities():
    return {key:{'available':bool(provider_binary(binary)),'installed':bool(provider_binary(binary)),'loginCommand':command,'canSignInFromApp':key in LOGIN,
                 'loginStatus':login_status(key), 'signedIn':signed_in(key) if provider_binary(binary) else False} for key,(binary,command) in SIGN_IN.items()}

def login_status(provider):
    attempt = LOGINS.get(provider)
    if attempt is None:
        return None
    code = attempt[0].returncode
    if code is None:
        return 'pending'
    return 'completed' if code == 0 else 'failed'

async def start_login(provider):
    """Start the provider's official login; return a sign-in URL if the CLI prints one."""
    if provider not in LOGIN:
        raise RuntimeError('This provider does not support sign-in from Architect.')
    async with LOGIN_LOCKS.setdefault(provider, asyncio.Lock()):
        return await _launch_login(provider)

async def _launch_login(provider):
    import re
    argv=LOGIN.get(provider)
    if not argv or not provider_binary(argv[0]):raise RuntimeError('This provider has no sign-in AtMem AI Architect can start. Use its API key instead.')
    if provider in PROFILE_KEYS:
        profile_dir(provider).mkdir(mode=0o700, parents=True, exist_ok=True)
    running=LOGINS.get(provider)
    if running and running[0].returncode is None:return {'started':True,'url':running[1]}
    process=await asyncio.create_subprocess_exec(*cli_command(argv),stdin=asyncio.subprocess.DEVNULL,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT,env=account_environment(provider),start_new_session=os.name!='nt')
    LOGINS[provider]=(process,None)
    url=None
    try:
        deadline=asyncio.get_running_loop().time()+6
        while asyncio.get_running_loop().time()<deadline and url is None:
            line=await asyncio.wait_for(process.stdout.readline(),timeout=max(.1,deadline-asyncio.get_running_loop().time()))
            if not line:break
            found=re.search(r'https://\S+',line.decode(errors='ignore'))
            if found:url=found.group(0).rstrip('.,)')
    except asyncio.TimeoutError:pass
    # Keep draining output so the CLI can finish its callback; don't block the request.
    async def drain():
        try:
            async with asyncio.timeout(300):
                while await process.stdout.read(4096):
                    pass
                await process.wait()
        except TimeoutError:
            if process.returncode is None:
                process.kill()
                await process.wait()
        finally:
            if LOGINS.get(provider, (None,))[0] is process:
                LOGINS[provider] = (process, None)
    asyncio.create_task(drain())
    LOGINS[provider]=(process,url)
    if not url and process.returncode not in (None, 0):
        raise RuntimeError('The provider could not start sign-in. Retry from Connections.')
    return {'started':True,'url':url}

def extract_json(text):
    text=text.strip()
    if text.startswith('```'):text='\n'.join(text.splitlines()[1:-1])
    return json.loads(text)

def strict_schema(schema):
    """Codex structured output requires every declared object field to be required."""
    schema=json.loads(json.dumps(schema))
    def visit(value):
        if isinstance(value,dict):
            if value.get('type')=='object' and 'properties' not in value:
                value.clear();value.update({'type':'string','description':'A JSON-encoded object. Preserve every field required by the application contract.'})
            if value.get('type')=='object' and 'properties' in value:value['required']=list(value['properties']);value['additionalProperties']=False
            for child in value.values():visit(child)
        elif isinstance(value,list):
            for child in value:visit(child)
    visit(schema);return schema

def restore_json_objects(value, schema, root=None):
    root = root or schema
    if '$ref' in schema:
        target = root
        for part in schema['$ref'].removeprefix('#/').split('/'):
            target = target[part]
        return restore_json_objects(value, target, root)
    for branch in schema.get('anyOf', []):
        kind = branch.get('type')
        if '$ref' in branch or kind == 'object' and isinstance(value, (dict, str)) or kind == 'array' and isinstance(value, list):
            return restore_json_objects(value, branch, root)
    if schema.get('type') == 'object' and 'properties' not in schema and isinstance(value, str):
        decoded = json.loads(value)
        if not isinstance(decoded, dict):
            raise ValueError('Expected a JSON object from the provider')
        return decoded
    if isinstance(value, dict):
        return {key: restore_json_objects(item, schema.get('properties', {}).get(key, {}), root) for key, item in value.items()}
    if isinstance(value, list):
        return [restore_json_objects(item, schema.get('items', {}), root) for item in value]
    return value

def provider_failure(output=b'',error=b''):
    """Classify provider errors without exposing raw CLI output or account details."""
    text=(output.decode(errors='replace') if isinstance(output,bytes) else str(output))+' '+(error.decode(errors='replace') if isinstance(error,bytes) else str(error))
    text=text[:64000].lower()
    if any(term in text for term in ['credits_required', 'model_requires_usage_credits', "out of usage credits"]):
        return 'This model requires provider usage credits. Choose another model or connect ChatGPT in Connections.'
    if any(term in text for term in ['session limit','usage limit','hit your limit','rate limit','rate_limit','insufficient_quota','credit balance','too many requests']):
        return 'The selected architect has reached its usage or rate limit. Wait for the provider reset or choose another connected architect. Your design is preserved; no correction was applied.'
    if any(term in text for term in ['not logged in','authentication failed','invalid api key','unauthorized','login required']):
        return 'The selected architect needs you to sign in again through its official client or update its API connection. Your design is preserved.'
    if any(term in text for term in ['model not found','model_not_found','model is not available']):
        return 'That model is not available to the selected account. Choose an accessible model in Connections. Your design is preserved.'
    return 'Provider request failed. Check its official CLI sign-in, model access and usage limits. No changes were applied.'

async def communicate(argv,prompt,cwd,is_disconnected,env=None,timeout=150):
    process=await asyncio.create_subprocess_exec(*argv,stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,cwd=cwd,env=env,start_new_session=os.name!='nt')
    task=asyncio.create_task(process.communicate(prompt.encode()))
    deadline=asyncio.get_running_loop().time()+timeout
    try:
        while not task.done():
            if await is_disconnected():raise asyncio.CancelledError()
            if asyncio.get_running_loop().time()>deadline:raise TimeoutError('Architect request timed out.')
            await asyncio.sleep(.2)
        output,error=await task
        if process.returncode:raise RuntimeError(provider_failure(output,error))
        return output.decode()
    finally:
        if process.returncode is None:
            try:
                if os.name=='nt':process.terminate()
                else:os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:await asyncio.wait_for(process.wait(),3)
            except asyncio.TimeoutError:
                try:
                    if os.name=='nt':process.kill()
                    else:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                await process.wait()
        if not task.done():task.cancel()
        try:await task
        except (asyncio.CancelledError,Exception):pass

CLAUDE_EFFORTS=['low','medium','high','xhigh','max']
# Claude Code accepts these model names; the list matches the current Claude family.
CLAUDE_MODELS=[('claude-opus-5-5','Opus 5.5'),('claude-fable-5-1','Fable 5.1'),('claude-sonnet-5','Sonnet 5'),('claude-haiku-4-5-20251001','Haiku 4.5')]
COPILOT_EFFORTS=['low','medium','high','xhigh','max']

def models(provider):
    """Models and thinking levels the provider's own CLI reports; empty list means type an ID."""
    import subprocess
    if provider=='claude-code':
        return [{'id':i,'name':n,'efforts':CLAUDE_EFFORTS,'defaultEffort':'medium'} for i,n in CLAUDE_MODELS]
    if provider=='codex' and provider_binary('codex'):
        try:
            done=subprocess.run(cli_command(['codex','debug','models']),capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=15,stdin=subprocess.DEVNULL,env=account_environment(provider))
            data=json.loads(done.stdout)
            return [{'id':m['slug'],'name':m.get('display_name',m['slug']),'efforts':[e['effort'] for e in m.get('supported_reasoning_levels',[])],'defaultEffort':m.get('default_reasoning_level')}
                    for m in data.get('models',[]) if m.get('visibility','list')=='list']
        except Exception:
            return []
    if provider=='gemini-cli' and shutil.which('gemini'):
        return [{'id':'auto','name':'Gemini CLI (your configured model)','efforts':[],'defaultEffort':None}]
    if provider=='copilot':
        # The Copilot SDK path doesn't take a thinking level yet; offer only what we can honour.
        return [{'id':'auto','name':'Auto (Copilot picks)','efforts':[],'defaultEffort':None}]
    return []

async def call_cli(provider,model,prompt,system,schema,is_disconnected,effort=None,images=None,timeout=150):
    binary=provider_binary(SIGN_IN[provider][0])
    if not binary:raise RuntimeError(f'Install and sign in with {SIGN_IN[provider][0]} first, or choose an API key.')
    with tempfile.TemporaryDirectory(prefix='atforma-agent-') as cwd:
        env=account_environment(provider)
        if provider=='claude-code':
            args=[binary,'-p','--safe-mode','--strict-mcp-config','--tools','','--no-session-persistence','--output-format','json','--json-schema',json.dumps(schema),'--system-prompt',system]
            if model not in ('default','auto'):args+=['--model',model]
            if effort in CLAUDE_EFFORTS:args+=['--effort',effort]
            if images:
                args+=['--input-format','stream-json']
                content=[{'type':'text','text':prompt}]+[{'type':'image','source':{'type':'base64','media_type':i['mime'],'data':i['data']}} for i in images]
                prompt=json.dumps({'type':'user','message':{'role':'user','content':content}})+'\n'
            result=json.loads(await communicate(args,prompt,cwd,is_disconnected,env,timeout=timeout))
            if result.get('is_error'):raise RuntimeError(provider_failure(json.dumps(result)))
            return result.get('structured_output') or extract_json(result.get('result',''))
        if provider=='codex':
            schema_path=Path(cwd)/'response-schema.json';schema_path.write_text(json.dumps(strict_schema(schema)))
            args=[binary,'exec','--sandbox','read-only','--skip-git-repo-check','--ephemeral','--ignore-user-config','--ignore-rules','--disable','shell_tool','--disable','unified_exec','--disable','plugins','--disable','apps','--disable','browser_use','--disable','in_app_browser','--disable','code_mode_host','-c','approval_policy="never"','-c','web_search="disabled"','--output-schema',str(schema_path),'--color','never','-']
            for index,item in enumerate(images or []):
                image_path=Path(cwd)/f'attachment-{index}.{item["mime"].split("/")[1]}'
                image_path.write_bytes(base64.b64decode(item['data']));image_path.chmod(0o600)
                args+=['--image',str(image_path)]
            if model not in ('default','auto'):args+=['--model',model]
            if effort:args+=['-c',f'model_reasoning_effort="{effort}"']
            return restore_json_objects(extract_json(await communicate(args,system+'\n\n'+prompt,cwd,is_disconnected,env,timeout=timeout)), schema)
        if provider=='gemini-cli':
            settings=Path(cwd)/'settings.json';settings.write_text(json.dumps({'tools':{'core':[]},'hooksConfig':{'enabled':False},'mcp':{'allowed':['atforma-no-servers']},'telemetry':{'enabled':False},'general':{'enableAutoUpdate':False,'sessionRetention':{'enabled':False}}}))
            env['GEMINI_CLI_SYSTEM_SETTINGS_PATH']=str(settings)
            policy=Path(cwd)/'deny-tools.toml';policy.write_text('[[rule]]\ntoolName = "*"\ndecision = "deny"\npriority = 999\n')
            args=[binary,'--prompt',system,'--output-format','json','--approval-mode','plan','--extensions','none','--allowed-mcp-server-names','atforma-no-servers','--policy',str(policy)]
            if model not in ('default','auto'):args+=['--model',model]
            result=json.loads(await communicate(args,prompt,cwd,is_disconnected,env,timeout=timeout))
            if result.get('error'):raise RuntimeError('Gemini request failed. Run gemini to sign in and check your model access.')
            return extract_json(result.get('response',''))
        # Official Copilot SDK provides tool exclusion and permission denial without --allow-all.
        worker=Path(__file__).with_name('copilot_worker.py')
        return extract_json(await communicate([sys.executable,str(worker)],json.dumps({'prompt':prompt,'system':system,'schema':strict_schema(schema),'model':model,'cwd':cwd,'cli':binary,'images':images or []}),cwd,is_disconnected,env,timeout=timeout))
