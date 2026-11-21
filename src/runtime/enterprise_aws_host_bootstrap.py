"""New dedicated ECS host preparation; no client content or credentials accepted."""
import base64
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import uuid
sys.path.insert(0,str(Path(__file__).resolve().parent))
from enterprise_aws_host_probe import expected_policy,first_rule_matches


def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Ambiguous host configuration')
        result[key]=value
    return result


def environment(raw):
    values={}
    for line in raw.splitlines():
        if not line.strip()or line.lstrip().startswith('#'):continue
        key,separator,value=line.partition('=')
        if not separator or not re.fullmatch('[A-Z][A-Z0-9_]*',key)or key in values:raise ValueError('Invalid ECS environment')
        values[key]=value
    return values


def required(expected):
    expected=expected_policy(expected)
    return {'ECS_CLUSTER':expected['clusterArn'],'ECS_ENABLE_TASK_IAM_ROLE':'true','ECS_ENABLE_TASK_IAM_ROLE_NETWORK_HOST':'false',
            'ECS_ENGINE_TASK_CLEANUP_WAIT_DURATION':'1s','ECS_INSTANCE_ATTRIBUTES':json.dumps({'atmem-document-policy':expected['policySha256']},sort_keys=True,separators=(',',':'))}


def read_optional(path):
    try:return Path(path).read_text()
    except FileNotFoundError:return ''


def atomic(path,text):
    path=Path(path);path.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
    parent=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);temporary='.atmem-'+uuid.uuid4().hex
    try:
        info=os.fstat(parent)
        if info.st_uid!=os.geteuid()or stat.S_IMODE(info.st_mode)&0o022:raise ValueError('Unsafe host configuration directory')
        try:
            info=os.stat(path.name,dir_fd=parent,follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode)or info.st_uid!=os.geteuid():raise ValueError('Refuse unowned host configuration')
        except FileNotFoundError:pass
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent)
        with os.fdopen(fd,'w')as stream:stream.write(text);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path.name,src_dir_fd=parent,dst_dir_fd=parent);os.fsync(parent)
    finally:
        try:os.unlink(temporary,dir_fd=parent)
        except FileNotFoundError:pass
        os.close(parent)


def prepare(expected,*,read=read_optional,write=atomic):
    updates=required(expected);raw=read('/etc/ecs/ecs.config');existing=environment(raw)
    if existing.get('ECS_CLUSTER')not in {None,'','default',updates['ECS_CLUSTER']}:raise ValueError('Do not adopt an existing ECS host')
    attributes=json.loads(existing.get('ECS_INSTANCE_ATTRIBUTES','{}'),object_pairs_hook=unique)
    if attributes not in [{},{'atmem-document-policy':expected['policySha256']}]:raise ValueError('Do not replace existing host ownership')
    daemon=json.loads(read('/etc/docker/daemon.json')or'{}',object_pairs_hook=unique)
    if not isinstance(daemon,dict):raise ValueError('Invalid native daemon configuration')
    daemon.update({'log-driver':'none','live-restore':False});daemon.pop('log-opts',None)
    lines=[];seen=set()
    for line in raw.splitlines():
        key=line.partition('=')[0]
        if key in updates:lines.append(key+'='+updates[key]);seen.add(key)
        else:lines.append(line)
    lines += [key+'='+value for key,value in updates.items()if key not in seen]
    write('/etc/docker/daemon.json',json.dumps(daemon,sort_keys=True,separators=(',',':'))+'\n')
    write('/etc/ecs/ecs.config','\n'.join(lines)+'\n')


def command(argv,*,absent=False):
    if argv[0]=='/usr/bin/docker':argv=[argv[0],'--host','unix:///var/run/docker.sock',*argv[1:]]
    result=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=4,
        env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C'})
    if absent and result.returncode==1:return None
    if result.returncode or len(result.stdout)>32768:raise ValueError('Native host preparation failed')
    return result.stdout.decode().strip()


def guard(expected,*,read=read_optional,run=command):
    updates=required(expected);values=environment(read('/etc/ecs/ecs.config'))
    if any(values.get(key)!=value for key,value in updates.items()):raise ValueError('ECS configuration not prepared')
    daemon=json.loads(read('/etc/docker/daemon.json'),object_pairs_hook=unique)
    if daemon.get('log-driver')!='none'or daemon.get('live-restore',False)is not False or daemon.get('bridge','docker0')!='docker0':raise ValueError('Unsafe prepared daemon')
    for field,value in [('LoggingDriver','none'),('LiveRestoreEnabled',False)]:
        if json.loads(run(['/usr/bin/docker','info','--format','{{json .'+field+'}}']))!=value:raise ValueError('Running daemon differs from prepared policy')
    options=json.loads(run(['/usr/bin/docker','info','--format','{{json .SecurityOptions}}']))
    if 'name=seccomp,profile=builtin'not in options:raise ValueError('Native seccomp is not active')
    bridge=json.loads(run(['/usr/bin/docker','network','inspect','bridge','--format','{{json .Options}}']))
    if bridge.get('com.docker.network.bridge.name')!='docker0':raise ValueError('Default bridge changed')
    for tool,destination in [('/usr/sbin/iptables','169.254.169.254/32'),('/usr/sbin/ip6tables','fd00:ec2::254/128')]:
        if run([tool,'-w','2','-S','DOCKER-USER'],absent=True)is None:run([tool,'-w','2','-N','DOCKER-USER'])
        for chain,rule in [('DOCKER-USER',['-i','docker0','-d',destination,'-j','DROP']),('FORWARD',['-j','DOCKER-USER'])]:
            for _ in range(4):
                if run([tool,'-w','2','-D',chain,*rule],absent=True)is None:break
            run([tool,'-w','2','-I',chain,'1',*rule])
        if not first_rule_matches(run([tool,'-w','2','-S','DOCKER-USER']),'DOCKER-USER',{'-i':'docker0','-d':destination,'-j':'DROP'}):raise ValueError('Metadata rule installation failed')
        if not first_rule_matches(run([tool,'-w','2','-S','FORWARD']),'FORWARD',{'-j':'DOCKER-USER'}):raise ValueError('Metadata forwarding hook installation failed')


def main():
    try:
        if os.geteuid()!=0 or len(sys.argv)!=3 or sys.argv[1]not in {'prepare','guard'}or len(sys.argv[2])>4096:raise ValueError()
        expected=json.loads(base64.b64decode(sys.argv[2],validate=True),object_pairs_hook=unique)
        (prepare if sys.argv[1]=='prepare'else guard)(expected)
        print(json.dumps({'status':'ok','phase':sys.argv[1]}))
    except Exception:raise SystemExit(2)from None


if __name__=='__main__':main()
