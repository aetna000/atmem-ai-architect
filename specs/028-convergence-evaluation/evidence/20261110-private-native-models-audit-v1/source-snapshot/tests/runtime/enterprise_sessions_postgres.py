"""Real restricted SQL session lifecycle/concurrency; no live IdP/cloud."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import time
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'.local/azure-runtime-sdk'),str(ROOT/'tests/runtime')]
import psycopg
from psycopg.conninfo import conninfo_to_dict
import enterprise_auth_postgres as fixture_module
from enterprise_auth_store import digest
from enterprise_sessions import CompanySessions
from enterprise_sources import SourceDenied

class BrowserSessionTransactions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture=fixture_module.EnterpriseCredentialTransactions;fixture.setUpClass();cls.owner_dsn=fixture.owner_dsn;cls.app_dsn=fixture.app_dsn;cls.key=fixture.key
    def setUp(self):fixture_module.EnterpriseCredentialTransactions.setUp(self);self.sessions=CompanySessions(self.store)
    def test_restart_encryption_and_session_rotation_preserve_browser_not_old_cookie(self):
        first=self.sessions.create(self.principal);actor=self.sessions.authenticate(first.token)
        self.assertEqual(actor.csrf,first.csrf);actor.require_csrf(first.csrf)
        with self.assertRaises(SourceDenied):actor.require_csrf('SYNTHETIC_WRONG_CSRF_01234567890123456789')
        second=self.sessions.create(self.principal,first.token);replacement=CompanySessions(self.store);self.assertEqual(replacement.authenticate(second.token).browser_nonce,actor.browser_nonce)
        with self.assertRaises(SourceDenied):replacement.authenticate(first.token)
        with self.assertRaises(SourceDenied):replacement.authenticate(second.token).require_csrf(first.csrf)
        with psycopg.connect(self.owner_dsn)as conn:rows=conn.execute('SELECT session_sha256,csrf_sha256,nonce_ciphertext FROM enterprise_auth.sessions WHERE account_id=%s',(self.account,)).fetchall()
        for secret in [first.token,first.csrf,actor.browser_nonce]:self.assertNotIn(secret,str(rows))

    def test_cross_session_cipher_swap_and_expired_cookie_fail_closed(self):
        first=self.sessions.create(self.principal);second=self.sessions.create(self.other)
        with psycopg.connect(self.owner_dsn)as conn:
            encrypted=conn.execute('SELECT nonce_ciphertext FROM enterprise_auth.sessions WHERE session_sha256=%s',(digest(first.token),)).fetchone()[0]
            conn.execute('UPDATE enterprise_auth.sessions SET nonce_ciphertext=%s WHERE session_sha256=%s',(encrypted,digest(second.token)))
        with self.assertRaises(SourceDenied):self.sessions.authenticate(second.token)
        with psycopg.connect(self.owner_dsn)as conn:conn.execute("UPDATE enterprise_auth.sessions SET expires_at=clock_timestamp()-interval '1 second'WHERE session_sha256=%s",(digest(first.token),))
        with self.assertRaises(SourceDenied):self.sessions.authenticate(first.token)

    def test_concurrent_sessions_are_bounded_and_revocation_is_live(self):
        with ThreadPoolExecutor(max_workers=8)as pool:list(pool.map(lambda _:self.sessions.create(self.principal),range(20)))
        with psycopg.connect(self.owner_dsn)as conn:
            count=conn.execute('SELECT count(*)FROM enterprise_auth.sessions WHERE account_id=%s AND revoked_at IS NULL',(self.account,)).fetchone()[0]
        self.assertEqual(count,10)
        current=self.sessions.create(self.principal)
        with psycopg.connect(self.owner_dsn)as conn:conn.execute('UPDATE enterprise_auth.memberships SET active=false WHERE account_id=%s AND principal_key=%s',(self.account,self.principal.key))
        with self.assertRaises(SourceDenied):self.sessions.authenticate(current.token)

    def test_opposite_profile_rotations_progress_without_cross_owner_deadlock(self):
        alice=[self.sessions.create(self.principal)for _ in range(10)];bob=[self.sessions.create(self.other)for _ in range(10)]
        settings=conninfo_to_dict(self.app_dsn)
        # Hold only the two owned old session rows. Release after both independent
        # requests reach a native lock wait; do not patch application SQL/code.
        with psycopg.connect(self.owner_dsn)as owner:
            owner.execute('SELECT session_sha256 FROM enterprise_auth.sessions WHERE session_sha256=ANY(%s)ORDER BY session_sha256 FOR UPDATE',([digest(alice[0].token),digest(bob[0].token)],)).fetchall()
            with ThreadPoolExecutor(max_workers=2)as pool:
                first=pool.submit(self.sessions.create,self.principal,bob[0].token);second=pool.submit(self.sessions.create,self.other,alice[0].token)
                deadline=time.monotonic()+1.5
                with psycopg.connect(self.owner_dsn,autocommit=True)as monitor:
                    while True:
                        waiting=monitor.execute("SELECT count(*)FROM pg_stat_activity WHERE datname=current_database()AND usename=%s AND wait_event_type='Lock'",(settings['user'],)).fetchone()[0]
                        if waiting>=2:break
                        if time.monotonic()>deadline:raise AssertionError('Owned profile-switch requests did not reach their native lock waits')
                        time.sleep(.01)
                owner.commit();a=first.result(timeout=5);b=second.result(timeout=5)
        self.assertEqual(self.sessions.authenticate(a.token).principal,self.principal);self.assertEqual(self.sessions.authenticate(b.token).principal,self.other)

if __name__=='__main__':unittest.main()
