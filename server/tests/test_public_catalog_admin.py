import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src/runtime'))
from public_catalog_admin import encode_catalog,initial_catalog,operate,parser,read_article,token_headers
from public_faq import CatalogChanged,PublicFaq,parse_catalog

class CatalogAdminTests(unittest.TestCase):
    def test_initialization_preserves_all_twenty_public_files_and_full_text(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);texts={}
            for i in range(20):texts['help-'+str(i)]='Public help '+str(i)+' '+('é'*14000);(folder/('help-'+str(i)+'.txt')).write_text(texts['help-'+str(i)],encoding='utf-8')
            current=parse_catalog(initial_catalog(folder),'initial')
            self.assertEqual(len(current.articles),20);self.assertEqual(len({a.id for a in current.articles}),20);self.assertEqual({a.title.replace(' ','-'):a.text for a in current.articles},texts)
            self.assertEqual([a.id for a in current.articles],[a.id for a in parse_catalog(initial_catalog(folder),'again').articles])
    def test_bad_files_fail_and_same_basename_articles_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);file=folder/'help.txt';file.write_text('Public help')
            (folder/'help.md').write_text('Another article with the same ID')
            duplicate_names=parse_catalog(initial_catalog(folder),'initial');self.assertEqual(len(duplicate_names.articles),2);self.assertEqual(len({a.id for a in duplicate_names.articles}),2)
            (folder/'help.md').unlink();(folder/'image.png').write_bytes(b'not text')
            with self.assertRaises(ValueError):initial_catalog(folder)
            (folder/'image.png').unlink();(folder/'linked.txt').symlink_to(file)
            with self.assertRaises(ValueError):initial_catalog(folder)
            with self.assertRaises(ValueError):read_article(folder/'linked.txt')
            (folder/'linked.txt').unlink();file.write_text('é'*15001,encoding='utf-8')
            with self.assertRaises(ValueError):read_article(file)
            file.write_bytes(b'\xff')
            with self.assertRaises(UnicodeError):read_article(file)
    def test_cli_create_update_delete_changes_retrieval_with_exact_version_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);file=folder/'refund.txt';file.write_text('Refunds are accepted within thirty days after purchase.')
            state={'raw':None,'version':0};storage=Mock()
            def load():return parse_catalog(state['raw'],'"'+str(state['version'])+'"')
            def save(raw,expected):
                current=None if state['raw'] is None else '"'+str(state['version'])+'"'
                if expected!=current:raise CatalogChanged()
                state['raw']=raw;state['version']+=1;return '"'+str(state['version'])+'"'
            storage.load.side_effect=load;storage.save.side_effect=save
            args=parser().parse_args(['--provider','ibm','--bucket','public-catalog','--region','au-syd','init','--directory',temp,'--expected-version','create','--confirm-write'])
            self.assertEqual(operate(args,storage)['articleCount'],1);identifier=load().articles[0].id
            file.write_text('Refunds are accepted within fourteen days after purchase.')
            args=parser().parse_args(['--provider','ibm','--bucket','public-catalog','--region','au-syd','upsert','--id',identifier,'--title','Refund policy','--file',str(file),'--expected-version','"1"','--confirm-write'])
            result=operate(args,storage);self.assertEqual(result['storageVersion'],'"2"');self.assertEqual(load().articles[0].text,file.read_text())
            storage.save.reset_mock()
            with self.assertRaises(CatalogChanged):operate(args,storage)
            storage.save.assert_not_called()
            args=parser().parse_args(['--provider','ibm','--bucket','public-catalog','--region','au-syd','delete','--id',identifier,'--expected-version','"2"','--confirm-write'])
            self.assertEqual(operate(args,storage)['articleCount'],0);model=Mock();self.assertTrue(PublicFaq(load,model)('refund')['abstained']);model.assert_not_called()
    def test_missing_write_intent_and_stale_reviewed_version_never_mutate_storage(self):
        storage=Mock();args=parser().parse_args(['--provider','gcp','--bucket','public-catalog','--region','australia-southeast1','delete','--id','refund','--expected-version','1'])
        with self.assertRaises(PermissionError):operate(args,storage)
        storage.load.assert_not_called();storage.save.assert_not_called()
        storage.load.return_value=parse_catalog(encode_catalog([]),'2');args.confirm_write=True
        with self.assertRaises(CatalogChanged):operate(args,storage)
        storage.save.assert_not_called()
    def test_token_file_permissions_and_shape_are_checked_without_echoing_credential(self):
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/'editor-token';file.write_text('fixture-short-lived-token');file.chmod(0o600)
            self.assertEqual(token_headers(file),{'Authorization':'Bearer fixture-short-lived-token'})
            file.chmod(0o644)
            with self.assertRaises(PermissionError):token_headers(file)
            file.chmod(0o600);file.write_text('token with whitespace')
            with self.assertRaises(PermissionError):token_headers(file)
            link=Path(temp)/'link';link.symlink_to(file)
            with self.assertRaises(PermissionError):token_headers(link)

if __name__=='__main__':unittest.main()
