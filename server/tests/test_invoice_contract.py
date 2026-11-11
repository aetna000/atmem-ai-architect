import unittest
import asyncio,copy,json
from unittest.mock import AsyncMock,patch
from pydantic import ValidationError
from server.contracts import Project,Configuration,NodeFieldUpdate,ChatRequest,validate_proposed_regions
from server.architect import AtMemArchitect

class InvoiceDesignContractTests(unittest.TestCase):
    def project(self):
        return {'version':1,'revision':1,'name':'Invoice workflow','provider':'ibm','nodes':[
            {'id':'workflow','position':{'x':0,'y':0},'data':{'label':'Invoice intake','kind':'resource','provider':'ibm','service':'IBM Code Engine','implementation':'invoice-workflow','config':{'region':'au-syd','maxPdfBytes':10000000,'maxPdfPages':100,'retentionDays':90}}},
            {'id':'accounting','position':{'x':1,'y':0},'data':{'label':'Existing accounting','kind':'tool','provider':'tools','origin':'existing','binding':'existing-service'}}],
            'edges':[{'id':'approved','source':'workflow','target':'accounting','integration':'approved-accounting-api'}]}

    def test_invoice_fields_and_typed_existing_accounting_flow_are_preserved(self):
        project=Project.model_validate(self.project());value=project.model_dump(exclude_none=True)
        self.assertEqual(value['nodes'][0]['data']['implementation'],'invoice-workflow')
        self.assertEqual(value['nodes'][0]['data']['config']['maxPdfBytes'],10000000)
        self.assertEqual(value['edges'][0]['integration'],'approved-accounting-api')
        self.assertEqual(value['nodes'][1]['data']['origin'],'existing')

    def test_explicit_alternative_retention_is_preserved_for_generator_gap_evaluation(self):
        value=self.project();value['nodes'][0]['data']['config']['retentionDays']=365
        self.assertEqual(Project.model_validate(value).nodes[0].data.config.retentionDays,365)
        update=NodeFieldUpdate(id='workflow',field='config.retentionDays',value=365)
        self.assertEqual(update.value,365)

    def test_pdf_and_retention_limits_refuse_boolean_fractional_and_unbounded_inputs(self):
        for key,value in [('maxPdfBytes',True),('maxPdfPages',1.5),('maxPdfBytes',20000001),('maxPdfPages',0),('retentionDays',3654)]:
            with self.subTest(key=key,value=value),self.assertRaises(ValidationError):Configuration.model_validate({key:value})

    def test_invoice_reference_cannot_be_used_to_create_an_existing_accounting_replacement(self):
        value=self.project();value['nodes'][1]['data']['deploymentMode']='create'
        with self.assertRaises(ValidationError):Project.model_validate(value)

    def test_proposed_region_annotation_requires_internal_format_repair_while_references_keep_their_description(self):
        value=self.project();value['nodes'][0]['data']['config']['region']='Sydney (au-syd) proposed; model availability unverified'
        historical=Project.model_validate(value)
        self.assertEqual(historical.nodes[0].data.config.region,value['nodes'][0]['data']['config']['region'])
        with self.assertRaisesRegex(ValueError,'canonical provider region'):validate_proposed_regions(historical)
        value['nodes'][0]['data']['config']['region']='au-syd';value['nodes'][0]['data']['description']='Sydney proposed; model availability unverified';value['nodes'][1]['data']['config']={'region':'Existing placement; unconfirmed'}
        result=Project.model_validate(value);self.assertEqual(result.nodes[0].data.config.region,'au-syd');self.assertIn('unverified',result.nodes[0].data.description);self.assertEqual(result.nodes[1].data.config.region,'Existing placement; unconfirmed')

    def test_region_format_failure_uses_bounded_model_repair_without_another_user_question(self):
        project=self.project();request=ChatRequest(projectId='invoice-repair',message='Keep invoice data in Australia.',provider='codex',model='default',project=project)
        invalid=copy.deepcopy(project);invalid['nodes'][0]['data']['config']['region']='Sydney (au-syd) proposed; service and model availability unverified'
        valid=copy.deepcopy(project);valid['nodes'][0]['data']['description']='Sydney proposed; service and model availability unverified'
        def response(next):return {'message':'Propose the regional workflow.','proposal':{'baseRevision':1,'title':'Invoice workflow','body':'Preserve existing accounting and residency.','next':next}}
        cli=AsyncMock(side_effect=[response(invalid),response(valid)])
        with patch('server.local_providers.call_cli',cli):result=asyncio.run(AtMemArchitect().call(request,AsyncMock(return_value=False),{'toolBudget':{'canRequestTools':False}}))
        self.assertEqual(cli.await_count,2);self.assertEqual(result._response_repair_attempts,1);self.assertIsNone(result.followUp)
        self.assertEqual(result.proposal.next.nodes[0].data.config.region,'au-syd');self.assertIn('unverified',result.proposal.next.nodes[0].data.description)
        diagnostic=json.loads(cli.await_args_list[1].args[2])['runtimeContext']['responseRepair'];self.assertIn('Do not ask the user',diagnostic['instruction']);self.assertIn('canonical provider region',json.dumps(diagnostic))

    def test_canonical_partition_regions_are_retained_without_claiming_adapter_support(self):
        for region in ['cn-north-1', 'us-gov-west-1']:
            with self.subTest(region=region):
                value=self.project();value['provider']='aws';value['nodes'][0]['data'].update(provider='aws',service='Amazon ECS')
                value['nodes'][0]['data']['config']['region']=region
                project=Project.model_validate(value);validate_proposed_regions(project)
                self.assertEqual(project.nodes[0].data.config.region,region)

if __name__=='__main__':unittest.main()
