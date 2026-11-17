"""Transactional aggregate reservations. Unknown spend remains charged at its reserved cap."""
import time

from .store import Conflict, digest


class Budget:
    def __init__(self, store):
        self.store = store
        with store.transaction() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS budget_reservations (
                tenant TEXT NOT NULL, project TEXT NOT NULL, owner TEXT NOT NULL,
                job TEXT NOT NULL, fingerprint TEXT NOT NULL, cap INTEGER NOT NULL,
                charged INTEGER NOT NULL, state TEXT NOT NULL, created REAL NOT NULL,
                PRIMARY KEY(tenant,job));
            ''')

    def reserve(self, tenant, project, owner, job, fingerprint, cap, *, tenant_limit, project_limit, owner_limit):
        for value in [cap, tenant_limit, project_limit, owner_limit]:
            if type(value) is not int or value < 0:
                raise ValueError('Money uses nonnegative integer micro-USD')
        with self.store.transaction() as db:
            self.store._load(db, tenant, project)
            prior = db.execute('SELECT * FROM budget_reservations WHERE tenant=? AND job=?', (tenant, job)).fetchone()
            identity = digest([project, owner, fingerprint, cap])
            if prior:
                if prior['fingerprint'] != identity:
                    raise Conflict('Budget idempotency key reused for different work')
                if prior['state'] != 'reserved':
                    raise Conflict('Settled or unknown work cannot be replayed')
                return
            for clause, params, limit in [
                ('tenant=?', (tenant,), tenant_limit),
                ('tenant=? AND project=?', (tenant, project), project_limit),
                ('owner=?', (owner,), owner_limit),
            ]:
                used = db.execute('SELECT COALESCE(SUM(charged),0) FROM budget_reservations WHERE ' + clause, params).fetchone()[0]
                if used + cap > limit:
                    raise Conflict('Aggregate compute budget exhausted')
            db.execute('INSERT INTO budget_reservations VALUES(?,?,?,?,?,?,?,?,?)',
                       (tenant, project, owner, job, identity, cap, cap, 'reserved', time.time()))

    def settle(self, tenant, job, spent=None):
        with self.store.transaction() as db:
            row = db.execute('SELECT * FROM budget_reservations WHERE tenant=? AND job=?', (tenant, job)).fetchone()
            if row is None:
                raise KeyError('Reservation unavailable')
            if spent is not None and (type(spent) is not int or not 0 <= spent <= row['cap']):
                raise ValueError('Spend exceeds reservation; stop provider work')
            state, charge = ('unknown', row['cap']) if spent is None else ('settled', spent)
            if row['state'] != 'reserved':
                if row['state'] == state and row['charged'] == charge:
                    return
                raise Conflict('Usage was already settled')
            db.execute('UPDATE budget_reservations SET state=?,charged=? WHERE tenant=? AND job=?',
                       (state, charge, tenant, job))
