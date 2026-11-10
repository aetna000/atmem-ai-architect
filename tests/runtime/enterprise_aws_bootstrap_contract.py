"""Dedicated-host bootstrap contracts; filesystem is real, daemon/firewall are fixtures."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src/runtime'))
from enterprise_aws_host_bootstrap import atomic,command,environment,guard,prepare,required
from enterprise_aws_host_probe import first_rule_matches

EXPECTED={'format':'enterprise-aws-host-policy-v1',
          'clusterArn':'arn:aws:ecs:ap-southeast-2:123456789012:cluster/document-parser',
          'policySha256':'a'*64}


class Preparation(unittest.TestCase):
    def setUp(self):self.files={};self.writes=[]
    def write(self,path,value):self.files[path]=value;self.writes.append(path)
    def prepare(self):prepare(EXPECTED,read=lambda path:self.files.get(path,''),write=self.write)
    def test_new_host_configuration_is_inert_and_idempotent(self):
        self.files={'/etc/ecs/ecs.config':'# retained\nECS_CLUSTER=default\nECS_LOGLEVEL=warn\n',
                    '/etc/docker/daemon.json':json.dumps({'storage-driver':'overlay2','log-driver':'json-file','log-opts':{'max-size':'1m'}})}
        self.prepare();first=copy.deepcopy(self.files);self.prepare();self.assertEqual(first,self.files)
        self.assertIn('# retained',first['/etc/ecs/ecs.config'])
        self.assertEqual(environment(first['/etc/ecs/ecs.config']),{**required(EXPECTED),'ECS_LOGLEVEL':'warn'})
        self.assertEqual(json.loads(first['/etc/docker/daemon.json']),{'storage-driver':'overlay2','log-driver':'none','live-restore':False})
    def test_foreign_cluster_or_attributes_are_not_adopted(self):
        for raw in ['ECS_CLUSTER=another-cluster','ECS_INSTANCE_ATTRIBUTES={"owner":"other"}']:
            with self.subTest(raw=raw):
                self.files={'/etc/ecs/ecs.config':raw}
                with self.assertRaises(ValueError):self.prepare()
                self.assertEqual(self.writes,[])
    def test_ambiguous_or_malformed_configuration_fails_before_writes(self):
        for path,raw in [('/etc/ecs/ecs.config','ECS_CLUSTER=default\nECS_CLUSTER=default'),
                         ('/etc/ecs/ecs.config','export ECS_CLUSTER=default'),
                         ('/etc/docker/daemon.json','{"bridge":"docker0","bridge":"other"}'),
                         ('/etc/docker/daemon.json','[]')]:
            with self.subTest(raw=raw):
                self.files={path:raw}
                with self.assertRaises(ValueError):self.prepare()
                self.assertEqual(self.writes,[])
    def test_untrusted_expected_metadata_is_never_written(self):
        for changed in [{**EXPECTED,'secret':'PRIVATE'}, {**EXPECTED,'clusterArn':'$(touch /tmp/untrusted)'},
                        {**EXPECTED,'policySha256':'invalid'}]:
            with self.assertRaises(ValueError):prepare(changed,read=lambda path:'',write=self.write)
        self.assertEqual(self.writes,[])


class AtomicConfiguration(unittest.TestCase):
    def test_real_write_replaces_owned_file_with_private_permissions(self):
        with tempfile.TemporaryDirectory()as directory:
            path=Path(directory)/'ecs.config';path.write_text('before');atomic(path,'after\n')
            self.assertEqual(path.read_text(),'after\n');self.assertEqual(path.stat().st_mode&0o777,0o600)
            self.assertEqual([value.name for value in Path(directory).iterdir()],['ecs.config'])
    def test_symlink_target_and_writable_parent_are_rejected(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);target=root/'target';target.write_text('preserve');link=root/'ecs.config';link.symlink_to(target)
            with self.assertRaises(ValueError):atomic(link,'replace')
            self.assertEqual(target.read_text(),'preserve');link.unlink();os.chmod(root,0o777)
            with self.assertRaises(ValueError):atomic(link,'replace')
            self.assertFalse(link.exists());os.chmod(root,0o700)


class Firewall:
    """Model rule ordering and native -S rendering, including an unrelated rule."""
    def __init__(self):
        self.calls=[];self.bad=None
        self.rules={tool:{'FORWARD':[('-j','ACCEPT')]}for tool in ['/usr/sbin/iptables','/usr/sbin/ip6tables']}
    def __call__(self,argv,*,absent=False):
        self.calls.append(argv)
        if argv[0]=='/usr/bin/docker':
            if argv[1]=='network':return json.dumps({'com.docker.network.bridge.name':'changed'if self.bad=='bridge'else'docker0'})
            field=argv[-1]
            if 'LoggingDriver'in field:return json.dumps('json-file'if self.bad=='logging'else'none')
            if 'LiveRestoreEnabled'in field:return json.dumps(self.bad=='restore')
            return json.dumps(['name=seccomp,profile=unconfined'if self.bad=='seccomp'else'name=seccomp,profile=builtin'])
        tool,_,_,operation,chain,*rule=argv;chains=self.rules[tool]
        if operation=='-S':
            if chain not in chains:
                if absent:return None
                raise ValueError('Missing chain')
            lines=['-N '+chain]
            for entry in chains[chain]:
                # Native iptables canonicalizes -d before -i.
                if len(entry)==6 and entry[:2]==('-i','docker0'):entry=entry[2:4]+entry[:2]+entry[4:]
                lines.append('-A '+chain+' '+' '.join(entry))
            return '\n'.join(lines)
        if operation=='-N':chains[chain]=[];return ''
        if operation=='-D':
            try:chains[chain].remove(tuple(rule));return ''
            except ValueError:
                if absent:return None
                raise
        if operation=='-I':
            if self.bad=='installation':return ''
            self.assert_position(rule.pop(0));chains[chain].insert(0,tuple(rule));return ''
        raise AssertionError(argv)
    @staticmethod
    def assert_position(value):
        if value!='1':raise AssertionError(value)


class Guard(unittest.TestCase):
    def setUp(self):
        self.files={};prepare(EXPECTED,read=lambda path:'',write=self.files.__setitem__);self.firewall=Firewall()
    def guard(self):guard(EXPECTED,read=self.files.__getitem__,run=self.firewall)
    def test_both_native_families_have_first_position_rules_without_flushing(self):
        self.guard();first=copy.deepcopy(self.firewall.rules);self.guard();self.assertEqual(first,self.firewall.rules)
        for tool,destination in [('/usr/sbin/iptables','169.254.169.254/32'),('/usr/sbin/ip6tables','fd00:ec2::254/128')]:
            self.assertEqual(self.firewall.rules[tool]['FORWARD'],[('-j','DOCKER-USER'),('-j','ACCEPT')])
            self.assertEqual(self.firewall.rules[tool]['DOCKER-USER'],[('-i','docker0','-d',destination,'-j','DROP')])
        self.assertFalse(any('-F'in value or '-X'in value for value in self.firewall.calls))
    def test_daemon_drift_fails_before_firewall_mutation(self):
        for bad in ['logging','restore','seccomp','bridge']:
            with self.subTest(bad=bad):
                self.firewall=Firewall();self.firewall.bad=bad
                with self.assertRaises(ValueError):self.guard()
                self.assertFalse(any(value[0].endswith('tables')for value in self.firewall.calls))
    def test_configuration_drift_and_failed_rule_installation_fail_closed(self):
        original=self.files['/etc/ecs/ecs.config'];self.files['/etc/ecs/ecs.config']=original.replace('1s','3h')
        with self.assertRaises(ValueError):self.guard()
        self.assertEqual(self.firewall.calls,[]);self.files['/etc/ecs/ecs.config']=original
        self.firewall.bad='installation'
        with self.assertRaisesRegex(ValueError,'installation failed'):self.guard()
    def test_native_commands_use_local_socket_and_bounded_scrubbed_process(self):
        seen=[]
        def run(argv,**options):seen.append((argv,options));return subprocess.CompletedProcess(argv,0,stdout=b'"none"')
        with patch('enterprise_aws_host_bootstrap.subprocess.run',side_effect=run):
            self.assertEqual(command(['/usr/bin/docker','info']),'"none"')
        self.assertEqual(seen[0][0][:3],['/usr/bin/docker','--host','unix:///var/run/docker.sock'])
        self.assertEqual(seen[0][1]['timeout'],4);self.assertNotIn('DOCKER_HOST',seen[0][1]['env'])


class RuleSemantics(unittest.TestCase):
    def test_equivalent_destination_and_option_order_are_accepted(self):
        expected={'-i':'docker0','-d':'169.254.169.254/32','-j':'DROP'}
        self.assertTrue(first_rule_matches('-A DOCKER-USER -d 169.254.169.254 -i docker0 -j DROP','DOCKER-USER',expected))
    def test_shadowing_narrower_scope_duplicates_and_other_chains_are_rejected(self):
        expected={'-i':'docker0','-d':'169.254.169.254/32','-j':'DROP'}
        good='-A DOCKER-USER -d 169.254.169.254/32 -i docker0 -j DROP'
        for rule in ['-A DOCKER-USER -j ACCEPT\n'+good,good+' -p tcp',good+' -i docker0',
                     good.replace('DOCKER-USER','OTHER'),good.replace('/32','/24'),good.replace('DROP','RETURN')]:
            with self.subTest(rule=rule):self.assertFalse(first_rule_matches(rule,'DOCKER-USER',expected))


if __name__=='__main__':unittest.main(verbosity=2)
