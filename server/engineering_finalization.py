"""Durable local-check ownership after a verified completed engineering turn.

Capture is synchronous with terminal observation, before another local intent can
start. Execution is background work against those immutable bytes. This supervisor
does not establish semantic acceptance or replay interrupted checks on restart.
"""
import asyncio
import json
import uuid


class EngineeringFinalization:
    def __init__(self,jobs,capture,checks):
        self.jobs,self.capture,self.checks=jobs,capture,checks
        self.store=jobs.sessions.store;self.db=self.store.db
        self.db.execute('''CREATE TABLE IF NOT EXISTS engineering_finalizations (
            id TEXT PRIMARY KEY, session TEXT NOT NULL, run TEXT NOT NULL,
            state TEXT NOT NULL, payload TEXT NOT NULL, UNIQUE(session,run))''')
        with self.db:
            self.db.execute("UPDATE engineering_finalizations SET state='recovery_required' WHERE state='checking'")
        self.tasks={};self.closed=False

    def list(self,scope,session):
        self.store.get(scope,session)
        return [self._public(row) for row in self.db.execute('SELECT * FROM engineering_finalizations WHERE session=? ORDER BY rowid',(session,))]

    @staticmethod
    def _public(row):
        return {'id':row['id'],'sessionId':row['session'],'runId':row['run'],'state':row['state'],
            **json.loads(row['payload']),'acceptance':'not_established_by_local_checks'}

    def _save(self,ident,state,payload):
        with self.db:self.db.execute('UPDATE engineering_finalizations SET state=?,payload=? WHERE id=?',(state,json.dumps(payload,allow_nan=False),ident))

    def observe(self,scope,session):
        """Called without an intervening await after verified terminal settlement."""
        row=self.store.get(scope,session)
        if self.closed or row['state']!='idle' or row['last_status']!='completed':return
        if self.db.execute('SELECT 1 FROM engineering_finalizations WHERE session=? AND run=?',(session,row['run'])).fetchone():return
        ident=str(uuid.uuid4());payload={'artifact':None,'plan':None,'checks':[]}
        with self.db:self.db.execute('INSERT INTO engineering_finalizations VALUES (?,?,?,?,?)',(ident,session,row['run'],'checking',json.dumps(payload)))
        try:
            manifest=self.capture(scope,session)
            checks=self.checks()
            plan=checks.plan(scope,session,manifest['id'])
            payload.update(artifact={'id':manifest['id'],'sha256':manifest['sha256']},plan=plan)
            self._save(ident,'checking',payload)
            self.jobs._record(scope,session,'finalization_started',runId=row['run'],finalizationId=ident,
                artifactId=manifest['id'],artifactSha256=manifest['sha256'],
                text='Saved the completed files. Selecting registered local checks; project acceptance remains unverified.')
            task=asyncio.create_task(self._execute(scope,session,row['run'],ident,payload,checks))
            self.tasks[ident]=task
            def settled(completed):
                self.tasks.pop(ident,None)
                if not completed.cancelled():completed.exception()
            task.add_done_callback(settled)
        except Exception:
            self._save(ident,'needs_attention',payload)
            self.jobs._record(scope,session,'finalization_needs_attention',runId=row['run'],finalizationId=ident,
                text='The completed files could not be captured or checks could not be selected. No result was inferred to pass. Capture/check the retained workspace explicitly.')

    def _current(self,scope,session,run):
        row=self.store.get(scope,session)
        return row['state']=='idle' and row['run']==run and row['last_status']=='completed'

    async def _execute(self,scope,session,run,ident,payload,checks):
        try:
            for decision in payload['plan']['decisions']:
                if decision['state']!='selected':continue
                if not self._current(scope,session,run):
                    self._save(ident,'superseded',payload);return
                check=await checks.start(scope,session,payload['artifact']['id'],decision['validatorId'])
                payload['checks'].append(check['id']);self._save(ident,'checking',payload)
                if check['artifactSha256']!=payload['artifact']['sha256'] or check['contractSha256']!=decision['contractSha256']:
                    raise ValueError('Check contract changed after applicability selection')
            while True:
                receipts=[checks.get(scope,session,check) for check in payload['checks']]
                if any(check['state']=='recovery_required' for check in receipts):
                    state='recovery_required';break
                if all(check['state']=='finished' for check in receipts):
                    current={entry['id']:entry for entry in checks.catalog()}
                    stale=any(check['contractSha256']!=current.get(check['validatorId'],{}).get('contractSha256') or not current.get(check['validatorId'],{}).get('available') for check in receipts)
                    if not self._current(scope,session,run):state='superseded'
                    elif stale or not receipts or any(d['state']=='unavailable' for d in payload['plan']['decisions']):state='needs_attention'
                    elif all(check['result'].get('status')=='passed' for check in receipts):state='local_checks_passed'
                    else:state='needs_attention'
                    break
                await asyncio.sleep(.05)
            self._save(ident,state,payload)
            text={'local_checks_passed':'Selected local checks passed for the saved package. Requirements and full-system acceptance still need independent verification.',
                'needs_attention':'Local verification is incomplete or failed. Inspect the saved package and check reports; no project acceptance is established.',
                'superseded':'Check evidence belongs to an earlier completed turn; newer work needs a new package and checks.',
                'recovery_required':'A local check needs original-worker cleanup. No check or model work was replayed.'}[state]
            self.jobs._record(scope,session,'finalization_'+state,runId=run,finalizationId=ident,artifactId=payload['artifact']['id'],text=text)
        except asyncio.CancelledError:
            self._save(ident,'recovery_required',payload)
            raise
        except Exception:
            self._save(ident,'needs_attention',payload)
            self.jobs._record(scope,session,'finalization_needs_attention',runId=run,finalizationId=ident,
                text='Local verification could not finish. Retained package/check evidence needs review; no work was replayed and no pass was inferred.')

    async def close(self):
        self.closed=True
        for task in list(self.tasks.values()):task.cancel()
        await asyncio.gather(*list(self.tasks.values()),return_exceptions=True)
