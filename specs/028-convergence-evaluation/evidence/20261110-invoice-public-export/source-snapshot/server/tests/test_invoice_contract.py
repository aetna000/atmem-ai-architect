import unittest
from pydantic import ValidationError
from server.contracts import Project,Configuration,NodeFieldUpdate

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

if __name__=='__main__':unittest.main()
