"""Native API/common-worker assembly with actual isolated mounted Office/PDF jobs.

Four provider configurations, local SQL and Linux only. External company/source
HTTP and model responses remain explicit fixtures; no cloud jobs or deployment.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src/runtime'), str(ROOT / 'tests/runtime'), str(ROOT / '.local/azure-runtime-sdk')]
import psycopg
from enterprise_document_docker_fixture import LocalDocumentJobs
from enterprise_native import DocumentExecutor
from enterprise_operator import activate
from enterprise_sources import SourceDenied
from enterprise_deployment_fixture import metadata
from enterprise_native_postgres import NativeFactories


async def qualify(args):
    out, prior_path = args.out.resolve(), args.parser_receipt.resolve()
    if out.exists() or not out.is_relative_to(ROOT / '.local') or not prior_path.is_relative_to(ROOT / '.local'):
        raise ValueError('Use fresh owned local evidence and a reviewed parser receipt')
    prior = json.loads(prior_path.read_text())
    if not prior['allChecksPassed']: raise ValueError('Supply a passed exact parser qualification')
    for name, digest in prior['sourceHashes'].items():
        if name.startswith('src/runtime/') and 'enterprise_document' in name:
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
                raise ValueError('Parser sources changed since image qualification')
    out.mkdir(parents=True)
    jobs = LocalDocumentJobs(prior['imageId'], args.docker_host, ROOT / '.local/qualification-docker-config', out)
    image = json.loads(jobs.command(['image', 'inspect', prior['imageId']]))[0]
    if image['Config']['User'] != '10001:10001' or image['Os'] != 'linux' or image['Architecture'] != 'amd64':
        raise ValueError('Unexpected parser platform/user')
    revision = hashlib.sha256(json.dumps({key: image[key] for key in ['RootFS', 'Config', 'Os', 'Architecture']}, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    paths = [*list((ROOT / 'src/runtime').glob('enterprise*')), *list((ROOT / 'tests/runtime').glob('enterprise*py')),
             ROOT / 'src/runtime/public_faq.py', ROOT / 'src/runtime/faq-output-contract.json',
             ROOT / 'tests/runtime/durable_postgres_acceptance.py', ROOT / 'tests/runtime/durable_fixture_tasks.py', Path(__file__).resolve()]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}
    checks, provider_results, passed, case = [], [], False, None
    def check(label, value):
        checks.append({'check': label, 'passed': bool(value)})
        if not value: raise AssertionError(label)
    try:
        NativeFactories.setUpClass()
        for provider in ['aws', 'azure', 'gcp', 'ibm']:
            case = NativeFactories(); await case.asyncSetUp()
            owned = metadata(case.f.account, provider); owned['parserRevision'] = revision
            with psycopg.connect(case.owner_dsn) as conn: activate(conn, owned)
            api = case.make(provider, 'api', metadata_override=owned)
            def models(selected, environment):
                def generate(payload, schema, instruction):
                    article = json.loads(payload)['articles'][0]
                    case.f.model_calls.append(True)
                    return json.dumps({'answer': case.f.answer_quote, 'abstained': False,
                        'citations': [{'id': article['id'], 'quote': case.f.answer_quote}]})
                return generate
            worker = case.make(provider, 'worker', metadata_override=owned,
                executor=DocumentExecutor(revision, jobs), model_factory=models)
            await case.browser(api)
            starts = len(jobs.attempts)
            for index, (filename, mime, quote) in enumerate([
                ('policy.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'Staff receive twenty days of paid leave.'),
                ('invoice-scan.pdf', 'application/pdf', 'Invoice total: AUD 42.50')]):
                folder = 'invoices' if filename.endswith('.pdf') else 'enterprise-documents'
                path = ROOT / 'benchmarks/convergence/fixtures' / folder / filename
                hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
                case.f.document_bytes, case.f.document_mime = path.read_bytes(), mime
                case.f.source_version, case.f.answer_quote = 'v' + str(index + 1), quote
                for iteration in range(2):
                    identity = await case.submit()
                    await worker.worker().run(wait=False, concurrency=1, install_signal_handlers=False, listen_notify=False, fetch_job_polling_interval=.01)
                    response = await case.status(identity)
                    value = response.json()
                    (out / f'{provider}-{filename}-{iteration}.json').write_text(json.dumps({'statusCode': response.status_code,
                        'state': value.get('status'), 'errorCode': value.get('errorCode'), 'hasResult': 'result' in value,
                        'parserAttempts': len(jobs.attempts) - starts}, indent=2) + '\n')
                    check(f'{provider}-{filename}-{iteration}-verified-answer', response.status_code == 200 and
                        value.get('status') == 'ready' and value['result']['citations'][0]['quote'] == quote)
                    check(f'{provider}-{filename}-{iteration}-one-native-job-per-distinct-file', len(jobs.attempts) - starts == index + 1)
            check(provider + '-warm-cache-still-reads-current-source-four-times', case.f.document_downloads == 4)
            with psycopg.connect(case.owner_dsn) as conn:
                audit = conn.execute("SELECT count(*)FILTER(WHERE event='knowledge.answer'AND outcome='answered'),count(*)FILTER(WHERE event='knowledge.release'AND outcome='released')FROM enterprise_audit.events WHERE account_id=%s", (case.f.account,)).fetchone()
                encrypted = conn.execute('SELECT value_ciphertext FROM enterprise_extractions.documents WHERE account_id=%s', (case.f.account,)).fetchall()
            check(provider + '-generation-and-release-have-durable-audit', audit == (4, 4))
            check(provider + '-derivatives-remain-encrypted', len(encrypted) == 2 and all('twenty days' not in row[0] and '42.50' not in row[0] for row in encrypted))
            await case.f.client.delete('/api/sources/sharepoint', headers=case.f.headers())
            identity = await case.submit(); await asyncio.to_thread(worker.answers.execute, identity)
            value = (await case.status(identity)).json()
            check(provider + '-withdrawn-source-does-not-use-warm-cache', value.get('status') == 'failed' and
                'result' not in value and len(case.f.model_calls) == 4 and len(jobs.attempts) - starts == 2)
            provider_results.append({'provider': provider, 'actualParses': 2, 'verifiedAnswers': 4,
                'separateApiWorkerRoles': True, 'cloudExecution': False})
            await case.asyncTearDown(); case = None
        # Cancel while a real per-file container starts. Its private input/output
        # volumes and all parser descendants must be removed before return.
        calls = []
        def guard():
            calls.append(True)
            if len(calls) == 4:
                check('cancelled-container-observed-running-before-revocation', jobs.observations[-1]['running'])
                raise SourceDenied('source_access_denied')
        try:
            jobs.from_source(b'Synthetic cancellation probe.', 'text/plain', guard)
        except SourceDenied: pass
        else: raise AssertionError('A revoked parser job continued')
        check('live-revocation-propagates-from-running-parser', len(calls) == 4 and len(jobs.attempts) == 8)
        remaining = jobs.command(['ps', '-aq', '--filter', 'name=atmem-document-workflow-'])
        volumes = jobs.command(['volume', 'ls', '-q', '--filter', 'name=atmem-document-workflow-'])
        check('owned-per-file-containers-and-volumes-removed', not remaining.strip() and not volumes.strip())
        check('exact-source-evidence-stable', all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest for name, digest in hashes.items()))
        passed = True
    finally:
        if case is not None: await case.asyncTearDown()
        (out / 'receipt.json').write_text(json.dumps({'recordedAt': datetime.now(timezone.utc).isoformat(), 'passed': passed,
            'checks': checks, 'providers': provider_results, 'parserImageId': prior['imageId'], 'parserRevision': revision,
            'parserAttempts': jobs.attempts, 'parserObservations': jobs.observations, 'sourceHashes': hashes,
            'scope': 'Actual local API/worker/operator/SQL/queue/native Office/PDF mounted containers; company/source/model transports are fixtures. No provider job execution, cloud plan, whole-case or deployment acceptance.'}, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--parser-receipt', type=Path, required=True)
    parser.add_argument('--docker-host', required=True)
    asyncio.run(qualify(parser.parse_args()))
