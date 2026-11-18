import asyncio
import contextlib
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

from atmem_review import ci
from atmem_review.adapters import Infracost,OpenRouterSemantic
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client,StdioServerParameters
from test_engine import request

ROOT=Path(__file__).resolve().parents[1]


class BoundaryTests(unittest.TestCase):
    def test_ci_reads_current_files_and_rejects_missing_or_escaped_inputs(self):
        value=request()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'architecture.md').write_text(value['rules']['content']);(root/'plan.md').write_text('Private database.')
            (root/'tfplan.json').write_text(json.dumps(value['terraform_plan']['json']))
            args=['--root',directory,'--rules','architecture.md','--artifact','plan:plan.md','--terraform-plan','tfplan.json']
            with contextlib.redirect_stdout(io.StringIO()) as out:self.assertEqual(ci.main(args),0)
            first=json.loads(out.getvalue())
            plan=value['terraform_plan']['json'];plan['planned_values']['root_module']['resources'][0]['values']['publicly_accessible']=True
            (root/'tfplan.json').write_text(json.dumps(plan))
            with contextlib.redirect_stdout(io.StringIO()) as out:self.assertEqual(ci.main(args),1)
            self.assertNotEqual(first['reviewer']['input_sha256'],json.loads(out.getvalue())['reviewer']['input_sha256'])
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(ci.main(['--root',directory,'--rules','missing.md','--artifact','plan:plan.md']),2)
                self.assertEqual(ci.main(['--root',directory,'--rules','../outside.md','--artifact','plan:plan.md']),2)

    def test_cost_executes_only_fixed_json_command_without_ambient_cloud_environment(self):
        sample={'version':'0.2','currency':'USD','totalMonthlyCost':'40','projects':[{'breakdown':{'resources':[{'name':'aws_db_instance.db','monthlyCost':'40'}]}}]}
        calls=[]
        def run(command,**kwargs):
            calls.append((command,kwargs))
            self.assertEqual(command[1],'scan');self.assertTrue(Path(command[2]).name=='tfplan.json')
            self.assertNotIn('AWS_SECRET_ACCESS_KEY',kwargs['env']);self.assertEqual(kwargs['cwd'],kwargs['env']['HOME'])
            self.assertEqual(kwargs['stdin'],__import__('subprocess').DEVNULL)
            self.assertEqual(json.loads(Path(command[2]).read_text())['format_version'],'1.2')
            kwargs['stdout'].write(json.dumps(sample).encode());kwargs['stdout'].flush()
            return SimpleNamespace(returncode=0)
        with patch.dict(os.environ,{'INFRACOST_CLI_AUTHENTICATION_TOKEN':'dummy-token','AWS_SECRET_ACCESS_KEY':'private-host-data'}),patch('atmem_review.adapters.subprocess.run',side_effect=run):
            result=Infracost(sys.executable)(request()['terraform_plan']['json'],'USD')
        self.assertEqual(result['monthly_total'],40);self.assertEqual(len(calls),1)
        self.assertFalse(Path(calls[0][1]['cwd']).exists())

    def test_model_egress_filters_plain_source_secrets_and_never_receives_terraform_plan(self):
        value=request();value['artifacts'][0]['content']='password = "super-secret-password"'
        with patch.dict(os.environ,{'ATMEM_REVIEW_OPENROUTER_API_KEY':'dummy','ATMEM_REVIEW_OPENROUTER_MODEL':'configured-model'}),patch('atmem_review.adapters.urllib.request.build_opener') as opener:
            with self.assertRaises(ValueError):OpenRouterSemantic()(value)
            opener.assert_not_called()
        value['artifacts'][0]['content']='Use a private database.'
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,_):return json.dumps({'choices':[{'message':{'content':'{"violations": [], "verified_adrs": []}'}}]}).encode()
        class Opener:
            def open(self,req,timeout):
                body=json.loads(req.data);selected=json.loads(body['messages'][1]['content'])
                self_test.assertNotIn('terraform_plan',selected);self_test.assertNotIn('tools',body)
                self_test.assertEqual(req.full_url,'https://openrouter.ai/api/v1/chat/completions')
                return Response()
        self_test=self
        with patch.dict(os.environ,{'ATMEM_REVIEW_OPENROUTER_API_KEY':'dummy','ATMEM_REVIEW_OPENROUTER_MODEL':'configured-model'}),patch('atmem_review.adapters.urllib.request.build_opener',return_value=Opener()):
            self.assertEqual(OpenRouterSemantic()(value)['violations'],[])


class StdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_stdio_sdk_handshake_tool_schema_and_read_only_call(self):
        with tempfile.TemporaryDirectory() as directory:
            params=StdioServerParameters(command=sys.executable,args=['-m','atmem_review.mcp_server'],
                cwd=directory,env={'PATH':os.defpath,'PYTHONPATH':str(ROOT/'src'),'PYTHONDONTWRITEBYTECODE':'1'})
            async with stdio_client(params) as (reader,writer):
                async with ClientSession(reader,writer,read_timeout_seconds=20) as session:
                    initialized=await session.initialize();self.assertEqual(initialized.server_info.name,'atmem-architect')
                    tools=(await session.list_tools()).tools
                    self.assertEqual([t.name for t in tools],['review_plan']);self.assertTrue(tools[0].annotations.read_only_hint)
                    value=request();value['artifacts'][0]['path']='../../private.env'
                    result=await session.call_tool('review_plan',value)
                    self.assertFalse(result.is_error);self.assertEqual(result.structured_content['verdict'],'pass')
                    bad=await session.call_tool('review_plan',{'artifacts':[],'rules':{'content':'invalid'}})
                    self.assertTrue(bad.is_error)
            self.assertEqual(list(Path(directory).iterdir()),[])


class StrictInputTests(unittest.TestCase):
    def test_json_duplicates_and_nonfinite_values_are_rejected(self):
        from atmem_review.cli import strict_json
        for text in ['{"key": 1, "key": 2}', '{"number": NaN}']:
            with self.assertRaises(ValueError):strict_json(text)


class MalformedPlanTests(unittest.TestCase):
    def test_invalid_nested_plan_has_no_verdict_and_exit_two(self):
        from atmem_review.cli import main
        value=request();value['terraform_plan']['json']['resource_changes']=['invalid-private-source']
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'request.json';path.write_text(json.dumps(value))
            with contextlib.redirect_stdout(io.StringIO()) as out,contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(main([str(path)]),2)
            self.assertEqual(out.getvalue(),'');self.assertNotIn('invalid-private-source',err.getvalue())
