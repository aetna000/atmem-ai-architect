"""Strict contracts for the local agent boundary; no executable config accepted."""
from typing import Literal, Annotated
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, StrictBool, StrictFloat, StrictInt, StrictStr, field_validator, model_validator

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')

class Position(Strict):
    x:float=Field(ge=-100000,le=100000,allow_inf_nan=False)
    y:float=Field(ge=-100000,le=100000,allow_inf_nan=False)

class OutputField(Strict):
    name:StrictStr=Field(pattern=r'^[a-z][a-zA-Z0-9_]{0,39}$')
    type:Literal['string','boolean','number']
    description:StrictStr=Field(min_length=1,max_length=300)
    values:list[StrictStr]|None=Field(default=None,min_length=1,max_length=30)
    maxLength:StrictInt|None=Field(default=None,ge=1,le=4096)
    @model_validator(mode='after')
    def constraints(self):
        if not self.description.strip():raise ValueError('Output field description is empty')
        if self.values is not None and (self.type!='string' or len(set(self.values))!=len(self.values) or any(not v or len(v)>100 for v in self.values)):raise ValueError('Invalid string enumeration')
        if self.maxLength is not None and self.type!='string':raise ValueError('Only strings have maxLength')
        if self.values and any(len(v)>(self.maxLength or 4096) for v in self.values):raise ValueError('Enumeration values exceed the field length limit')
        return self

class OutputContract(Strict):
    instruction:StrictStr=Field(min_length=1,max_length=2000)
    fields:list[OutputField]=Field(min_length=1,max_length=24)
    @model_validator(mode='after')
    def constraints(self):
        if not self.instruction.strip():raise ValueError('Instruction is empty')
        if len({f.name for f in self.fields})!=len(self.fields):raise ValueError('Duplicate output fields')
        return self

class Configuration(Strict):
    outputContract:OutputContract|None=None
    region:str=Field(default='To be selected',max_length=100)
    classification:Literal['Public','Internal','Confidential']='Internal'
    timeout:int=Field(default=5000,ge=100,le=60000)
    memoryMb:StrictInt|None=Field(default=None,ge=128,le=10240)
    functionTimeoutSeconds:StrictInt|None=Field(default=None,ge=1,le=900)
    concurrency:StrictInt|None=Field(default=None,ge=1,le=1000)
    maxInputBytes:StrictInt|None=Field(default=None,ge=1,le=1000000)
    maxOutputTokens:StrictInt|None=Field(default=None,ge=1,le=4096)
    modelId:StrictStr|None=Field(default=None,max_length=150,pattern=r'^[a-z0-9][a-z0-9.-]*:[0-9]+$')
    logRetentionDays:Literal[1,3,5,7,14,30,60,90,120,150,180,365,400,545,731,1096,1827,2192,2557,2922,3288,3653]|None=None

class Measure(Strict):
    label:str=Field(min_length=1,max_length=150)
    path:str=Field(pattern=r'^[A-Za-z_][A-Za-z0-9_.]{0,79}$')
    op:Literal['>=','<=','==']
    target:StrictBool|StrictInt|StrictFloat|StrictStr
    @field_validator('target')
    @classmethod
    def short(cls,value):
        if isinstance(value,str) and len(value)>100:raise ValueError('Target too long')
        return value

class Data(Strict):
    label:str=Field(max_length=16000)
    kind:Literal['source','predict','agent','guard','output','tool','resource','stream','history','features','train','registry','monitor','note']
    provider:Literal['aws','azure','gcp','ibm','tools']
    description:str=Field(default='',max_length=16000)
    config:Configuration=Field(default_factory=Configuration)
    inputPosition:Literal['left','right','top','bottom']='left'
    outputPosition:Literal['left','right','top','bottom']='right'
    origin:str=Field(default='proposed',max_length=100)
    deploymentMode:Literal['reference','create']|None=None
    poc:bool=False
    role:Literal['data','ingest','index','llm','guard','human','app','output','model','monitor']|None=None
    measures:list[Measure]|None=Field(default=None,max_length=10)
    topologyGroup:str|None=Field(default=None,max_length=100)
    service:str|None=Field(default=None,max_length=150)
    category:str|None=Field(default=None,max_length=150)
    binding:Literal['public-catalog-editor','cloud-storage-principal','aws-iam-principal','aws-bedrock-model','normalized-source-contract','web-browser','existing-service']|None=None
    implementation:Literal['public-faq-app','ibm-structured-app','gcp-structured-app','azure-structured-app','container-service','private-object-storage','rag-web-app','rag-user-pool','bounded-keyword-rag','iam-rag-api','bounded-rag-catalog','text-statistics','bedrock-summary','bedrock-structured','structured-api','structured-web-app','structured-user-pool','async-word-count','sqs-standard','sqs-dead-letter','word-count-results']|None=None

    @model_validator(mode='after')
    def named_component(self):
        if self.deploymentMode=='reference' and self.origin not in {'existing','imported Pulumi state'}:raise ValueError('Reference handling must preserve an existing system')
        if self.binding and (self.origin not in {'existing','imported Pulumi state'} or self.deploymentMode=='create'):raise ValueError('Reference bindings identify existing systems and cannot provision a replacement')
        if self.origin=='existing' and self.deploymentMode=='create' and (self.implementation!='container-service' or self.binding):
            raise ValueError('Existing application source needs an explicit container-service contract without a reference binding.')
        if self.kind != 'note' and len(self.label)>150:
            raise ValueError('Architecture component names must have at most 150 characters.')
        if self.kind != 'note' and not self.label.strip():
            raise ValueError('Architecture components need a name; sticky notes may be empty.')
        return self

class Node(Strict):
    id:str=Field(min_length=1,max_length=100)
    type:Literal['resource']='resource'
    position:Position
    data:Data

class Edge(Strict):
    id:str=Field(min_length=1,max_length=150)
    source:str=Field(max_length=100)
    target:str=Field(max_length=100)
    type:Literal['smoothstep']='smoothstep'
    label:str=Field(default='data',max_length=150)
    integration:Literal['public-catalog-edit','browser-https','web-rag-api','oauth-pkce','jwt-authorizer','source-catalog-sync','http-api-lambda','lambda-catalog-read','bedrock-converse','s3-object-created','sqs-lambda','lambda-s3-read','lambda-dynamodb-write','sqs-redrive']|None=None
    access:Literal['storage-object-admin','s3-read','s3-read-write','lambda-invoke','api-invoke']|None=None

class Project(Strict):
    version:Literal[1]=1
    revision:int=Field(ge=1)
    name:str=Field(min_length=1,max_length=200)
    provider:Literal['aws','azure','gcp','ibm','tools']='tools'
    domain:Literal['maintenance','churn']|None=None
    requirements:str=Field(default='',max_length=64000)
    nodes:list[Node]=Field(max_length=200)
    edges:list[Edge]=Field(max_length=600)
    @model_validator(mode='after')
    def integrity(self):
        ids=[n.id for n in self.nodes]
        if len(ids)!=len(set(ids)):raise ValueError('Duplicate block IDs')
        wires=[e.id for e in self.edges]
        if len(wires)!=len(set(wires)):raise ValueError('Duplicate wire IDs')
        if any(e.source not in ids or e.target not in ids or e.source==e.target for e in self.edges):raise ValueError('Invalid wire endpoint')
        return self

class Proposal(Strict):
    baseRevision:int=Field(ge=1)
    title:str=Field(max_length=200)
    body:str=Field(max_length=4000)
    next:Project

class ToolRequest(Strict):
    name:Literal['memory.lookup','knowledge.lookup','project.read','skills.lookup','pricing.lookup','pricing.aws_s3']
    query:str=Field(default='',max_length=500)

class Scores(Strict):
    cost:int=Field(ge=1,le=5)
    risk:int=Field(ge=1,le=5)
    scalability:int=Field(ge=1,le=5)
    security:int=Field(ge=1,le=5)

class OptionAssessment(Strict):
    provider:Literal['current','aws','azure','gcp','ibm']
    scores:Scores
    rationale:str=Field(min_length=1,max_length=1000)

class UsageUpdate(Strict):
    key:Literal['requests_per_month','tokens_per_request','data_gb','endpoint_hours','events_per_month','training_hours']
    value:float=Field(ge=0,le=1e12,allow_inf_nan=False)
    sourceText:str=Field(min_length=1,max_length=500)

class RequirementUpdate(Strict):
    rationale:str=Field(default='',max_length=1000)
    id:str=Field(min_length=1,max_length=60)
    statement:str=Field(min_length=1,max_length=1000)
    sourceText:str=Field(min_length=1,max_length=500)

class RequirementTarget(Strict):
    metric:str=Field(min_length=1,max_length=150)
    op:Literal['>=','<=','==']
    target:float=Field(allow_inf_nan=False)
    unit:str=Field(default='',max_length=40)

class RequirementDraft(Strict):
    rationale:str=Field(default='',max_length=1000)
    basis:str=Field(default='',max_length=1000)
    id:str=Field(pattern=r'^ai-[A-Za-z0-9-]{1,55}$')
    statement:str=Field(min_length=1,max_length=1000)
    kind:Literal['functional','nonfunctional']
    category:Literal['security','reliability','availability','scalability','performance','maintainability','cost','compliance','other']
    priority:Literal['must','should','could']='should'
    links:list[str]=Field(default_factory=list,max_length=50)
    measure:RequirementTarget|None=None

class DecisionUpdate(Strict):
    subject:Literal['platform.cloud','cloud.region','data.country','infrastructure.tool']
    value:str=Field(min_length=1,max_length=100)
    sourceText:str=Field(min_length=1,max_length=500)

class ComponentReviewResult(Strict):
    componentId:str=Field(min_length=1,max_length=100)
    summary:str=Field(min_length=1,max_length=2000)
    questions:list[str]=Field(default_factory=list,max_length=6)
    @field_validator('questions')
    @classmethod
    def bounded_questions(cls,values):
        if any(not q.strip() or len(q)>1000 for q in values):
            raise ValueError('Block questions must contain 1–1000 characters.')
        return values

class FollowUpQuestion(Strict):
    question:str=Field(min_length=1,max_length=400)
    why:str=Field(min_length=1,max_length=400)
    example:str=Field(default='',max_length=400)
    topic:Literal['application','users','data','systems','quality','cloud','budget']|None=None

class NodeFieldUpdate(Strict):
    id:StrictStr=Field(min_length=1,max_length=100)
    field:Literal['label','description','kind','provider','service','role','origin','binding','implementation','deploymentMode','topologyGroup','config.region','config.classification','config.maxInputBytes','config.maxOutputTokens','config.memoryMb','config.functionTimeoutSeconds','config.concurrency','config.logRetentionDays','config.modelId','config.outputContract']
    value:StrictStr|StrictInt|StrictBool|OutputContract|None

class EdgeFieldUpdate(Strict):
    id:StrictStr=Field(min_length=1,max_length=150)
    field:Literal['label','source','target','integration','access']
    value:StrictStr|None

class DesignPatch(Strict):
    projectName:StrictStr|None=Field(default=None,min_length=1,max_length=200)
    baseRevision:int=Field(ge=1)
    title:str=Field(min_length=1,max_length=200)
    body:str=Field(default='',max_length=4000)
    addNodes:list[Node]=Field(default_factory=list,max_length=200)
    nodeUpdates:list[NodeFieldUpdate]=Field(default_factory=list,max_length=600)
    removeNodeIds:list[Annotated[StrictStr,Field(min_length=1,max_length=100)]]=Field(default_factory=list,max_length=200)
    addEdges:list[Edge]=Field(default_factory=list,max_length=600)
    edgeUpdates:list[EdgeFieldUpdate]=Field(default_factory=list,max_length=1200)
    removeEdgeIds:list[Annotated[StrictStr,Field(min_length=1,max_length=150)]]=Field(default_factory=list,max_length=600)

class ArchitectResponse(Strict):
    _response_repair_attempts:int=PrivateAttr(default=0)
    _model_response_encoding:str=PrivateAttr(default="full_response")
    _model_response_json_bytes:int=PrivateAttr(default=0)
    message:str=Field(min_length=1,max_length=16000)
    patch:DesignPatch|None=None
    componentReview:ComponentReviewResult|None=None
    followUp:FollowUpQuestion|None=None
    phase:Literal['Discovery','Architecture','Cost Analysis','Architecture Review']='Discovery'
    proposal:Proposal|None=None
    toolRequests:list[ToolRequest]|None=Field(default=None,max_length=3)
    optionAssessment:list[OptionAssessment]|None=Field(default=None,max_length=5)
    usageUpdates:list[UsageUpdate]|None=Field(default=None,max_length=6)
    requirementDrafts:list[RequirementDraft]|None=Field(default=None,max_length=20)
    requirementUpdates:list[RequirementUpdate]|None=Field(default=None,max_length=10)
    decisionUpdates:list[DecisionUpdate]|None=Field(default=None,max_length=3)

class Message(Strict):
    role:Literal['user','assistant']
    text:str=Field(max_length=12000)

class ContextItem(Strict):
    type:Literal['requirement','assumption','question','decision','discovery']
    id:str=Field(min_length=1,max_length=60)
    text:str=Field(max_length=1000)

class Attachment(Strict):
    name:str=Field(min_length=1,max_length=180,pattern=r'^[^/\\\x00-\x1f]+$')
    mime:Literal['image/png','image/jpeg','image/webp','application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document','text/plain','text/markdown','text/csv','application/json']
    data:str=Field(min_length=1,max_length=5592408)

class ChatRequest(Strict):
    attachments:list[Attachment]=Field(default_factory=list,max_length=4)
    origin:Literal['chat','canvas','workflow','document','preview','emulation','block-review']='chat'
    projectId:str|None=Field(default=None,pattern=r'^[A-Za-z0-9-]{8,64}$')
    message:str=Field(min_length=1,max_length=8000)
    provider:Literal['claude-code','codex','copilot','gemini-cli','anthropic','openai','gemini-api','xai','bedrock']='claude-code'
    model:str=Field(min_length=1,max_length=150)
    effort:Literal['none','minimal','low','medium','high','xhigh','max','ultra']|None=None
    project:Project
    stage:Literal['discover','design','review','estimate','deploy','build']='discover'
    context:list[ContextItem]=Field(default_factory=list,max_length=300)
    history:list[Message]=Field(default_factory=list,max_length=16)
    @field_validator('message','model')
    @classmethod
    def not_blank(cls,value):
        if not value.strip():raise ValueError('Must not be blank')
        return value


def architect_output_schema(allow_tools=True):
    """Compact model wire protocol; host still returns the established proposal API."""
    schema=ArchitectResponse.model_json_schema()
    schema['properties']['proposal']={'type':'null','description':'Full snapshots are host-owned. Use patch for design edits.'}
    if not allow_tools:schema['properties']['toolRequests']={'type':'null','description':'Evidence lookup budget is exhausted. Return the bounded final response using available evidence.'}
    else:schema['$defs']['ToolRequest']['properties']['name']['enum']=['memory.lookup','knowledge.lookup','pricing.lookup']
    schema.get('$defs',{}).pop('Proposal',None)
    schema.get('$defs',{}).pop('Project',None)
    return schema
