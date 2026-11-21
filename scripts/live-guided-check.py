"""Opt-in synthetic native-account architecture check; incurs model usage, no cloud operations."""
import asyncio,json,sys
from pathlib import Path
from unittest.mock import AsyncMock
from server.architect import AtMemArchitect
from server.contracts import ChatRequest

async def main():
    provider=sys.argv[1] if len(sys.argv)>1 else 'codex'
    architect=AtMemArchitect()
    project={'version':1,'revision':1,'name':'Synthetic HR assistant','provider':'tools','requirements':'Staff ask questions about approved HR policy PDFs. Cite sources and respect document access.','nodes':[],'edges':[]}
    first=await architect.call(ChatRequest(provider=provider,model='default',effort='low',project=project,message='Sketch an internal assistant for staff questions about approved HR policy PDFs. We need citations and document access controls. Ask the next useful scope question. This is a synthetic test; no deployment.',context=[{'type':'discovery','id':'guided-journey','text':'Current stage: sketch and document. Draw from the idea and ask one scope question; cloud not chosen yet.'}]),AsyncMock(return_value=False))
    assert first.proposal and first.proposal.next.nodes, 'First turn did not sketch the idea'
    project=first.proposal.next.model_dump(exclude_none=True);project['revision']=2
    second=await architect.call(ChatRequest(provider=provider,model='default',effort='low',project=project,message='Use Azure, with data in Australia East (Sydney). Translate this sketch into actual Azure services and explicit connections. Preserve component IDs where practical. Populate data.service with each actual service name and config.region with australiaeast (global only for a global identity service). Describe each role and ask one refinement question. Do not deploy or claim regional availability was verified.',context=[{'type':'discovery','id':'guided-journey','text':'Current stage: concrete Azure architecture. Working scope reviewed. Use actual services such as Azure Blob Storage, Azure AI Search, Azure OpenAI, Azure Container Apps, Microsoft Entra ID, Azure Key Vault. Region and integration verification remain review tasks.'}]),AsyncMock(return_value=False))
    assert second.proposal, 'Second turn did not translate the concept'
    nodes=[n for n in second.proposal.next.nodes if n.data.kind!='note' and n.data.origin!='existing']
    assert nodes and all(n.data.provider=='azure' and n.data.service for n in nodes), 'Generic/unmapped cloud components remain'
    assert second.proposal.next.edges, 'No service connections'
    out=Path('/tmp/forma-qa/journey');out.mkdir(parents=True,exist_ok=True)
    (out/'native-account-journey.json').write_text(json.dumps({'sketch':first.model_dump(exclude_none=True),'cloudArchitecture':second.model_dump(exclude_none=True)},indent=2))
    print(json.dumps({'provider':provider,'sketchBlocks':len(first.proposal.next.nodes),'services':[n.data.service for n in nodes],'connections':len(second.proposal.next.edges),'nextQuestion':second.message,'scope':'Real native model responses; no cloud compatibility or deployment validation'}))
if __name__=='__main__':asyncio.run(main())
