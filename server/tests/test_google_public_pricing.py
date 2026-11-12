import unittest
from unittest.mock import patch
from server.pricing import parse_google_public,google_public_quote

RUN='Services (Requests-based billing)<table><tr><td>CPU (per vCPU-second)</td><td>Active time</td><td>$0.000024</td><td>$0.00001992</td></tr><tr><td>Memory (per GiB-second)</td><td>Active time</td><td>$0.0000025</td></tr><tr><td>Requests (per 1,000,000)</td><td>N/A</td><td>$0.40</td></tr></table>'
SQL='Enterprise Edition - N4 machine series Iowa (us-central1)<table><tr><td>vCPUs</td><td>$0.0413 / 1 hour</td><td>$0.030975 / 1 hour</td></tr><tr><td>Memory</td><td>$0.007 / 1 gibibyte hour</td></tr></table>'

class GooglePublicPricingTests(unittest.TestCase):
    def test_public_default_meter_units_exclude_discount_columns(self):
        run=parse_google_public(RUN,'cloud-run','https://cloud.google.com/run/pricing')
        self.assertEqual(run['meters']['cpu'],{'price':.000024,'unit':'vCPU-seconds'})
        self.assertEqual(run['meters']['requests']['price'],.4)
        sql=parse_google_public(SQL,'cloud-sql','https://cloud.google.com/sql/pricing')
        self.assertEqual(sql['meters']['memory'],{'price':.007,'unit':'GiB-hours'})

    def test_missing_edition_region_or_meter_fails_closed(self):
        for source,service in [(RUN.replace('CPU (per vCPU-second)','CPU'),'cloud-run'),(SQL.replace('Iowa (us-central1)','Sydney'),'cloud-sql'),(SQL.replace('Enterprise Edition - N4','Enterprise Plus'),'cloud-sql')]:
            with self.subTest(service=service),self.assertRaises(ValueError):parse_google_public(source,service,'fixture')

    def test_reference_must_be_explicit_and_cannot_replace_selected_region(self):
        with patch('server.pricing._google_public',return_value={'region':'us-central1'}):
            self.assertTrue(google_public_quote('cloud-run','To be selected',True)['planningReference'])
            self.assertFalse(google_public_quote('cloud-run','us-central1')['planningReference'])
            for region,reference in [('',False),('australia-southeast1',True),('us-east4',False)]:
                with self.assertRaises(ValueError):google_public_quote('cloud-run',region,reference)
