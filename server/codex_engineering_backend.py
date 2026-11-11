"""Codex adapter for portable engineering sessions; no public/browser endpoint.

Workspace registrations and scope originate from the worker's trusted control plane.
The native sandbox constrains writes/network, but this adapter alone is NOT a hosted
multi-tenant isolation boundary. Hosted workers need separately qualified isolation.
"""
from pathlib import Path
from .codex_app_server import CodexAppServer, ProtocolError
from .engineering_sessions import BackendEvent, EmptySessionUnavailable, RecoveredStart, SessionError


class CodexEngineeringBackend:
    name='codex-app-server'

    def __init__(self,workspaces,*,client_factory=CodexAppServer,instructions='',permission_profile=None,tools=None):
        self.workspaces=dict(workspaces)
        self.client_factory=client_factory
        self.instructions=instructions
        self.permission_profile=permission_profile
        self.tools=tools
        if permission_profile:
            # The durable coordinator must refuse a legacy-policy fallback after
            # restart, even though both implementations use the same model API.
            self.name=f'codex-app-server:{permission_profile}'
        self.clients={}

    def _workspace(self,scope,workspace):
        registered=self.workspaces.get((scope,workspace))
        if registered is None:
            raise SessionError('Workspace is not registered for this project')
        root=Path(registered).resolve(strict=True)
        if not root.is_dir():
            raise SessionError('Registered workspace is unavailable')
        return root

    @staticmethod
    def _policy(root):
        return {'type':'workspaceWrite','writableRoots':[str(root)],'networkAccess':False,
                'excludeSlashTmp':True,'excludeTmpdirEnvVar':True}

    def _verify(self,result,root,selection):
        policy=result.get('sandbox',{})
        if result.get('cwd')!=str(root) or result.get('model')!=selection.model or result.get('reasoningEffort')!=selection.effort:
            raise SessionError('Codex did not confirm the selected workspace, model and reasoning effort')
        expected_network=bool(self.permission_profile)
        if result.get('approvalPolicy')!='never' or policy.get('type')!='workspaceWrite' or policy.get('networkAccess') is not expected_network:
            raise SessionError('Codex did not confirm the required local execution policy')
        if policy.get('excludeSlashTmp') is not True or policy.get('excludeTmpdirEnvVar') is not True or set(policy.get('writableRoots',[]))-{str(root)}:
            raise SessionError('Codex returned additional writable roots or temporary directories')
        if self.permission_profile:
            if result.get('activePermissionProfile',{}).get('id')!=self.permission_profile or result.get('runtimeWorkspaceRoots')!=[str(root)]:
                raise SessionError('Codex did not confirm the selected worker profile and sole project root')
            sources=result.get('instructionSources',[])
            if not isinstance(sources,list) or any(not isinstance(source,str) or not Path(source).resolve().is_relative_to(root) for source in sources):
                raise SessionError('The native worker inherited instructions outside this project workspace')
        handle=result.get('thread',{}).get('id')
        if not isinstance(handle,str) or not handle:
            raise SessionError('Codex did not confirm a thread')
        return handle

    def _params(self,root,selection):
        return {'cwd':str(root),'model':selection.model,'approvalPolicy':'never',
                **({'permissions':self.permission_profile,'config':{'model_reasoning_effort':selection.effort}}
                   if self.permission_profile else {'sandbox':'workspace-write','config':{
                    'model_reasoning_effort':selection.effort,
                    'sandbox_workspace_write.network_access':False,
                    'sandbox_workspace_write.exclude_slash_tmp':True,
                    'sandbox_workspace_write.exclude_tmpdir_env_var':True}}),
                **({'developerInstructions':self.instructions} if self.instructions else {})}

    def _owned(self,scope,handle,selection=None):
        row=self.clients.get((scope,handle))
        if not row or (selection is not None and row[2]!=selection):
            raise SessionError('Codex session is unavailable for this project or model selection')
        return row

    def _bind_tools(self,client,scope,workspace,handle):
        if self.tools is None:return
        async def invoke(params):
            self._owned(scope,handle)
            if not isinstance(params,dict) or set(params)-{'threadId','turnId','callId','tool','arguments','namespace'} or params.get('threadId')!=handle or params.get('namespace') is not None:
                raise SessionError('Native tool callback belongs to another thread or namespace')
            return await self.tools.invoke(scope,workspace,params.get('turnId'),params.get('callId'),params.get('tool'),params.get('arguments'))
        client.dynamic_tool_handler=invoke

    async def create(self,scope,workspace,selection):
        root=self._workspace(scope,workspace)
        client=self.client_factory(root)
        try:
            if self.tools is not None:client.experimental=True
            await client.start()
            result=await client.request('thread/start',{**self._params(root,selection),
                **({'dynamicTools':self.tools.specs} if self.tools is not None else {})})
            handle=self._verify(result,root,selection)
            if self.permission_profile:
                await client.verify_worker_tools(self.permission_profile)
            if (scope,handle) in self.clients:
                raise SessionError('Codex returned a previously registered thread')
            self.clients[scope,handle]=(client,root,selection)
            self._bind_tools(client,scope,workspace,handle)
            return handle
        except BaseException:
            await client.close();raise

    async def resume(self,scope,handle,workspace,selection):
        root=self._workspace(scope,workspace)
        if (scope,handle) in self.clients:
            row=self._owned(scope,handle,selection)
            if row[1]!=root:
                raise SessionError('A session cannot change its registered workspace')
            client=row[0]
            process=getattr(client,'process',None)
            if not getattr(client,'failure',None) and (process is None or process.returncode is None):
                return
            # A dead cached transport cannot recover itself. Reopen the same
            # persisted native thread; never start a replacement for accepted work.
            self.clients.pop((scope,handle))
            await client.close()
        client=self.client_factory(root)
        try:
            if self.tools is not None:client.experimental=True
            await client.start()
            # App-server resume reloads runtime configuration. Reassert the exact
            # project model/effort and execution policy instead of inheriting the
            # worker's current defaults, then verify its acknowledgement below.
            params=self._params(root,selection)
            result=await client.request('thread/resume',{
                **params,'threadId':handle,'excludeTurns':True})
            if self._verify(result,root,selection)!=handle:
                raise SessionError('Codex resumed a different thread')
            if self.permission_profile:
                await client.verify_worker_tools(self.permission_profile)
            self.clients[scope,handle]=(client,root,selection)
            self._bind_tools(client,scope,workspace,handle)
        except ProtocolError as error:
            await client.close()
            if error.category=='missing_thread':
                raise EmptySessionUnavailable('Native thread has no stored history') from None
            raise
        except BaseException:
            await client.close();raise

    async def start(self,scope,handle,text,selection,*,request_id=None,context=None):
        client,root,_=self._owned(scope,handle,selection)
        inputs = self._inputs(scope, text, context)
        result=await client.request('turn/start',{'threadId':handle,
            'input':inputs,'cwd':str(root),
            'model':selection.model,'effort':selection.effort,
            'approvalPolicy':'never',
            **({'permissions':self.permission_profile} if self.permission_profile else {'sandboxPolicy':self._policy(root)}),
            **({'clientUserMessageId':request_id} if request_id is not None else {})})
        turn=result.get('turn',{})
        if turn.get('status')!='inProgress' or not isinstance(turn.get('id'),str) or not turn['id']:
            raise SessionError('Codex did not confirm an active engineering turn')
        return turn['id']

    async def recover_start(self,scope,handle,request_id):
        """Match durable client message identity; never infer acceptance from text.

        This is acknowledgement recovery, not an idempotent resubmission promise.
        An absent/ambiguous match leaves the reservation unresolved.
        """
        client,_,_=self._owned(scope,handle)
        cursor=None;seen=set();matches=[]
        for _ in range(20):
            params={'threadId':handle,'limit':100,'sortDirection':'desc','itemsView':'summary'}
            if cursor is not None:params['cursor']=cursor
            result=await client.request('thread/turns/list',params)
            turns=result.get('data')
            if not isinstance(turns,list):raise SessionError('Native start history is unavailable')
            for candidate in turns:
                if not isinstance(candidate,dict) or not isinstance(candidate.get('items'),list):
                    raise SessionError('Native start history is malformed')
                for item in candidate['items']:
                    if not isinstance(item,dict):raise SessionError('Native message identity is malformed')
                    if item.get('type')=='userMessage' and item.get('clientId')==request_id:
                        status=candidate.get('status')
                        matches.append(RecoveredStart(request_id,candidate.get('id'),'running' if status=='inProgress' else status))
            cursor=result.get('nextCursor')
            if cursor is None:
                if len(matches)>1:raise SessionError('Native start identity is ambiguous; no work was replayed')
                return matches[0] if matches else None
            if not isinstance(cursor,str) or not cursor or cursor in seen:
                raise SessionError('Native start history cursor is invalid')
            seen.add(cursor)
        raise SessionError('Native start history exceeded the recovery bound')

    async def observe(self,scope,handle,turn):
        """Recover terminal state without resubmitting work or loading its content.

        Missing, malformed or excessively paginated history is uncertain, never
        an idle session. The control-plane reservation remains in place.
        """
        client,_,_=self._owned(scope,handle)
        cursor=None
        seen=set()
        for _ in range(20):
            params={'threadId':handle,'limit':100,'sortDirection':'desc','itemsView':'notLoaded'}
            if cursor is not None:
                params['cursor']=cursor
            result=await client.request('thread/turns/list',params)
            turns=result.get('data')
            if not isinstance(turns,list):
                raise SessionError('Codex turn history is unavailable; recovery is required')
            for candidate in turns:
                if not isinstance(candidate,dict):
                    raise SessionError('Codex returned malformed turn history')
                if candidate.get('id')==turn:
                    status=candidate.get('status')
                    if status=='inProgress':
                        return None
                    if status in {'completed','failed','interrupted'}:
                        return BackendEvent(turn,status)
                    raise SessionError('Codex returned an unknown recovered turn status')
            cursor=result.get('nextCursor')
            if cursor is None:
                break
            if not isinstance(cursor,str) or not cursor or cursor in seen:
                raise SessionError('Codex returned an invalid turn-history cursor')
            seen.add(cursor)
        raise SessionError('The owned turn was not found in bounded history; recovery is required')

    @staticmethod
    def _inputs(scope, text, context):
        inputs = [{'type':'text','text':text}]
        if context is not None:
            from .engineering_contexts import context_input
            if context.get('projectId') != scope.project:
                raise SessionError('Project context does not belong to this engineering session')
            inputs.append(context_input(context))
        return inputs

    async def steer(self,scope,handle,turn,text,*,request_id=None,context=None):
        client,_,_=self._owned(scope,handle)
        await client.request('turn/steer',{'threadId':handle,'expectedTurnId':turn,
                                         'input':self._inputs(scope, text, context),
                                         **({'clientUserMessageId':request_id} if request_id is not None else {})})

    async def interrupt(self,scope,handle,turn):
        client,_,_=self._owned(scope,handle)
        await client.request('turn/interrupt',{'threadId':handle,'turnId':turn})

    async def next_event(self,scope,handle):
        client,_,_=self._owned(scope,handle)
        while True:
            message=await client.notification()
            method=message.get('method');params=message.get('params',{})
            if params.get('threadId') not in (None,handle):
                raise SessionError('Codex notification belongs to another thread')
            if method=='turn/completed':
                turn=params.get('turn',{});status=turn.get('status')
                if status not in {'completed','failed','interrupted'}:
                    raise SessionError('Codex returned an unknown terminal turn status')
                return BackendEvent(turn.get('id'),status)
            if method=='item/agentMessage/delta':
                return BackendEvent(params.get('turnId'),'message',params.get('delta',''))
            if method in {'item/started','item/completed'}:
                item=params.get('item',{})
                if params.get('turnId'):
                    # Tool summaries are progress, never successful validation.
                    return BackendEvent(params['turnId'],'progress',str(item.get('type','work')))

    async def close(self):
        rows=list(self.clients.values());self.clients.clear()
        for client,_,_ in rows:
            await client.close()
