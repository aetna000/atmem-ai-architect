"""Real restricted SQL/crypto/lease tests; extraction/source gates are fixtures."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import sys
import threading
import unittest
import uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'.local/azure-runtime-sdk'),str(ROOT/'tests/runtime')]
import psycopg
from psycopg.conninfo import conninfo_to_dict
import enterprise_auth_postgres as fixture
from enterprise_extraction_cache import ExtractionCache,ExtractionLeaseLost,initialize_extraction_cache,grant_extraction_runtime
from enterprise_identity import CompanyPrincipal
from enterprise_sources import SourceDenied,SourceUnavailable,SourceChanged

REVISION='a'*64  # Explicit synthetic decoder revision, not the actual parser image.


class ExtractionReuse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base=fixture.EnterpriseCredentialTransactions;base.setUpClass()
        cls.owner_dsn,cls.app_dsn,cls.key=base.owner_dsn,base.app_dsn,base.key
        with psycopg.connect(cls.owner_dsn)as conn:
            initialize_extraction_cache(conn);grant_extraction_runtime(conn,conninfo_to_dict(cls.app_dsn)['user'])

    def setUp(self):
        fixture.EnterpriseCredentialTransactions.setUp(self)
        self.cache=ExtractionCache(self.store,self.account,REVISION)
        self.raw=b'SYNTHETIC PRIVATE DOCUMENT';self.calls=[];self.gates=[];self.allowed=True
        def extract(raw,mime):self.calls.append((hashlib.sha256(raw).hexdigest(),mime));return raw.decode()
        self.extract=extract
        self.decoder=self.cache.wrap(extract,lambda:self.store.authorize(self.principal))

    def source(self):
        self.gates.append(True)
        if not self.allowed:raise SourceDenied('source_access_denied')

    def decode(self,raw=None):return self.decoder.from_source(raw or self.raw,'text/plain',self.source)
    def rows(self):
        with psycopg.connect(self.owner_dsn,row_factory=psycopg.rows.dict_row)as conn:
            return conn.execute('SELECT * FROM enterprise_extractions.documents WHERE account_id=%s',(self.account,)).fetchall()

    def test_warm_reuse_keeps_ciphertext_and_keys_private(self):
        self.assertEqual(self.decode(),self.raw.decode());self.assertEqual(self.decode(),self.raw.decode())
        self.assertEqual(len(self.calls),1);self.assertGreaterEqual(len(self.gates),6)
        row=self.rows()[0];self.assertNotIn(self.raw.decode(),row['value_ciphertext'])
        self.assertNotEqual(row['content_key'],hashlib.sha256(self.raw).hexdigest())
        self.assertNotIn('sha256',row)

    def test_new_bytes_mime_or_parser_revision_are_not_cache_hits(self):
        self.decode();self.decode(b'CHANGED PRIVATE DOCUMENT')
        self.decoder.from_source(self.raw,'application/octet-stream',self.source)
        other=ExtractionCache(self.store,self.account,'b'*64).wrap(self.extract,lambda:self.store.authorize(self.principal))
        other.from_source(self.raw,'text/plain',self.source)
        self.assertEqual(len(self.calls),4)

    def test_other_company_cannot_reuse_the_first_company_derivative(self):
        self.decode();account=uuid.uuid4().hex
        principal=CompanyPrincipal(account,self.principal.issuer,self.principal.subject,self.principal.expires_at)
        with psycopg.connect(self.owner_dsn)as conn:conn.execute('INSERT INTO enterprise_auth.memberships VALUES(%s,%s,%s,%s,true)',(account,principal.key,principal.issuer,principal.subject))
        other=ExtractionCache(self.store,account,REVISION)
        other.wrap(self.extract,lambda:self.store.authorize(principal)).from_source(self.raw,'text/plain',self.source)
        self.assertEqual(len(self.calls),2)
        self.assertNotEqual(self.cache.identity(self.raw,'text/plain')[0],other.identity(self.raw,'text/plain')[0])

    def test_source_denial_and_outage_with_warm_text_are_not_fallbacks(self):
        self.decode();self.allowed=False
        with self.assertRaises(SourceDenied):self.decode()
        def outage():raise SourceUnavailable('source_request_failed')
        with self.assertRaises(SourceUnavailable):self.decoder.from_source(self.raw,'text/plain',outage)
        self.assertEqual(len(self.calls),1)

    def test_live_company_membership_rechecked_on_hit(self):
        self.decode()
        with psycopg.connect(self.owner_dsn)as conn:conn.execute('UPDATE enterprise_auth.memberships SET active=false WHERE account_id=%s AND principal_key=%s',(self.account,self.principal.key))
        with self.assertRaises(SourceDenied):self.decode()
        self.assertEqual(len(self.calls),1)

    def test_plain_decoder_call_cannot_bypass_the_source_validation_contract(self):
        with self.assertRaisesRegex(SourceUnavailable,'source_validation_required'):self.decoder(self.raw,'text/plain')
        self.assertEqual(self.calls,[]);self.assertEqual(self.rows(),[])

    def test_source_revoked_or_changed_during_extraction_is_not_published(self):
        for changed in [False,True]:
            state={'changed':False}
            def source():
                if state['changed']:raise (SourceChanged('source_document_changed')if changed else SourceDenied('source_access_denied'))
            def extract(raw,mime):state['changed']=True;return self.raw.decode()
            decoder=self.cache.wrap(extract,lambda:self.store.authorize(self.principal))
            with self.subTest(changed=changed),self.assertRaises(SourceUnavailable):decoder.from_source(self.raw,'text/plain',source)
            self.assertEqual(self.rows(),[])

    def test_per_file_launcher_rechecks_company_authority_before_releasing_input(self):
        from enterprise_native import DocumentExecutor
        calls=[]
        owner_dsn,account,principal=self.owner_dsn,self.account,self.principal
        class Launch:
            def __call__(self,raw,mime):raise AssertionError('Live authority must reach the per-file launcher')
            def from_source(self,raw,mime,guard):
                calls.append('waiting-for-workload')
                # An administrator removes the employee while a native job is
                # starting. Do not release its source bytes or cache a derivative.
                with psycopg.connect(owner_dsn)as conn:
                    conn.execute('UPDATE enterprise_auth.memberships SET active=false WHERE account_id=%s AND principal_key=%s',(account,principal.key))
                guard()
                calls.append('released-private-input')
                raise AssertionError('Revoked job continued')
        decoder=self.cache.wrap(DocumentExecutor(REVISION,Launch()),lambda:self.store.authorize(self.principal))
        with self.assertRaises(SourceDenied):decoder.from_source(self.raw,'text/plain',self.source)
        self.assertEqual(calls,['waiting-for-workload']);self.assertEqual(self.rows(),[])

    def test_concurrent_misses_share_one_extractor_without_holding_a_sql_lock(self):
        entered=threading.Event();release=threading.Event();calls=[]
        def extract(raw,mime):calls.append(True);entered.set();release.wait(5);return self.raw.decode()
        decoder=self.cache.wrap(extract,lambda:self.store.authorize(self.principal))
        with ThreadPoolExecutor(max_workers=2)as pool:
            first=pool.submit(decoder.from_source,self.raw,'text/plain',self.source)
            self.assertTrue(entered.wait(2))
            second=pool.submit(decoder.from_source,self.raw,'text/plain',self.source)
            try:
                # The committed building lease is observable while parsing, so a
                # second process can wait without a parser-length SQL transaction.
                self.assertEqual(self.rows()[0]['state'],'building');self.assertEqual(len(calls),1)
            finally:release.set()
            self.assertEqual(first.result(timeout=5),self.raw.decode());self.assertEqual(second.result(timeout=5),self.raw.decode())
        self.assertEqual(len(calls),1)

    def test_expired_build_recovery_fences_prior_publication_and_abandon(self):
        key,digest,mime=self.cache.identity(self.raw,'text/plain');_,old=self.cache.claim(key)
        with psycopg.connect(self.owner_dsn)as conn:conn.execute("UPDATE enterprise_extractions.documents SET lease_until=clock_timestamp()-interval '1 second',expires_at=clock_timestamp()-interval '1 second'WHERE account_id=%s",(self.account,))
        state,current=self.cache.claim(key);self.assertEqual(state,'claimed');self.assertNotEqual(old,current)
        value={'sha256':digest,'mediaType':mime,'text':self.raw.decode()}
        with self.assertRaises(ExtractionLeaseLost):self.cache.publish(key,old,value)
        self.cache.abandon(key,old);self.cache.publish(key,current,value)
        self.assertEqual(self.decode(),self.raw.decode());self.assertEqual(self.calls,[])

    def test_inflight_wait_is_bounded(self):
        cache=ExtractionCache(self.store,self.account,REVISION,wait_seconds=1)
        key,_,_=cache.identity(self.raw,'text/plain');cache.claim(key)
        with self.assertRaisesRegex(SourceUnavailable,'document_extraction_busy'):
            cache.wrap(self.extract,lambda:self.store.authorize(self.principal)).from_source(self.raw,'text/plain',self.source)
        self.assertEqual(self.calls,[])

    def test_parser_failure_and_invalid_text_leave_no_ready_derivative(self):
        for value in ['', '\x00secret', 'x'*200001, None]:
            decoder=self.cache.wrap(lambda raw,mime:value,lambda:self.store.authorize(self.principal))
            with self.subTest(value_type=type(value).__name__),self.assertRaises(SourceUnavailable):decoder.from_source(self.raw,'text/plain',self.source)
            self.assertEqual(self.rows(),[])

    def test_ciphertext_swap_or_corruption_is_rejected_without_reparsing(self):
        self.decode();self.decode(b'OTHER PRIVATE DOCUMENT');rows=self.rows()
        key,digest,mime=self.cache.identity(self.raw,'text/plain')
        foreign=next(row for row in rows if row['content_key']!=key)
        with self.assertRaises(SourceDenied):self.cache.open(key,digest,mime,foreign['value_ciphertext'])
        with psycopg.connect(self.owner_dsn)as conn:conn.execute("UPDATE enterprise_extractions.documents SET value_ciphertext='corrupt'WHERE account_id=%s AND content_key=%s",(self.account,key))
        with self.assertRaises(SourceDenied):self.decode()
        self.assertEqual(len(self.calls),2)

    def test_expiry_forces_fresh_parse_and_purge_is_company_scoped_and_bounded(self):
        self.decode()
        with psycopg.connect(self.owner_dsn)as conn:conn.execute("UPDATE enterprise_extractions.documents SET expires_at=clock_timestamp()-interval '1 second'WHERE account_id=%s",(self.account,))
        self.decode();self.assertEqual(len(self.calls),2)
        self.decode(b'SECOND DOCUMENT')
        with psycopg.connect(self.owner_dsn)as conn:conn.execute("UPDATE enterprise_extractions.documents SET expires_at=clock_timestamp()-interval '1 second'WHERE account_id=%s",(self.account,))
        self.assertEqual(self.cache.purge(1),1);self.assertEqual(len(self.rows()),1)
        self.assertEqual(ExtractionCache(self.store,'other-company',REVISION).purge(),0)
        self.assertEqual(self.cache.purge(),1)


if __name__=='__main__':unittest.main(verbosity=2)
