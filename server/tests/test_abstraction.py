import json,unittest
from server.contracts import ChatRequest
from server.abstraction import consultation_focus
from server.architect import AtMemArchitect
from server.prompts import SYSTEM_PROMPT

def request(message,origin='chat'):
    return ChatRequest(message=message,provider='codex',model='default',origin=origin,project={'version':1,'revision':1,'name':'Topology','nodes':[],'edges':[]})

class ProgressiveAbstractionTests(unittest.TestCase):
    def test_deployment_goal_does_not_force_packaging_questionnaire(self):
        focus=consultation_focus(request('I can build it if needed. Put Architect on our existing website.'))
        self.assertEqual(focus['level'],'system_design')
        self.assertIn('runtime port',focus['deferUnlessRelevant'])
        self.assertLess(focus['priorityOrder'].index('existing systems and deployment ownership'),focus['priorityOrder'].index('implementation configuration'))

    def test_explicit_detail_and_overview_requests_are_respected(self):
        self.assertEqual(consultation_focus(request('What port does it run on?'))['level'],'implementation')
        self.assertEqual(consultation_focus(request('Show the high-level topology and defer ports'))['level'],'topology')
        self.assertEqual(consultation_focus(request('Review the selected block','block-review'))['level'],'component_contracts')

    def test_policy_is_server_owned_and_present_in_native_model_context(self):
        context=json.loads(AtMemArchitect.context(request('Help shape this system')))
        self.assertEqual(context['consultationFocus']['level'],'system_design')
        self.assertIn('Do not ask how to package an application',SYSTEM_PROMPT)
        self.assertIn('ask only for material user decisions',SYSTEM_PROMPT)

    def test_components_are_presented_while_topology_stays_internal(self):
        focus=consultation_focus(request('Help me add what this application needs'))
        self.assertIn('Keep topology reasoning internal',focus['topologyPolicy'])
        self.assertIn('Add the components and connections',focus['topologyPolicy'])
        self.assertIn('Do not expect the user to know',SYSTEM_PROMPT)

    def test_follow_up_is_optional_and_separate_from_generic_topic_checklist(self):
        from server.contracts import ArchitectResponse
        quiet=ArchitectResponse(message='The topology now separates access and project memory.')
        self.assertIsNone(quiet.followUp)
        answer=ArchitectResponse(message='Who owns project memory?',followUp={'question':'Who owns project memory?','why':'This determines access boundaries.','example':'Creator only or project members.','topic':'users'})
        self.assertEqual(answer.followUp.topic,'users')

    def test_architect_owns_engineering_and_targets_fast_convergence_without_skipping_quality(self):
        focus=consultation_focus(request('Please build a website with sign-in, credits and project memory'))
        self.assertIn('Architect proposes',focus['engineeringOwner'])
        self.assertIn('ten meaningful user exchanges',focus['convergencePolicy'])
        self.assertIn('not a limit or a quality claim',focus['convergencePolicy'])
        self.assertIn('Track interconnected application',SYSTEM_PROMPT)
        self.assertIn('Recommend first',SYSTEM_PROMPT)


class ResponseBudgetTests(unittest.TestCase):
    def test_complex_connected_designs_have_a_bounded_larger_budget_without_changing_questions(self):
        from server.abstraction import response_budget_seconds
        simple=request('Summarize a short public article')
        self.assertEqual(response_budget_seconds(simple),150)
        complex_request=request('Existing website with tenant authentication, credit payments and durable workflow retries')
        self.assertEqual(response_budget_seconds(complex_request),240)
        self.assertEqual(consultation_focus(complex_request)['level'],'system_design')

    def test_real_regulated_enterprise_case_receives_complex_design_budget(self):
        from server.abstraction import response_budget_seconds
        import json
        from pathlib import Path
        corpus=json.loads((Path(__file__).resolve().parents[2]/'benchmarks/convergence/scenarios.json').read_text())
        for scenario in corpus['scenarios']:
            if scenario['difficulty']=='hard':self.assertEqual(response_budget_seconds(request(scenario['intent'])),240,scenario['id'])
