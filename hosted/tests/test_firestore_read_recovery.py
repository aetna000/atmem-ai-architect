"""Read aborts restart pure transactions; uncertain commits never replay here."""
import unittest
from unittest.mock import MagicMock,patch
from google.api_core.exceptions import Aborted,DeadlineExceeded
from hosted.firestore_store import FirestoreTransactions

class ReadRecoveryTests(unittest.TestCase):
 def test_read_abort_restarts_with_a_new_transaction(self):
  client=MagicMock();first,second=object(),object();client.transaction.side_effect=[first,second]
  attempts=[]
  def transactional(callback):
   def run(transaction):
    attempts.append(transaction)
    if transaction is first:raise Aborted('Read transaction aborted')
    return 'committed-once'
   return run
  with patch('google.cloud.firestore.transactional',side_effect=transactional),patch('hosted.firestore_store.time.sleep'):
   self.assertEqual(FirestoreTransactions(client).transaction(lambda tx:None),'committed-once')
  self.assertEqual(attempts,[first,second])
 def test_uncertain_deadline_is_not_replayed(self):
  client=MagicMock()
  def transactional(callback):
   def run(transaction):raise DeadlineExceeded('Commit outcome unknown')
   return run
  with patch('google.cloud.firestore.transactional',side_effect=transactional):
   with self.assertRaises(DeadlineExceeded):FirestoreTransactions(client).transaction(lambda tx:None)
  self.assertEqual(client.transaction.call_count,1)
