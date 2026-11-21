import unittest
from pydantic import ValidationError
from server.contracts import DesignPatch, Project
from server.design_patch import apply_design_patch


def block(id, **data):
    return {'id': id, 'position': {'x': 0, 'y': 0}, 'data': {
        'label': id, 'kind': 'resource', 'provider': 'tools', **data,
    }}


class BlockSpecTests(unittest.TestCase):
    def test_patch_can_nest_and_specify_existing_nodes(self):
        project = Project(name='Reservation system', revision=3, nodes=[block('app'), block('holds')], edges=[])
        patch = DesignPatch.model_validate({'baseRevision': 3, 'title': 'Plan reservations', 'nodeUpdates': [
            {'id': 'holds', 'field': 'parentBlockId', 'value': 'app'},
            {'id': 'holds', 'field': 'buildSpec', 'value': {'scenarios': [{
                'name': 'Competing holds',
                'steps': [{'sender': 'API', 'receiver': 'Hold manager', 'action': 'Try to reserve a seat'}],
            }], 'tests': 'Only one hold is accepted.', 'behavior': None}},
        ]})
        candidate = apply_design_patch(project, patch).next
        self.assertIsNone(project.nodes[1].data.parentBlockId)
        self.assertEqual(candidate.nodes[1].data.parentBlockId, 'app')
        self.assertEqual(candidate.nodes[1].data.buildSpec.scenarios[0].steps[0].receiver, 'Hold manager')

    def test_cycle_and_invalid_spec_are_rejected(self):
        with self.assertRaisesRegex(ValidationError, 'cycle'):
            Project(name='Cycle', revision=1, nodes=[block('a', parentBlockId='b'), block('b', parentBlockId='a')], edges=[])
        with self.assertRaises(ValidationError):
            Project(name='Empty', revision=1, nodes=[block('a', buildSpec={'tests': None, 'behavior': None})], edges=[])

    def test_interface_patch_keeps_proposed_contract(self):
        project = Project(name='Reservations', revision=1, nodes=[block('a'), block('b')],
                          edges=[{'id': 'e', 'source': 'a', 'target': 'b'}])
        fields = dict(transport='JSON v1', input='Seat', output='Reservation ID', authorization='Box office',
                      failure='Look up reservation after timeout', verification='Contract fixture')
        patch = DesignPatch.model_validate({'baseRevision': 1, 'title': 'Contract',
                                           'edgeUpdates': [{'id': 'e', 'field': 'interfaceSpec', 'value': fields}]})
        self.assertEqual(apply_design_patch(project, patch).next.edges[0].interfaceSpec.model_dump(), fields)


    def test_typed_behavior_refs_survive_patch_and_reject_invalid_kinds(self):
        from server.contracts import ScenarioStep
        step={'sender':'API role','receiver':'Hold manager role','action':'Reserve seat','messageKind':'command',
              'senderBlockId':'app','receiverBlockId':'holds','interfaceId':'reserve','requirementIds':['one-owner']}
        project=Project(name='Reservations',revision=1,nodes=[block('app'),block('holds')],edges=[])
        patch=DesignPatch.model_validate({'baseRevision':1,'title':'Bind behavior','nodeUpdates':[
            {'id':'holds','field':'buildSpec','value':{'scenarios':[{'name':'Race','steps':[step]}]}}]})
        actual=apply_design_patch(project,patch).next.nodes[1].data.buildSpec.scenarios[0].steps[0]
        self.assertEqual(actual.model_dump(exclude_none=True),step)
        for change in [{'messageKind':'guess'},{'requirementIds':['one-owner','one-owner']},{'receiverBlockId':''},{'execute':'command'}]:
            with self.assertRaises(ValidationError):ScenarioStep.model_validate({**step,**change})

    def test_model_operation_identity_survives_scenario_patch(self):
        step={'sender':'Technician','receiver':'Hold manager','action':'Record hold','messageKind':'command','operationId':'hold.record'}
        project=Project(name='Reservation system',revision=3,nodes=[block('app'),block('holds')],edges=[])
        patch=DesignPatch.model_validate({'baseRevision':3,'title':'Bind operation','nodeUpdates':[{'id':'holds','field':'buildSpec','value':{'scenarios':[{'name':'Hold','steps':[step]}]}}]})
        candidate=apply_design_patch(project,patch).next
        self.assertEqual(candidate.nodes[1].data.buildSpec.scenarios[0].steps[0].operationId,'hold.record')
        from server.contracts import ScenarioStep
        with self.assertRaises(ValidationError):ScenarioStep(**{**step,'operationId':' '})
