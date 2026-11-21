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

STORAGE='''<section id="data-storage"><div role="option" aria-selected="true" data-value="Iowa (us-central1)">Iowa</div><div role="option" aria-selected="false" data-value="Sydney (australia-southeast1)">Sydney</div><table><tr><th>Standard storage</th><th>Nearline storage</th></tr><tr><td>$0.000027397 / 1 gibibyte hour, per 1 month / account</td><td>$0.000013699 / 1 gibibyte hour</td></tr></table><p><b>Dual-region</b></p><table><tr><td>$999</td></tr></table></section>'''

class GoogleStoragePublicTests(unittest.TestCase):
    def test_public_iowa_rate_has_explicit_unit_conversion_and_exclusions(self):
        from server.pricing import parse_google_storage_public
        q=parse_google_storage_public(STORAGE,'us-central1','https://cloud.google.com/storage/pricing')
        self.assertAlmostEqual(q['price'],.000027397*730)
        self.assertEqual(q['unit'],'GiB-month');self.assertEqual(q['hoursPerMonth'],730)
        self.assertIn('Operations',q['coverage']);self.assertEqual(len(q['sourceSha256']),64)

    def test_listed_region_is_not_selected_region_and_units_must_match(self):
        from server.pricing import parse_google_storage_public
        wrong=STORAGE.replace('aria-selected="true"','aria-selected="false"',1).replace('aria-selected="false" data-value="Sydney','aria-selected="true" data-value="Sydney')
        for html,region in [(wrong,'us-central1'),(STORAGE,'australia-southeast1'),(STORAGE.replace('gibibyte hour','gigabyte hour'),'us-central1'),(STORAGE.replace('Standard storage','Rapid storage'),'us-central1')]:
            with self.subTest(region=region),self.assertRaises(ValueError):parse_google_storage_public(html,region,'fixture')

    def test_public_quote_works_without_catalog_credentials(self):
        from server.pricing import storage_quote,parse_google_storage_public
        q=parse_google_storage_public(STORAGE,'us-central1','https://cloud.google.com/storage/pricing')
        with patch.dict('os.environ',{},clear=True),patch('server.pricing._google_storage_public',return_value=q):
            self.assertTrue(storage_quote('gcp','us-central1')['available'])
            self.assertFalse(storage_quote('gcp','us-east4')['available'])
