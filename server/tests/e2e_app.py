"""Browser fixture only. Real AtMem, real app routes; deterministic model/prices.
Never imported by scripts/local.mjs or production server.app startup.
"""
import asyncio
import copy
from server.app import app
import server.app as app_module
from server.contracts import ArchitectResponse, ToolRequest, OptionAssessment, Scores, UsageUpdate, RequirementUpdate, DecisionUpdate
import server.agent_runtime as runtime_module
import server.memory_routes as routes_module
from server.memory_service import service


def quote(provider,region):
    if provider in {'gcp','ibm'}:return {'available':False,'provider':provider,'region':region,'reason':'Fixture requires an exact sourced quote; no rate substituted','sourceUrl':'https://example.invalid/test-quote'}
    return {'available':True,'provider':provider,'region':region,'price':0.025 if provider=='aws' else 0.02,'currency':'USD','unit':'GB-month','service':'Synthetic QA storage meter','source':'AWS public Price List' if provider=='aws' else 'Azure Retail Prices API','url':'https://pricing.us-east-1.amazonaws.com/fixture' if provider=='aws' else 'https://prices.azure.com/fixture','date':'2026-11-05','coverage':'Synthetic test rate only; not a provider quote','tierLimit':51200}
runtime_module.storage_quote=quote
routes_module.storage_quote=quote
app_module.capabilities=lambda:{'claude-code':{'installed':True,'available':True,'signedIn':True}}
app_module.models=lambda provider:[{'id':'fixture-model','name':'Fixture model','efforts':[]}]

def node(id,label,kind,provider='tools',region='To be selected',x=0):
    return {'id':id,'type':'resource','position':{'x':x,'y':100},'data':{'label':label,'kind':kind,'provider':provider,'description':label,'origin':'proposed','config':{'region':region,'classification':'Internal','timeout':5000}}}

class FixtureArchitect:
    keys={}
    async def call(self,request,disconnected,runtime=None):
        await asyncio.sleep(.08)
        msg=request.message.lower();runtime=runtime or {};p=request.project.model_dump(exclude_none=True)
        if msg.startswith('connection check'):return ArchitectResponse(message='Fixture connection ready.')
        if 'compare' in msg and 'optionassessment' in msg:
            return ArchitectResponse(message='All four clouds can support this design; existing systems and residency should drive the choice. Which cloud agreement do you already have?',optionAssessment=[OptionAssessment(provider=provider,scores=Scores(cost=3,risk=3,scalability=4,security=4),rationale=f'Provisional {provider} option for the current document assistant; exact cost and region still need verification.') for provider in ['current','aws','azure','gcp','ibm']])
        if request.origin=='document':
            import re
            match=re.search(r'Requirement (\S+)(?: \(selected text: .*?\))? — comment: (.+)',request.message)
            return ArchitectResponse(message='I proposed new wording from your comment; review it in the document. What else should we clarify?',requirementUpdates=[RequirementUpdate(id=match[1],statement='Only HR managers may retrieve policy documents.',sourceText=match[2])])
        if request.origin=='preview':
            provider='azure' if 'azure' in msg else 'gcp' if 'google' in msg else 'ibm' if 'ibm' in msg else 'aws'
            labels={'aws':{'files':'Amazon S3','assistant':'Amazon Bedrock','chat':'Amazon API Gateway'},'azure':{'files':'Azure Blob Storage','assistant':'Azure OpenAI','chat':'Azure App Service'},'gcp':{'files':'Google Cloud Storage','assistant':'Vertex AI','chat':'Cloud Run'},'ibm':{'files':'IBM Cloud Object Storage','assistant':'watsonx.ai','chat':'IBM Cloud Code Engine'}}
            p['provider']=provider
            for n in p['nodes']:
                if n['data']['kind']=='note':continue
                n['data']['provider']=provider;n['data']['label']=labels[provider].get(n['id'],n['data']['label']);n['data']['service']=n['data']['label']
            return ArchitectResponse(message='Here is an alternative service architecture. Which country should we plan for?',proposal={'baseRevision':p['revision'],'title':'Preview service architecture','body':'Alternative only; regional availability unverified.','next':p})
        if request.message=='Use AWS for this project.':
            return ArchitectResponse(message='We can explore AWS. Which country should the data stay in?',decisionUpdates=[DecisionUpdate(subject='platform.cloud',value='aws',sourceText=request.message)])
        if 'ask which country' in msg:
            return ArchitectResponse(message='Country and residency shape our regional options. Which country should the data stay in?')
        if request.origin=='canvas':
            return ArchitectResponse(message='I can see your edits and comments in our shared diagram. Which of these constraints matters most for the first release?')
        if request.stage=='estimate' and not runtime.get('toolResults'):
            provider=request.project.provider if request.project.provider!='tools' else 'aws'
            region=next((n.data.config.region for n in request.project.nodes if n.data.provider==provider),'ap-southeast-2')
            return ArchitectResponse(message='Checking the appropriate provider price source.',toolRequests=[ToolRequest(name='pricing.lookup',query='{"provider":"'+provider+'","region":"'+region+'"}')])
        if 'only the hr team' in msg:
            target=next((c.id for c in request.context if c.type=='requirement' and c.id=='drv-data-access'),'drv-data-access')
            return ArchitectResponse(message='Only the HR team should access these documents. Which sign-in system does the team already use?',requirementUpdates=[RequirementUpdate(id=target,statement='Only the HR team may access the documents and answers.',sourceText=request.message)])
        if 'remember about me:' in msg:return ArchitectResponse(message='Your confirmed preference is recorded. Which part of our design should we work on next?')
        if 'what do you remember' in msg or 'which region did' in msg:
            if not runtime.get('toolResults'):return ArchitectResponse(message='Looking up relevant confirmed context.',toolRequests=[ToolRequest(name='memory.lookup',query='region explanation preferences')])
            content=' '.join(r['text'] for r in runtime.get('memory',[]))
            return ArchitectResponse(message=(content or 'No relevant confirmed memory was supplied.')+' What should we refine next?')
        if '3,000 tokens' in msg:
            return ArchitectResponse(message='We can use 3,000 tokens per request in the working estimate. How many questions do you expect each month?',usageUpdates=[UsageUpdate(key='tokens_per_request',value=3000,sourceText='3,000 tokens')])
        if request.stage=='estimate':return ArchitectResponse(message='The source covers base storage only; model and other charges are still open. How many questions should we plan for each month?')
        if 'sydney' in msg or 'melbourne' in msg or 'use azure' in msg or 'use google' in msg or 'use ibm' in msg:
            provider='azure' if 'azure' in msg else 'gcp' if 'google' in msg else 'ibm' if 'ibm' in msg else 'aws'
            region={'aws':'ap-southeast-4' if 'melbourne' in msg else 'ap-southeast-2','azure':'australiaeast','gcp':'australia-southeast1','ibm':'au-syd'}[provider]
            p['provider']=provider
            for n in p['nodes']:
                if n['data']['kind']=='note':continue
                n['data']['provider']=provider;n['data']['config']['region']=region
                labels={'aws':{'files':'Amazon S3','assistant':'Amazon Bedrock','chat':'Amazon API Gateway'},'azure':{'files':'Azure Blob Storage','assistant':'Azure OpenAI','chat':'Azure App Service'},'gcp':{'files':'Google Cloud Storage','assistant':'Vertex AI','chat':'Cloud Run'},'ibm':{'files':'IBM Cloud Object Storage','assistant':'watsonx.ai','chat':'IBM Cloud Code Engine'}}
                n['data']['label']=labels[provider].get(n['id'],n['data']['label']);n['data']['service']=n['data']['label']
            updates=[DecisionUpdate(subject='platform.cloud',value=provider,sourceText=request.message),DecisionUpdate(subject='cloud.region',value=region,sourceText=request.message)]
            return ArchitectResponse(message='We can use that cloud and region for this design. How many people will use it?',decisionUpdates=updates,proposal={'baseRevision':p['revision'],'title':'Apply your cloud and region choice','body':'Based on your explicit choice.','next':p})
        if not any(n['data']['kind']!='note' for n in p['nodes']):
            notes=[n for n in p['nodes'] if n['data']['kind']=='note']
            p['nodes']=[node('files','Company policy documents','source',x=0),node('assistant','Policy question answering','agent',x=300),node('chat','Staff chat interface','output',x=600)]+notes
            p['edges']=[{'id':'read','source':'files','target':'assistant','type':'smoothstep','label':'policy documents'},{'id':'answer','source':'assistant','target':'chat','type':'smoothstep','label':'answer'}]
            return ArchitectResponse(message='Here is a first sketch for your staff document assistant. Where do the policy documents live?',proposal={'baseRevision':p['revision'],'title':'Sketch your staff document assistant','body':'Drawn from your stated idea; no deployment or test is claimed.','next':p})
        return ArchitectResponse(message='We can refine this design together. Who needs access to these documents?')

app_module.ARCHITECT=FixtureArchitect()
_original_worker=None
@app.post('/test/memory-outage')
async def outage(body:dict):
    global _original_worker
    memory=service()
    if _original_worker is None:_original_worker=memory.worker
    memory.worker='/unavailable/atmem' if body.get('down') else _original_worker
    return {'down':bool(body.get('down'))}
