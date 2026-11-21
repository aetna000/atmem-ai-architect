"""One isolated Copilot SDK request using the official installed CLI and native sign-in."""
import asyncio, json, sys
from copilot import CopilotClient, RuntimeConnection

async def main():
    config=json.load(sys.stdin)
    async with CopilotClient(connection=RuntimeConnection.for_stdio(path=config['cli'],args=['--disable-builtin-mcps','--no-custom-instructions','--no-auto-update','--disable-client-telemetry']),working_directory=config['cwd'],use_logged_in_user=True,log_level='none') as client:
        async with await client.create_session(model=None if config['model'] in ('auto','default') else config['model'],available_tools=[],tools=[],system_message={'mode':'replace','content':config['system']},skip_custom_instructions=True,enable_file_hooks=False,enable_skills=False,enable_config_discovery=False,enable_host_git_operations=False,enable_session_store=False,enable_session_telemetry=False,mcp_servers={},disabled_mcp_servers=['github-mcp-server','githubiq'],interactive_user=False) as session:
            attachments=[{'type':'blob','data':i['data'],'mimeType':i['mime'],'displayName':i['name']} for i in config.get('images',[])]
            result=await session.send_and_wait(config['prompt'],attachments=attachments or None,response_schema=config['schema'],timeout=130)
            if not result:raise RuntimeError('No assistant response')
            content=getattr(result.data,'content',None)
            if not content:raise RuntimeError('No assistant content')
            print(content)

if __name__=='__main__':asyncio.run(main())
