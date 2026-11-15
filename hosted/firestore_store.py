"""Firestore transaction adapter. Never falls back to memory or local files."""
import os
import re
import random
import time


class FirestoreTransactions:
    def __init__(self, client, *, namespace='architect'):
        if not re.fullmatch(r'[a-z][a-z0-9_]{2,40}', namespace):
            raise ValueError('Use an explicit bounded collection namespace')
        self.client, self.namespace = client, namespace

    @classmethod
    def configured(cls, project, database):
        if not project or not database:
            raise ValueError('Explicit Google project and database are required')
        if os.environ.get('K_SERVICE') and os.environ.get('FIRESTORE_EMULATOR_HOST'):
            raise ValueError('Cloud service cannot use the emulator')
        from google.cloud import firestore
        return cls(firestore.Client(project=project, database=database))

    def transaction(self, callback):
        from google.cloud import firestore
        from google.api_core.exceptions import Aborted
        @firestore.transactional
        def apply(transaction):
            return callback(_Transaction(self.client, transaction, self.namespace))
        # The SDK retries commit aborts, but lets aborts raised during reads
        # escape. Those transactions did not commit. Retry the complete pure
        # callback; never retry an ambiguous commit/network exception here.
        for attempt in range(5):
            try:return apply(self.client.transaction(max_attempts=10))
            except Aborted:
                if attempt==4:raise
                time.sleep(random.uniform(.02,.08)*(2**attempt))


class _Transaction:
    def __init__(self, client, transaction, namespace):
        self.client, self.transaction, self.namespace = client, transaction, namespace
        self.written = False

    def _reference(self, collection, key):
        if not re.fullmatch(r'[a-z][a-z0-9_]{1,40}', collection) or not re.fullmatch(r'[a-z0-9_-]{1,200}', key):
            raise ValueError('Unrecognized internal document path')
        return self.client.collection(self.namespace + '_' + collection).document(key)

    def get(self, collection, key):
        if self.written:
            raise ValueError('All transaction reads must precede writes')
        from google.api_core.retry import Retry, if_exception_type
        from google.api_core.exceptions import ServiceUnavailable, DeadlineExceeded
        # An aborted transaction cannot recover by retrying the same document
        # read for minutes. Let the outer transaction restart it immediately.
        retry=Retry(predicate=if_exception_type(ServiceUnavailable,DeadlineExceeded),initial=.05,maximum=.5,timeout=5)
        snapshot = self._reference(collection, key).get(transaction=self.transaction,retry=retry,timeout=5)
        return snapshot.to_dict() if snapshot.exists else None

    def set(self, collection, key, record):
        self.transaction.set(self._reference(collection, key), record); self.written = True

    def create(self, collection, key, record):
        self.transaction.create(self._reference(collection, key), record); self.written = True

    def delete(self, collection, key):
        self.transaction.delete(self._reference(collection,key));self.written=True
