"""Private exact-action authority and write-ahead/fencing tests; no remote writes."""
from pathlib import Path
import tempfile
import time
import unittest
from uuid import uuid4

from server.maintenance.publication_store import PublicationStore
from server.maintenance.store import Store, Conflict


class PublicationLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.db = Store(Path(self.temp.name) / 'maintenance.sqlite')
        self.ledger = PublicationStore(self.db)
        self.payload = {'id': str(uuid4()), 'tenant': 'tenant-one', 'project': 'project-one',
                        'createdAt': int(time.time()), 'actions': [{'kind': 'ref', 'repository': 'owner/project',
                        'body': {'ref': 'refs/heads/atmem-upgrades/campaign/module', 'sha': 'a' * 40}}]}
        self.preview = self.ledger.save_preview('tenant-one', 'project-one', 'campaign-one', self.payload)

    def authorize(self):
        return self.ledger.authorize('tenant-one', 'project-one', self.preview['id'], self.preview['digest'], automation_accepted=True)

    def test_exact_scope_digest_automation_and_15_minute_expiry(self):
        with self.assertRaises(PermissionError):
            self.ledger.preview('tenant-two', 'project-one', self.preview['id'])
        with self.assertRaises(Conflict):
            self.ledger.authorize('tenant-one', 'project-one', self.preview['id'], 'b' * 64, automation_accepted=True)
        with self.assertRaises(Conflict):
            self.ledger.authorize('tenant-one', 'project-one', self.preview['id'], self.preview['digest'], automation_accepted=False)
        authorization = self.authorize()
        self.assertLessEqual(authorization['expiresAt'] - time.time(), 900)
        with self.db.transaction() as db:
            db.execute('UPDATE publication_authorizations SET expires=0 WHERE id=?', (authorization['id'],))
        with self.assertRaises(PermissionError):
            self.ledger.acquire('tenant-one', 'project-one', self.preview['id'], authorization['id'], self.preview['digest'])

    def test_intent_durable_before_write_cancel_fences_but_late_result_is_recorded(self):
        auth = self.authorize();pid = self.preview['id']
        lease = self.ledger.acquire('tenant-one', 'project-one', pid, auth['id'], self.preview['digest'])
        op = self.ledger.operation('tenant-one', 'project-one', pid, 0)
        self.ledger.before_write('tenant-one', 'project-one', pid, auth['id'], self.preview['digest'], lease, op)
        self.assertEqual(self.ledger.status('tenant-one', 'project-one', pid)['operations'][0]['state'], 'uncertain')
        self.ledger.cancel('tenant-one', 'project-one', pid)
        with self.assertRaises(PermissionError):
            self.ledger.before_write('tenant-one', 'project-one', pid, auth['id'], self.preview['digest'], lease, op)
        result = {'sha': 'a' * 40, 'ref': 'refs/heads/atmem-upgrades/campaign/module'}
        self.ledger.result(pid, op, 'confirmed', result)
        self.ledger.result(pid, op, 'confirmed', dict(reversed(list(result.items()))))
        self.assertEqual(self.ledger.status('tenant-one', 'project-one', pid)['operations'][0]['state'], 'confirmed')
        with self.assertRaises(Conflict):
            self.ledger.result(pid, op, 'confirmed', {'sha': 'b' * 40})

    def test_expired_coordinator_recovery_cannot_release_new_executor(self):
        auth = self.authorize();pid = self.preview['id']
        old = self.ledger.acquire('tenant-one', 'project-one', pid, auth['id'], self.preview['digest'])
        op = self.ledger.operation('tenant-one', 'project-one', pid, 0)
        self.ledger.before_write('tenant-one', 'project-one', pid, auth['id'], self.preview['digest'], old, op)
        with self.db.transaction() as db:
            db.execute('UPDATE publication_leases SET expires=0 WHERE preview=?', (pid,))
        fresh = self.ledger.acquire('tenant-one', 'project-one', pid, auth['id'], self.preview['digest'])
        self.ledger.release(pid, old)
        current = self.ledger.operation('tenant-one', 'project-one', pid, 0)
        self.assertEqual(current['state'], 'uncertain')
        with self.assertRaises(Conflict):
            self.ledger.before_write('tenant-one', 'project-one', pid, auth['id'], self.preview['digest'], old, current)
        self.ledger.before_write('tenant-one', 'project-one', pid, auth['id'], self.preview['digest'], fresh, current)

    def test_two_previews_cannot_execute_the_same_campaign_concurrently(self):
        auth = self.authorize()
        lease = self.ledger.acquire('tenant-one', 'project-one', self.preview['id'], auth['id'], self.preview['digest'])
        self.payload['id'] = str(uuid4())
        second = self.ledger.save_preview('tenant-one', 'project-one', 'campaign-one', self.payload)
        other = self.ledger.authorize('tenant-one', 'project-one', second['id'], second['digest'], automation_accepted=True)
        with self.assertRaisesRegex(Conflict, 'campaign'):
            self.ledger.acquire('tenant-one', 'project-one', second['id'], other['id'], second['digest'])
        self.ledger.release(self.preview['id'], lease)
        self.ledger.acquire('tenant-one', 'project-one', second['id'], other['id'], second['digest'])

    def test_unknown_pr_outcome_cannot_be_blindly_retried_and_branch_claims_are_scoped(self):
        self.payload['id'] = str(uuid4());self.payload['actions'][0]['kind'] = 'pull'
        p = self.ledger.save_preview('tenant-one', 'project-one', 'campaign-one', self.payload)
        auth = self.ledger.authorize('tenant-one', 'project-one', p['id'], p['digest'], automation_accepted=True)
        lease = self.ledger.acquire('tenant-one', 'project-one', p['id'], auth['id'], p['digest'])
        op = self.ledger.operation('tenant-one', 'project-one', p['id'], 0)
        self.ledger.result(p['id'], op, 'uncertain')
        op = self.ledger.operation('tenant-one', 'project-one', p['id'], 0)
        with self.assertRaises(Conflict):
            self.ledger.before_write('tenant-one', 'project-one', p['id'], auth['id'], p['digest'], lease, op)
        self.ledger.claim('tenant-one', 'project-one', 'campaign-one', 17, 'atmem-upgrades/campaign/module', 'private-nonce', 'a' * 40)
        with self.assertRaises(Conflict):
            self.ledger.claim('tenant-two', 'project-two', 'campaign-other', 17, 'atmem-upgrades/campaign/module', 'other-nonce', 'a' * 40)
        self.assertIsNone(self.ledger.owned('tenant-two', 'project-one', 'campaign-one', 17, 'atmem-upgrades/campaign/module'))
