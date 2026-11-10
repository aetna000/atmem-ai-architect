"""Trusted local worker policy, separate from browser input and model selection.

This constrains native local commands, not a hosted OS/tenant boundary. Only
control-plane selected tool directories may be added as read roots. Do not pass
client paths, source repositories or credential directories here.
"""
import json
import os
import re
from pathlib import Path
import shutil
import tomllib

from .codex_app_server import CodexAppServer

PROFILE = 'atmem-engineering-v2'


def configured_mcp_names():
    """Inspect names only; never copy credentials or server definitions.

    An empty table override merges with the user's existing table in current
    Codex versions. Explicitly disable known entries; the live worker check must
    still reject any server introduced by another effective configuration layer.
    """
    names=set()
    paths=[Path('/etc/codex/config.toml'),Path(os.getenv('CODEX_HOME',str(Path.home()/'.codex')))/'config.toml']
    def collect(value):
        if not isinstance(value,dict):return
        servers=value.get('mcp_servers',{})
        if isinstance(servers,dict):names.update(servers)
        for nested in value.values():
            if isinstance(nested,dict):collect(nested)
    for path in paths:
        if path.exists():
            with path.open('rb') as source:collect(tomllib.load(source))
    return sorted(names)


def configured_shell_override_names():
    """Return keys to blank in the worker; never forward their original values."""
    names=set()
    paths=[Path('/etc/codex/config.toml'),Path(os.getenv('CODEX_HOME',str(Path.home()/'.codex')))/'config.toml']
    def collect(value):
        if not isinstance(value,dict):return
        policy=value.get('shell_environment_policy',{})
        if isinstance(policy,dict) and isinstance(policy.get('set',{}),dict):names.update(policy.get('set',{}))
        for nested in value.values():
            if isinstance(nested,dict):collect(nested)
    for path in paths:
        if path.exists():
            with path.open('rb') as source:collect(tomllib.load(source))
    return sorted(names)


def worker_command(read_roots=(),*,temporary_dir=None):
    executable = shutil.which('codex')
    if not executable:
        raise RuntimeError('The selected native worker is unavailable')
    binary = Path(executable).resolve(strict=True)
    # Include the symlink's directory and native package tree so the CLI's
    # sandbox helper can execute. These are code paths, not its auth/state home.
    roots = {Path(executable).parent.resolve(), binary.parent}
    for root in read_roots:
        path = Path(root).resolve(strict=True)
        if not path.is_dir():
            raise ValueError('A worker tool read root must be an existing directory')
        secrets = [Path.home()/name for name in ['.codex','.aws','.ssh','.kube']]
        if Path.home().is_relative_to(path) or any(path.is_relative_to(p) or p.is_relative_to(path) for p in secrets):
            raise ValueError('Worker tools cannot expose a home or credential tree')
        roots.add(path)
    forbidden = {Path('/'), Path.home(), Path.home()/'.codex', Path.home()/'.aws', Path.home()/'.ssh'}
    if roots & forbidden:
        raise ValueError('Worker tool roots cannot grant filesystem, home or credential trees')
    entries = {':root':'deny', ':minimal':'read', ':tmpdir':'deny', ':slash_tmp':'deny'}
    entries.update({str(p):'read' for p in sorted(roots)})
    filesystem = ','.join(f'{json.dumps(k)}={json.dumps(v)}' for k,v in entries.items())
    # The native proxy must be active to propagate its Unix-socket allowlist.
    # No domain is allowed, local binding is forbidden and raw IP access remains
    # sandboxed. The profile's enabled flag is not an unrestricted network grant.
    network='enabled=true,domains={},proxy_url="http://127.0.0.1:0",enable_socks5=false,allow_local_binding=false'
    if temporary_dir is not None:
        # Terraform's provider protocol binds random AF_UNIX sockets beneath its
        # private temp directory. Permit only that subtree, never Docker/host IPC
        # or IP networking. This must be requalified per native worker platform.
        network+=',unix_sockets={'+json.dumps(str(temporary_dir))+'="allow"}'
    definition = f'permissions.{PROFILE}={{extends=":workspace",filesystem={{{filesystem}}},network={{{network}}}}}'
    command = [str(binary),'app-server','--listen','stdio://',
            '-c','analytics.enabled=false','-c',definition,
            '-c',f'default_permissions={json.dumps(PROFILE)}',
            '-c','shell_environment_policy.inherit="core"',
            '-c','shell_environment_policy.ignore_default_excludes=false',
            '-c','allow_login_shell=false','-c','features.shell_snapshot=false',
            '-c','features.network_proxy=true',
            '-c','mcp_servers={}','-c','features.apps=false','-c','features.plugins=false',
            '-c','web_search="disabled"']
    if temporary_dir is not None:
        command.extend(['-c',f'shell_environment_policy.set.TMPDIR={json.dumps(str(temporary_dir))}'])
    for name in configured_mcp_names():
        # CLI override dotted paths do not parse TOML quotes in key segments.
        # Refuse unusual keys rather than creating a second, ineffective entry.
        if not re.fullmatch(r'[A-Za-z0-9_-]+',name):
            raise ValueError('An MCP configuration key cannot be disabled safely by this worker')
        command.extend(['-c',f'mcp_servers.{name}.enabled=false'])
    for name in configured_shell_override_names():
        if name=='TMPDIR':continue
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name):
            raise ValueError('A shell override key cannot be disabled safely by this worker')
        command.extend(['-c',f'shell_environment_policy.set.{name}=""'])
    return command


class CodexWorkerClient(CodexAppServer):
    def __init__(self,workspace,*,read_roots=()):
        root=Path(workspace).resolve(strict=True)
        temporary=root/'.worker-tmp'
        if os.name=='posix' and len(os.fsencode(temporary))>80:
            raise ValueError('Register a shorter worker workspace path for Unix-socket validators')
        if temporary.is_symlink():
            raise ValueError('Worker temporary storage cannot be a symlink')
        temporary.mkdir(exist_ok=True)
        command=worker_command(read_roots,temporary_dir=temporary)
        definition=next(value for value in command if value.startswith(f'permissions.{PROFILE}='))
        self.expected_worker_profile=tomllib.loads(definition)['permissions'][PROFILE]
        super().__init__(root,command=command,experimental=True)

    async def verify_worker_tools(self,expected_profile=PROFILE):
        if expected_profile!=PROFILE:
            raise RuntimeError('This worker cannot attest a different named permission profile')
        effective=await self.request('config/read',{'includeLayers':False,'cwd':str(self.workspace)})
        config=effective.get('config')
        if not isinstance(config,dict):
            raise RuntimeError('Worker configuration acknowledgement is unavailable')
        definitions=config.get('mcp_servers',{})
        if not isinstance(definitions,dict) or any(not isinstance(v,dict) or v.get('enabled') is not False for v in definitions.values()):
            raise RuntimeError('Unapproved MCP enablement is present in this local worker')
        features=config.get('features',{})
        if not isinstance(features,dict) or features.get('apps') is not False or features.get('plugins') is not False or config.get('web_search')!='disabled':
            raise RuntimeError('External tools were not disabled in this local worker')
        shell=config.get('shell_environment_policy',{})
        if config.get('allow_login_shell') is not False or features.get('shell_snapshot') is not False or not isinstance(shell,dict) or shell.get('inherit')!='core' or shell.get('ignore_default_excludes') is not False or shell.get('include_only') not in (None,[]):
            raise RuntimeError('The restricted worker shell environment was not confirmed')
        overrides=shell.get('set')
        if not isinstance(overrides,dict) or overrides.get('TMPDIR')!=str(self.workspace/'.worker-tmp') or any(k!='TMPDIR' and v!='' for k,v in overrides.items()):
            raise RuntimeError('Unexpected inherited shell variable overrides were configured')
        profile=config.get('permissions',{}).get(PROFILE,{})
        network=profile.get('network',{})
        if features.get('network_proxy') is not True or network.get('enabled') is not True or network.get('domains') not in ({},None) or network.get('allow_local_binding') is not False:
            raise RuntimeError('The deny-all worker proxy was not confirmed')
        filesystem=profile.get('filesystem')
        if isinstance(filesystem,dict):
            filesystem=dict(filesystem)
            if filesystem.get('glob_scan_max_depth') is None:filesystem.pop('glob_scan_max_depth',None)
        if profile.get('extends')!=':workspace' or filesystem!=self.expected_worker_profile['filesystem']:
            raise RuntimeError('The worker filesystem policy changed in an effective configuration layer')
        if network.get('unix_sockets')!=self.expected_worker_profile['network'].get('unix_sockets') or network.get('dangerously_allow_all_unix_sockets') is True or network.get('dangerously_allow_non_loopback_proxy') is True:
            raise RuntimeError('Unexpected local socket access was added to the worker')
        roots=profile.get('workspace_roots',{}) or {}
        if not isinstance(roots,dict) or any(value is not False for value in roots.values()):
            raise RuntimeError('Unexpected profile-owned workspace roots were added')
        result=await self.request('mcpServerStatus/list',{'limit':100})
        states=result.get('data')
        if not isinstance(states,list) or result.get('nextCursor'):
            raise RuntimeError('Unapproved MCP tools are configured in this local worker')
        # The status API lists disabled definitions too. Require both effective
        # disabled configuration and no initialized server/tool/resource surface.
        for state in states:
            if not isinstance(state,dict) or state.get('name') not in definitions or state.get('runtimeStatus') is not None or state.get('tools')!={} or state.get('resources')!=[] or state.get('resourceTemplates')!=[]:
                raise RuntimeError('An MCP server exposed tools or resources in this local worker')
        return {'configuredMcpDefinitions':len(definitions),'allDisabled':True,'exposedMcpTools':0,'apps':False,'plugins':False,'webSearch':'disabled'}
