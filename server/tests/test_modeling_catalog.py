"""Fixed engine research and authoring resources, never caller-controlled paths."""
from hashlib import sha256
import unittest
from server import modeling_catalog


class ModelingCatalogTests(unittest.TestCase):
    def test_grammar_pages_reconstruct_exact_engine_resource(self):
        first=modeling_catalog.read('modeling-grammar')
        raw=(modeling_catalog.ROOT/'engineering-model-v1.md').read_bytes()
        self.assertEqual(first['sha256'],sha256(raw).hexdigest())
        pages=[first['text']]
        offset=first['nextOffset']
        while offset is not None:
            page=modeling_catalog.read('modeling-grammar',offset,first['sha256'])
            self.assertEqual(page['sha256'],first['sha256'])
            pages.append(page['text'])
            offset=page['nextOffset']
        self.assertEqual(''.join(pages),raw.decode())
        self.assertEqual(first['representationSha256'],sha256(raw).hexdigest())
        self.assertEqual(first['evidenceLevel'],'engine_research_inventory')

    def test_no_arbitrary_paths_or_unpinned_continuations(self):
        for reference in ['../../etc/passwd','modeling-family-unknown','https://example.com']:
            with self.assertRaises(ValueError):modeling_catalog.read(reference)
        with self.assertRaises(ValueError):modeling_catalog.read('modeling-grammar',5000)
        with self.assertRaises(ValueError):modeling_catalog.read('modeling-grammar',5000,'0'*64)
        with self.assertRaises(ValueError):modeling_catalog.read('modeling-grammar',999999,'0'*64)

    def test_catalog_exposes_grammar_and_each_registered_family(self):
        rows=modeling_catalog.catalog()
        self.assertIn('modeling-grammar',[row['id']for row in rows])
        for row in rows:
            value=modeling_catalog.read(row['id'])
            self.assertTrue(value['text'])
            self.assertEqual(value['id'],row['id'])
            self.assertLessEqual(len(value['text']),modeling_catalog.PAGE)
