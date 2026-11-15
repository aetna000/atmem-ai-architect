"""Admin-owned OpenRouter model selection; clients never choose managed models."""
import time
from datetime import datetime, timezone
import uuid
import httpx
from .auth import Forbidden
from .credits import CreditError, Conflict

DEFAULT_MODEL='openai/gpt-6.1-sol'
PRESETS=[{'id':'openai/gpt-6.1-sol','label':'Sol Medium'},
         {'id':'openai/gpt-6.1-terra','label':'Terra Medium'}]
DEFAULTS={'revision':1,'model':DEFAULT_MODEL,'reasoning':'medium','welcomeMicros':20_000_000,
          'maxOutputTokens':4096,'dailyPlatformBudgetMicros':0,'platformSpendingEnabled':False}


class CatalogUnavailable(RuntimeError):pass


class OpenRouterCatalog:
    def __init__(self,fetch=None,*,clock=time.time):
        self.fetch=fetch or self._fetch;self.clock=clock;self.cached=None;self.fetched_at=0

    @staticmethod
    def _fetch():
        with httpx.Client(timeout=20,follow_redirects=False,trust_env=False) as client:
            response=client.get('https://openrouter.ai/api/v1/models');response.raise_for_status()
            return response.json()

    def current(self):
        if self.cached is not None and self.clock()-self.fetched_at<60:return self.cached
        try:
            data=self.fetch()['data'];models=[]
            for item in data:
                architecture=item.get('architecture',{})
                if 'text' not in architecture.get('input_modalities',[]) or 'text' not in architecture.get('output_modalities',[]):continue
                model=item.get('id');name=item.get('name',model)
                if type(model) is not str or not 1<=len(model)<=160:continue
                parameters=item.get('supported_parameters',[])
                models.append({'id':model,'name':name,'mediumSupported':bool(set(parameters)&{'reasoning','reasoning_effort'}),
                               'inputModalities':architecture.get('input_modalities',[]),'pricing':item.get('pricing',{}),'contextLength':item.get('context_length') or 0})
            if not models:raise ValueError('Empty text catalog')
            self.cached={'models':models,'presets':PRESETS,'fetchedAt':datetime.now(timezone.utc).isoformat()}
            self.fetched_at=self.clock();return self.cached
        except (httpx.HTTPError,KeyError,TypeError,ValueError) as error:
            raise CatalogUnavailable('OpenRouter models are temporarily unavailable') from error

    def selected(self,model):
        row=next((row for row in self.current()['models'] if row['id']==model),None)
        if not row:raise CreditError('Choose an available OpenRouter text model')
        if not row['mediumSupported']:raise CreditError('This model does not advertise medium reasoning support')
        return row


class PilotSettings:
    def __init__(self,store,access,catalog):self.store,self.access,self.catalog=store,access,catalog

    def current(self):return self.store.transaction(lambda tx:tx.get('settings','pilot') or DEFAULTS.copy())

    def update(self,actor,revision,changes):
        if type(revision) is not int or revision<1 or type(changes) is not dict or not changes or set(changes)-{'model','welcomeMicros','dailyPlatformBudgetMicros','platformSpendingEnabled'}:
            raise CreditError('Update supported settings with the current revision')
        if 'model' in changes:self.catalog.selected(changes['model'])
        audit=uuid.uuid4().hex
        def apply(tx):
            entry=self.access._entry(tx,actor.x_id)
            previous=tx.get('settings','pilot') or DEFAULTS.copy()
            if not entry['allowed'] or entry['role']!='admin':raise Forbidden('Administrator access required')
            if previous['revision']!=revision:raise Conflict('Settings changed. Reload before saving')
            updated={**previous,**changes,'revision':revision+1}
            for key in ['welcomeMicros','dailyPlatformBudgetMicros']:
                if type(updated[key]) is not int or not 0<=updated[key]<=100_000_000_000:raise CreditError('Use bounded integer USD micro-units')
            if type(updated['platformSpendingEnabled']) is not bool or updated['platformSpendingEnabled'] and not updated['dailyPlatformBudgetMicros']:
                raise CreditError('Set a positive daily budget before enabling managed AI')
            tx.set('settings','pilot',updated)
            tx.create('audit',audit,{'kind':'pilot_settings_updated','actor':actor.x_id,'previous':previous,'updated':updated,
                                    'createdAt':datetime.now(timezone.utc).isoformat()})
            return updated
        return self.store.transaction(apply)
