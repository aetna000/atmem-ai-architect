"""Fixed SSM host inspection. Standard library only; no document or secret input."""
import base64
import json
from pathlib import Path
import re
import subprocess
import sys


def run(argv):
    value=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                         timeout=4,check=True,env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C'})
    if len(value.stdout)>32768:raise ValueError('Invalid host observation')
    return value.stdout.decode().strip()


def inspect_host(expected,*,read=lambda name:Path(name).read_text(),command=run):
    if (not isinstance(expected,dict)or set(expected)!={'format','clusterArn','policySha256'}or
        expected['format']!='enterprise-aws-host-policy-v1'or
        not isinstance(expected['policySha256'],str)or not re.fullmatch('[0-9a-f]{64}',expected['policySha256'])or
        not isinstance(expected['clusterArn'],str)or not re.fullmatch(r'arn:aws:ecs:[a-z]{2}-[a-z]+-[1-9]:[0-9]{12}:cluster/[A-Za-z0-9_-]{1,255}',expected['clusterArn'])):
        raise ValueError('Use the exact owned host policy')
    # Parse values as inert text. Never source a host config into a shell.
    values={}
    for line in read('/etc/ecs/ecs.config').splitlines():
        if not line.strip()or line.lstrip().startswith('#'):continue
        key,separator,value=line.partition('=')
        if not separator or key in values:raise ValueError('Ambiguous ECS configuration')
        values[key]=value
    if (values.get('ECS_CLUSTER')!=expected['clusterArn']or
        values.get('ECS_ENABLE_TASK_IAM_ROLE')!='true'or
        values.get('ECS_ENGINE_TASK_CLEANUP_WAIT_DURATION')!='1s'or
        values.get('ECS_ENABLE_TASK_IAM_ROLE_NETWORK_HOST')!='false'):
        raise ValueError('ECS host policy changed')
    attributes=json.loads(values.get('ECS_INSTANCE_ATTRIBUTES','{}'))
    if attributes!={'atmem-document-policy':expected['policySha256']}:raise ValueError('Host policy selection changed')
    daemon=json.loads(read('/etc/docker/daemon.json'))
    if (daemon.get('log-driver')!='none'or daemon.get('live-restore',False)is not False or daemon.get('bridge','docker0')!='docker0'):
        raise ValueError('Unsafe daemon logging, network or task persistence')
    if json.loads(command(['/usr/bin/docker','info','--format','{{json .LoggingDriver}}']))!='none':raise ValueError('Actual daemon logging changed')
    if json.loads(command(['/usr/bin/docker','info','--format','{{json .LiveRestoreEnabled}}']))is not False:raise ValueError('Native live restore is active')
    options=json.loads(command(['/usr/bin/docker','info','--format','{{json .SecurityOptions}}']))
    if not isinstance(options,list)or 'name=seccomp,profile=builtin'not in options:
        raise ValueError('Native seccomp is not active')
    bridge=json.loads(command(['/usr/bin/docker','network','inspect','bridge','--format','{{json .Options}}']))
    if bridge.get('com.docker.network.bridge.name')!='docker0':raise ValueError('Actual default bridge changed')
    native_env=json.loads(command(['/usr/bin/docker','inspect','ecs-agent','--format','{{json .Config.Env}}']))
    if not isinstance(native_env,list)or any(not isinstance(v,str)for v in native_env):raise ValueError('Native ECS agent configuration unavailable')
    native={}
    for entry in native_env:
        key,separator,value=entry.partition('=')
        if not separator or key in native:raise ValueError('Ambiguous native ECS environment')
        native[key]=value
    for key in ['ECS_CLUSTER','ECS_ENABLE_TASK_IAM_ROLE','ECS_ENGINE_TASK_CLEANUP_WAIT_DURATION','ECS_ENABLE_TASK_IAM_ROLE_NETWORK_HOST','ECS_INSTANCE_ATTRIBUTES']:
        if native.get(key)!=values[key]:raise ValueError('Running ECS agent differs from host policy')
    # Both paths are fixed, read-only probes. A plain TCP bridge must not expose
    # instance-profile credentials to the transfer containers.
    for destination in ['169.254.169.254/32','fd00:ec2::254/128']:
        tool='/usr/sbin/iptables'if ':'not in destination else'/usr/sbin/ip6tables'
        rules=command([tool,'-w','2','-S','DOCKER-USER']).splitlines()
        active=[value for value in rules if value.startswith('-A ')]
        if not active or active[0]!='-A DOCKER-USER -i docker0 -d '+destination+' -j DROP':raise ValueError('IMDS rule is missing or shadowed')
    boot=read('/proc/sys/kernel/random/boot_id').strip()
    if not re.fullmatch('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',boot):raise ValueError('Invalid native boot identity')
    return {'format':'enterprise-aws-host-observation-v1','policySha256':expected['policySha256'],
            'clusterArn':expected['clusterArn'],'bootId':boot}


def main():
    try:
        if len(sys.argv)!=2 or len(sys.argv[1])>4096:raise ValueError()
        expected=json.loads(base64.b64decode(sys.argv[1],validate=True))
        print(json.dumps(inspect_host(expected),separators=(',',':')))
    except Exception:raise SystemExit(2)from None


if __name__=='__main__':main()
