"""Real SDK connection to an installed package outside the source checkout."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import tempfile
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client,StdioServerParameters


async def run(args):
    payload=json.loads(Path(args.sample).read_text())
    with tempfile.TemporaryDirectory() as directory:
        params=StdioServerParameters(command=str(Path(args.python).absolute()),args=['-I','-m','atmem_review.mcp_server'],
                                     cwd=directory,env={'PATH':os.defpath,'PYTHONDONTWRITEBYTECODE':'1'})
        async with stdio_client(params) as (reader,writer):
            async with ClientSession(reader,writer,read_timeout_seconds=20) as session:
                await session.initialize()
                assert [t.name for t in (await session.list_tools()).tools]==['review_plan']
                result=await session.call_tool('review_plan',payload)
                assert not result.is_error and result.structured_content['verdict']=='fail'
                assert {'REGION-001','NET-001','NET-002'}<={v['rule_id'] for v in result.structured_content['violations']}
                assert result.structured_content['cost']['status']=='skipped'
        assert not list(Path(directory).iterdir())
    print(json.dumps({'status':'passed','transport':'real_installed_mcp_stdio','verdict':'fail_expected','cloudCalls':0,'modelCalls':0,'livePricing':False}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--python',required=True);parser.add_argument('--sample',required=True)
    asyncio.run(run(parser.parse_args()))
