"""Independent generic storage contract checks in a disposable real SQL fixture."""
import hashlib, json, os, sys, unittest, uuid
from pathlib import Path
sys.path.insert(0, '/work/source/runtime')
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from workflow_database import initialize_database, grant_runtime_roles
from workflow_payload import PayloadContract, encoded
from durable_workflow import WorkflowStore, Principal, Conflict
from durable_fixture_tasks import fixture_tasks, FIXTURE_CONTRACT


def obj(fields): return {'type': 'object', 'properties': fields, 'required': list(fields)}
def text(): return {'type': 'string', 'minBytes': 1, 'maxBytes': 64000}


class Persistence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = os.environ['ATMEM_TEST_POSTGRES_DSN']
        with psycopg.connect(cls.admin) as c:
            initialize_database(c)

    def setUp(self):
        self.account = str(uuid.uuid4()); self.namespace = uuid.uuid4().hex
        self.roles = ['api_'+self.namespace[:12], 'worker_'+self.namespace[:12]]
        password = uuid.uuid4().hex
        with psycopg.connect(self.admin) as c:
            for role in self.roles:
                c.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(sql.Identifier(role), sql.Literal(password)))
            grant_runtime_roles(c, *self.roles)
            c.execute('INSERT INTO workflow.accounts(id) VALUES(%s)', (self.account,))
            for subject, roles in [('staff', ['user']), ('reviewer', ['reviewer'])]:
                c.execute('INSERT INTO workflow.memberships(account_id,subject,roles) VALUES(%s,%s,%s)', (self.account, subject, roles))
        self.api_dsn, self.worker_dsn = [make_conninfo(self.admin, user=role, password=password) for role in self.roles]
        self.app, self.extract, self.dispatch = fixture_tasks(self.worker_dsn, self.namespace)
        self.user = Principal(self.account, 'staff'); self.reviewer = Principal(self.account, 'reviewer')

    def stores(self, domain, source_field, result_field):
        contract = PayloadContract({'version': 1, 'id': domain,
            'source': obj({source_field: text()}), 'result': obj({result_field: text()})})
        args = dict(destination_contract=FIXTURE_CONTRACT, payload_contract=contract)
        return contract, WorkflowStore(self.api_dsn, self.extract, self.dispatch, **args), WorkflowStore(self.worker_dsn, self.extract, self.dispatch, **args)

    def test_two_domains_preserve_control_unicode_history_approval_and_receipt(self):
        for domain, sf, rf in [('archive-transcription', 'transcript', 'correctedText'),
                               ('sensor-annotation', 'observation', 'annotation')]:
            with self.subTest(domain=domain):
                contract, api, worker = self.stores(domain, sf, rf)
                # Valid UTF8 includes controls; validation must never normalize,
                # strip or clip them merely to fit the chosen persistence type.
                value = ''.join(chr(n) for n in range(32))+'🙂é\u0301'
                source = {sf: value}; result = {rf: value+' processed'}
                self.assertEqual(contract.validate('source', source), source)
                operation = api.submit(self.user, 'draft', domain, source)
                self.assertEqual(api.submit(self.user, 'draft', domain, source), operation)
                self.assertEqual(api.get(self.user, operation)['source_ref'], source)
                claim = worker.claim_extract(operation)
                worker.record_result(operation, str(claim['lease_token']), result)
                edited = {rf: value+' reviewed'}
                api.edit_result(self.reviewer, operation, 1, edited)
                self.assertEqual([r['result'] for r in api.result_history(self.reviewer, operation)], [result, edited])
                self.assertEqual(api.get(self.user, operation)['source_ref'], source)
                with self.assertRaises(Conflict): api.approve(self.reviewer, operation, 1)
                approved = api.approve(self.reviewer, operation, 2)
                self.assertEqual(approved['approved_hash'], worker._fingerprint(approved))
                claim = worker.claim_dispatch(operation)
                receipt = {'externalId': 'independent\0receipt🙂'}
                worker.record_sent(operation, str(claim['lease_token']), receipt)
                self.assertEqual(api.get(self.user, operation)['receipt'], receipt)

    def test_large_non_bmp_result_remains_in_byte_contract_and_history(self):
        contract, api, worker = self.stores('long-unicode-document', 'document', 'summary')
        result = {'summary': '🙂'*15000}
        self.assertLess(len(encoded(result)), 64000)
        # Default ASCII JSON escaping exceeds the old history SQL limit, despite
        # the actual accepted UTF8 payload fitting its contract.
        self.assertGreater(len(json.dumps(result).encode()), 70000)
        op = api.submit(self.user, 'draft', 'long-document', {'document': 'source🙂'})
        claim = worker.claim_extract(op); worker.record_result(op, str(claim['lease_token']), result)
        self.assertEqual(api.get(self.user, op)['result'], result)
        self.assertEqual(api.result_history(self.reviewer, op)[0]['result'], result)
        before = api.get(self.user, op)['result_revision']
        with self.assertRaises(ValueError): api.edit_result(self.reviewer, op, before, {'summary': '🙂'*16001})
        self.assertEqual(api.get(self.user, op)['result_revision'], before)

    def test_unknown_schema_blocks_runtime_and_grants_without_rewriting(self):
        _, api, _ = self.stores('schema-admission', 'source', 'result')
        with psycopg.connect(self.admin) as c:
            original = c.execute('SELECT source_sha256 FROM workflow.schema_version').fetchone()[0]
            c.execute("UPDATE workflow.schema_version SET source_sha256='unreviewed-schema'")
        try:
            with self.assertRaises(ValueError):
                with api.connect(): pass
            with self.assertRaises(ValueError):
                with psycopg.connect(self.admin) as c: grant_runtime_roles(c, *self.roles)
            with psycopg.connect(self.admin) as c:
                self.assertEqual(c.execute('SELECT source_sha256 FROM workflow.schema_version').fetchone()[0], 'unreviewed-schema')
        finally:
            with psycopg.connect(self.admin) as c: c.execute('UPDATE workflow.schema_version SET source_sha256=%s', (original,))
