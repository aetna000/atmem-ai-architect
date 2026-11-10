"""Owned native private API/worker composition; no provisioning at startup.

The API never constructs an inference client or document executor. The worker's
executor is supplied by the owned per-file workload launcher, not a request URL.
Provider-specific native per-file launchers remain a separate required dependency.
"""
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
import os
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import psycopg
from enterprise_audit import KnowledgeAudit
from enterprise_auth_store import EnterpriseAuthStore
from enterprise_configuration import deployment, read_deployment, native_database, validate_runtime,session_domain
from enterprise_document_contract import MAX_INPUT, document_result, media_type
from enterprise_extraction_cache import ExtractionCache
from enterprise_http import SourceConnection, create_app
from enterprise_identity import CompanyIdentity
from enterprise_knowledge import EnterpriseKnowledge
from enterprise_oauth import GraphConsent, ConfluenceConsent
from enterprise_queries import producer_queries
from enterprise_query_service import EnterpriseAnswers, EnterpriseQueryWorker
from enterprise_secrets import SecretFiles
from enterprise_sessions import CompanySessions
from enterprise_sources import GraphSharePoint, ConfluenceCloud, SourceUnavailable


@dataclass(frozen=True)
class DocumentExecutor:
    """Application-side byte-bound contract for one owned per-file execution.

    A launcher must verify the complete artifact revision and provide actual native
    per-file isolation. This type alone does not establish isolation or provenance.
    No app credential or source URL is an argument to the parser.
    """
    artifact_revision: str
    run: object = field(repr=False)

    def __post_init__(self):
        if not isinstance(self.artifact_revision, str) or not re.fullmatch(r'[0-9a-f]{64}', self.artifact_revision) or not callable(self.run):
            raise ValueError('Supply the reviewed full parser artifact and owned execution adapter')

    def __call__(self, raw, declared):
        try:
            if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_INPUT: raise ValueError()
            declared = media_type(declared)
            return document_result(self.run(raw, declared), raw, declared)['text']
        except Exception:
            raise SourceUnavailable('document_extraction_unavailable') from None

    def from_source(self, raw, declared, revalidate):
        if not callable(revalidate): raise ValueError('Supply the live source and company/job check')
        # Preserve authority exceptions so cancellation/source changes keep their
        # actual queue semantics. Only transport/parser errors are sanitized.
        revalidate()
        owned = getattr(self.run, 'from_source', None)
        if not callable(owned):
            value = self(raw, declared)
        else:
            try:
                if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_INPUT: raise ValueError()
                declared = media_type(declared)
                value = document_result(owned(raw, declared, revalidate), raw, declared)['text']
            except SourceUnavailable:
                raise
            except Exception:
                raise SourceUnavailable('document_extraction_unavailable') from None
        revalidate()
        return value


def unavailable(*args):
    raise SourceUnavailable('dedicated_question_worker_required')


class NativeRuntime:
    def __init__(self, metadata, environment, role, *, database=None, identity=None,
                 executor=None, model_factory=None, token_http=None, profile_http=None, document_http=None):
        self.deployment = deployment(metadata)
        if role not in {'api', 'worker'}: raise ValueError('Use the owned API or worker role')
        self.role = role
        if role == 'api' and (executor is not None or model_factory is not None):
            raise ValueError('API must not receive inference or parser adapters')
        if role == 'worker' and (not isinstance(executor, DocumentExecutor) or executor.artifact_revision != self.deployment['parserRevision']):
            raise ValueError('Worker requires the owned matching per-file document executor')
        if model_factory is not None and not callable(model_factory): raise ValueError('Supply the owned model factory')
        if role == 'worker':
            bind = getattr(executor.run, 'bind_runtime', None)
            if callable(bind): bind(self.deployment['provider'], environment)
        self.secrets = SecretFiles(self.deployment['provider'], environment, role)
        try:
            env = self.secrets.env
            if role == 'worker':
                from enterprise_models import model_configuration, validate_configured_review, native_generator
                config=model_configuration(self.deployment['provider'], env)
                validate_configured_review(self.deployment['provider'],config)
                model_factory = model_factory or native_generator
            self.database = database if database is not None else native_database(self.deployment['provider'], env, role, self.secrets)
            if not callable(self.database): raise ValueError('Use the owned native database credential factory')
            self.session_domain=session_domain(self.deployment)
            self.auth = EnterpriseAuthStore(lambda: psycopg.connect(self.database(), connect_timeout=5), self.secrets.read('encryption').encode(),company_domain=self.session_domain)
            validate_runtime(self.auth, role,self.deployment['accountId'])
            self.document_recovery = None
            if role == 'worker':
                attach = getattr(executor.run, 'attach_runtime', None)
                if callable(attach): attach(self.auth, self.deployment['accountId'])
                recovery = getattr(executor.run, 'reconcile', None)
                if callable(recovery): self.document_recovery = recovery
            owned = self.deployment['company']
            self.identity = identity or CompanyIdentity(self.deployment['accountId'], owned['issuer'], owned['audience'], owned['jwksUri'], owned['scope'])
            if (not isinstance(self.identity, CompanyIdentity) or
                (self.identity.account_id, self.identity.issuer, self.identity.audience, self.identity.jwks_uri, self.identity.scope) !=
                (self.deployment['accountId'], owned['issuer'], owned['audience'], owned['jwksUri'], owned['scope'])):
                raise ValueError('Company identity adapter differs from the owned deployment')
            graph, confluence = self.deployment['sources']['sharepoint'], self.deployment['sources']['confluence']
            tokens = token_http or {}
            origin = self.deployment['publicOrigin']
            self.connections = {
                'sharepoint': SourceConnection('SharePoint', 'graph', GraphConsent(self.auth, graph['tenantId'], graph['clientId'],
                    origin + '/oauth/callback/sharepoint', graph['driveId'], graph['host'], self.secrets.reader('graph'),
                    http=tokens.get('sharepoint'), profile_http=profile_http)),
                'confluence': SourceConnection('Confluence', 'confluence', ConfluenceConsent(self.auth, confluence['clientId'],
                    origin + '/oauth/callback/confluence', confluence['cloudId'], confluence['host'], confluence['spaces'],
                    self.secrets.reader('confluence'), http=tokens.get('confluence'), profile_http=profile_http))}
            self.sessions = CompanySessions(self.auth,domain=self.session_domain)
            self.store = producer_queries(self.auth, self.database, self.deployment['accountId'],session_domain=self.session_domain)
            self.audit = KnowledgeAudit(self.auth, self.deployment['accountId'])
            def make_engine(principal, access, authorize):
                sources = [GraphSharePoint(graph['driveId'], graph['host'], access['sharepoint'], http=document_http),
                    ConfluenceCloud(confluence['cloudId'], confluence['host'], confluence['spaces'], access['confluence'], http=document_http)]
                generate = model_factory(self.deployment['provider'], env) if role == 'worker' else unavailable
                return EnterpriseKnowledge(sources, generate, executor if role == 'worker' else unavailable,
                    audit=self.audit.bind(principal), authorize=authorize)
            self.make_engine = make_engine
            cache = ExtractionCache(self.auth, self.deployment['accountId'], executor.artifact_revision) if role == 'worker' else None
            self.answers = EnterpriseAnswers(self.store, self.connections, make_engine, extraction_cache=cache, audit=self.audit)
        except BaseException:
            self.close(); raise

    def api(self):
        if self.role != 'api': raise ValueError('The inference worker must not serve the browser API')
        app = create_app(self.identity, self.sessions, self.connections, self.make_engine,
            public_origin=self.deployment['publicOrigin'], web_config=self.deployment['company']['web'],
            answers=self.answers, allow_synchronous=False)
        app.state.native_runtime = self
        @asynccontextmanager
        async def lifespan(app):
            try: yield
            finally: self.close()
        app.router.lifespan_context = lifespan
        return app

    def worker(self):
        if self.role != 'worker': raise ValueError('The browser API must not start a question worker')
        return EnterpriseQueryWorker(self.database, self.answers, document_recovery=self.document_recovery)

    def close(self): self.secrets.close()


def app_factory():
    runtime = NativeRuntime(read_deployment(), os.environ, 'api')
    try: return runtime.api()
    except BaseException:
        runtime.close(); raise


def main():
    # No worker command is advertised until the provider-specific per-file
    # launcher supplies its reviewed executor. Never substitute the unsafe shared
    # parser RPC service or run a document parser inside this credentialed API.
    if sys.argv[1:] != ['api']: raise SystemExit('Use the owned private API command')
    port = int(os.environ.get('PORT', '8080'))
    if not 1 <= port <= 65535: raise ValueError('Invalid owned listener port')
    import uvicorn
    uvicorn.run(app_factory(), host='0.0.0.0', port=port, proxy_headers=False, access_log=False)


if __name__ == '__main__': main()
