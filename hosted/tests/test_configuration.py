import unittest
from hosted.auth import Identity, Forbidden, Unauthorized
from hosted.configuration import BillingConfiguration, DEFAULT_POLICY
from hosted.credits import Conflict, CreditError
from hosted.tests.test_credits import AtomicTestStore


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.store=AtomicTestStore();self.config=BillingConfiguration(self.store)
        self.admin=Identity('owner','taghia.javad@gmail.com','google.com',True)
        self.user=Identity('ordinary','person@example.test','google.com',True)

    def test_owner_defaults_and_arbitrary_whole_cent_topup(self):
        self.assertEqual(self.config.current()['welcomeMicros'],5_000_000)
        self.assertEqual(self.config.purchase_quote(100)['creditMicros'],1_000_000)
        self.assertEqual(self.config.purchase_quote(137)['creditMicros'],1_370_000)
        self.assertFalse(self.config.current()['platformSpendingEnabled'])
        for amount in [99,True,1.5,100_000_000]:
            with self.assertRaises(CreditError):self.config.purchase_quote(amount)

    def test_only_verified_google_admin_can_edit_and_client_roles_cannot_help(self):
        for identity in [self.user,Identity('other','taghia.javad@gmail.com','password',True),Identity('other','taghia.javad@gmail.com','google.com',False)]:
            with self.assertRaises(Forbidden):self.config.update(identity,1,{'welcomeMicros':9})
        with self.assertRaises(CreditError):self.config.update(self.admin,1,{'admin':True})
        self.assertEqual(self.config.current()['revision'],1)

    def test_config_updates_require_revision_are_audited_and_validate_spend_budget(self):
        with self.assertRaises(CreditError):self.config.update(self.admin,1,{'platformSpendingEnabled':True})
        result=self.config.update(self.admin,1,{'minimumPurchaseCents':200,'welcomeMicros':6_000_000})
        self.assertEqual(result['revision'],2)
        with self.assertRaises(Conflict):self.config.update(self.admin,1,{'welcomeMicros':1})
        self.assertEqual(len([k for k in self.store.data if k[0]=='audit']),1)

    def test_verified_claims_need_google_and_verified_email(self):
        claims={'uid':'owner','email':'TAGHIA.JAVAD@GMAIL.COM','email_verified':True,'firebase':{'sign_in_provider':'google.com'}}
        self.assertTrue(Identity.from_verified_claims(claims).admin)
        for patch in [{'email_verified':False},{'firebase':{'sign_in_provider':'custom'}},{'email':'somebody@example.test'}]:
            value={**claims,**patch}
            if 'email' in patch:self.assertFalse(Identity.from_verified_claims(value).admin)
            else:
                with self.assertRaises(Unauthorized):Identity.from_verified_claims(value)
