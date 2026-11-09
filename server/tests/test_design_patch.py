import asyncio,copy,json,unittest
from unittest.mock import AsyncMock,patch
from server.contracts import Project,DesignPatch,ArchitectResponse,ChatRequest
from server.design_patch import apply_design_patch
from server.architect import AtMemArchitect

def project():return Project.model_validate({'version':1,'revision':7,'name':'Client system','provider':'gcp','requirements':'Keep existing website and private project data','nodes':[{'id':'website','position':{'x':1,'y':2},'data':{'label':'Existing website','kind':'resource','provider':'gcp','origin':'existing','binding':'existing-service','description':'Preserve existing hosting','config':{'region':'To be selected'}}},{'id':'client','position':{'x':-1,'y':2},'data':{'label':'Browser','kind':'resource','provider':'tools','origin':'existing','binding':'web-browser'}}],'edges':[{'id':'visit','source':'client','target':'website','integration':'browser-https'}]})
class DesignPatchTests(unittest.TestCase):
    def change(self,**kwargs):return DesignPatch(baseRevision=7,title='Use accepted placement',**kwargs)
    def test_small_edit_preserves_scope_ownership_unchanged_fields_and_positions(self):
        p=project();before=p.model_dump();proposal=apply_design_patch(p,self.change(nodeUpdates=[{'id':'website','field':'config.region','value':'australia-southeast1'}]))
        self.assertEqual(p.model_dump(),before);self.assertEqual(proposal.next.requirements,p.requirements);self.assertEqual(proposal.next.provider,p.provider)
        self.assertEqual(proposal.next.nodes[0].data.origin,'existing');self.assertEqual(proposal.next.nodes[0].position,p.nodes[0].position);self.assertEqual(proposal.next.nodes[1],p.nodes[1]);self.assertEqual(proposal.next.edges,p.edges)
        self.assertEqual(proposal.next.nodes[0].data.config.region,'australia-southeast1')
    def test_invalid_or_ambiguous_patch_does_not_mutate_the_source(self):
        for updates in [[{'id':'missing','field':'label','value':'x'}],[{'id':'website','field':'config.maxInputBytes','value':True}],[{'id':'website','field':'provider','value':'invented'}],[{'id':'website','field':'label','value':'a'},{'id':'website','field':'label','value':'b'}]]:
            p=project();before=p.model_dump()
            with self.assertRaises(ValueError):apply_design_patch(p,self.change(nodeUpdates=updates))
            self.assertEqual(p.model_dump(),before)
    def test_stale_revision_and_implicit_edge_deletion_rejected(self):
        with self.assertRaisesRegex(ValueError,'wrong revision'):apply_design_patch(project(),DesignPatch(baseRevision=6,title='Stale'))
        with self.assertRaises(ValueError):apply_design_patch(project(),self.change(removeNodeIds=['website']))
        result=apply_design_patch(project(),self.change(removeNodeIds=['website'],removeEdgeIds=['visit']));self.assertEqual(len(result.next.nodes),1);self.assertEqual(result.next.edges,[])
    def test_paths_and_requirement_replacement_are_not_in_the_patch_language(self):
        for field in ['requirements','config.command','__proto__','position.x']:
            with self.assertRaises(ValueError):self.change(nodeUpdates=[{'id':'website','field':field,'value':'injected'}])
        with self.assertRaises(ValueError):self.change(provider='aws')
    def test_host_canonicalizes_patch_to_existing_proposal_api_and_observes_encoding(self):
        async def check():
            raw={'message':'Placed the existing site without recreating it.','patch':self.change(nodeUpdates=[{'id':'website','field':'config.region','value':'australia-southeast1'}]).model_dump(exclude_none=True)}
            req=ChatRequest(provider='codex',model='default',message='Use Australia',project=project())
            with patch('server.local_providers.call_cli',AsyncMock(return_value=raw)):
                result=await AtMemArchitect().call(req,AsyncMock(return_value=False))
            self.assertIsNone(result.patch);self.assertEqual(result.proposal.next.nodes[0].data.config.region,'australia-southeast1');self.assertEqual(result._model_response_encoding,'compact_patch');self.assertGreater(result._model_response_json_bytes,0)
            self.assertNotIn('_model_response_json_bytes',result.model_dump());self.assertEqual(req.project.nodes[0].data.config.region,'To be selected')
        asyncio.run(check())
    def test_ambiguous_both_forms_get_one_internal_repair_and_never_apply_rejected_patch(self):
        async def check():
            raw={'message':'Bad mixed response','patch':self.change().model_dump(exclude_none=True),'proposal':{'baseRevision':7,'title':'Other','body':'','next':project().model_dump(exclude_none=True)}}
            native=AsyncMock(side_effect=[raw,{'message':'A valid no-change response'}]);req=ChatRequest(provider='codex',model='default',message='Review',project=project())
            with patch('server.local_providers.call_cli',native):result=await AtMemArchitect().call(req,AsyncMock(return_value=False))
            self.assertEqual(native.await_count,2);self.assertIsNone(result.proposal);self.assertEqual(result._response_repair_attempts,1)
            self.assertEqual(json.loads(native.call_args_list[1].args[2])['runtimeContext']['responseRepair']['issues'][0]['path'],'patch')
        asyncio.run(check())

    def test_model_wire_schema_forces_compact_edits_but_host_keeps_full_proposal_contract(self):
        from server.contracts import architect_output_schema
        wire=architect_output_schema()
        self.assertEqual(wire['properties']['proposal']['type'],'null');self.assertIn('DesignPatch',wire['$defs']);self.assertNotIn('Project',wire['$defs']);self.assertIn('Proposal',ArchitectResponse.model_json_schema()['$defs'])
        original=project();renamed=apply_design_patch(original,self.change(projectName='New user-selected title'))
        self.assertEqual(renamed.next.name,'New user-selected title');self.assertEqual(original.name,'Client system')
