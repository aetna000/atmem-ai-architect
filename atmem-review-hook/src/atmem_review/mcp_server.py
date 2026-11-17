"""MCP stdio, one read-only tool, fixed operator egress configuration."""
import argparse
import asyncio
import json
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from . import __version__
from .engine import INPUT,OUTPUT,review_plan
from .adapters import Infracost,OpenRouterSemantic


def build_server(*,allow_cost=False,allow_model=False):
    async def list_tools(context,params):
        return types.ListToolsResult(tools=[types.Tool(name='review_plan',description='Review supplied architecture artifacts and Terraform JSON against policy. No Terraform execution or cloud access.',
            inputSchema=INPUT,outputSchema=OUTPUT,annotations=types.ToolAnnotations(readOnlyHint=True,destructiveHint=False,idempotentHint=not (allow_cost or allow_model),openWorldHint=allow_cost or allow_model))])
    async def call_tool(context,params):
        if params.name!='review_plan':return types.CallToolResult(isError=True,content=[types.TextContent(type='text',text='Unknown tool')])
        try:
            result=await asyncio.to_thread(review_plan,params.arguments or {},cost_engine=Infracost() if allow_cost else None,
                                           semantic_engine=OpenRouterSemantic() if allow_model else None)
            return types.CallToolResult(content=[types.TextContent(type='text',text=json.dumps(result,allow_nan=False))],structuredContent=result)
        except (ValueError,TypeError,KeyError,AttributeError,IndexError,OverflowError,RecursionError):
            return types.CallToolResult(isError=True,content=[types.TextContent(type='text',text='Invalid or unsupported review input; no verdict issued.')])
    return Server('atmem-architect',version=__version__,on_list_tools=list_tools,on_call_tool=call_tool)


async def serve(args):
    server=build_server(allow_cost=args.allow_cost_egress,allow_model=args.allow_model_egress)
    async with stdio_server() as (reader,writer):
        await server.run(reader,writer,server.create_initialization_options())


def main():
    parser=argparse.ArgumentParser(description='AtMem read-only architecture reviewer over MCP stdio.')
    parser.add_argument('--allow-cost-egress',action='store_true')
    parser.add_argument('--allow-model-egress',action='store_true')
    args=parser.parse_args()
    asyncio.run(serve(args))


if __name__=='__main__':main()
