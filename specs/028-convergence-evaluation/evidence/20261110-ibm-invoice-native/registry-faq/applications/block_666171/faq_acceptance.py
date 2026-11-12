"""Local public-only lifecycle/HTTP/transport checks; not cloud IAM or model quality."""
from faq_core_acceptance import PublicFaqCoreTests
from faq_http_acceptance import PublicFaqHttpTests
from faq_catalog_admin_acceptance import CatalogAdminTests
from faq_catalog_store_acceptance import HttpCatalogContractTests,ConditionalConcurrencyTests
import unittest
if __name__=="__main__":unittest.main()
