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

    def test_follow_up_is_optional_and_separate_from_generic_topic_checklist(self):
        from server.contracts import ArchitectResponse
        quiet=ArchitectResponse(message='The topology now separates access and project memory.')
        self.assertIsNone(quiet.followUp)
        answer=ArchitectResponse(message='Who owns project memory?',followUp={'question':'Who owns project memory?','why':'This determines access boundaries.','example':'Creator only or project members.','topic':'users'})
        self.assertEqual(answer.followUp.topic,'users')
