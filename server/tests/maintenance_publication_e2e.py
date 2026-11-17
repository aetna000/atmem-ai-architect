"""Explicit fake-GitHub browser fixture. Never import into a deployed server."""
from pathlib import Path
import os
from unittest import TestCase

from server.app import app
from server import maintenance_routes as local, maintenance_campaign_routes as campaigns, maintenance_publication_routes as publications
from server.tests import test_maintenance_publication_protocol as fixtures

fixture = TestCase()
fixtures.PublicationProtocolTests.setUp(fixture)
local.TENANT = 'tenant-one'
campaigns.service = lambda: fixture.service
full = os.getenv('ATMEM_MAINTENANCE_PUBLICATION_E2E_FULL') == '1'
if full:
    from server.maintenance.workers import MaintenanceWorker
    fixture.service.worker = MaintenanceWorker.from_file(Path(os.environ['ATMEM_MAINTENANCE_TEST_CONFIG']))
    fixture.multi = fixtures.MultiGitHub({'owner/project': fixture.result['moduleBefore'],
        **{'owner/' + name: fixture.result['consumers']['root-' + name]['before'] for name in ['consumer-a', 'consumer-b']}})
    fixture.broker = fixtures.GitHubBroker(fixture.db, fixtures.FakeKeychain(), fixture.multi)
    fixture.connection = fixture.broker.register('tenant-one', ['project-one'], 'owner', list(fixture.multi.repositories),
        'github_pat_' + 'x' * 30, int(__import__('time').time()) + 3600)
    fixture.remote = fixture.multi.repositories['owner/project']
publications._service = publications.PublicationService(fixture.service, fixture.broker)
publications._parent = fixture.service


@app.get('/api/test/publication-fixture')
async def fixture_info():
    return {'projectId': 'project-one', 'campaignId': fixture.value.id, 'connectionId': fixture.connection.id,
            'repository': 'owner/project', 'root': 'root-shared', 'full': full, 'evidenceLevel': 'fake_github_ui_fixture_only'}


@app.get('/api/test/publication-receipt')
async def fixture_receipt():
    return {'writes': [path for path, _ in fixture.remote.writes], 'pullRequests': len(fixture.remote.pulls),
            'defaultHead': fixture.remote.refs['main'],
            'consumerPullRequests': {name: len(fixture.multi.repositories['owner/' + name].pulls) for name in ['consumer-a', 'consumer-b']} if full else {},
            'githubNetworkCalls': 0, 'modelCalls': 0,
            'evidenceLevel': 'fake_github_ui_fixture_only'}


@app.on_event('shutdown')
async def cleanup_fixture():
    fixture.doCleanups()


@app.post('/api/test/publication-operator/{action}')
async def operator_fixture(action: str):
    # Fake owner actions and accelerated poll clock only. No GitHub transport.
    if not full or action not in {'release', 'merge-a', 'merge-b'}:
        raise ValueError('Explicit full browser fixture required')
    repository = fixture.remote if action == 'release' else fixture.multi.repositories['owner/consumer-' + action[-1]]
    pull = repository.pulls[0]
    repository.refs['main'] = pull['head']['sha']
    pull.update(merged=True, state='closed')
    if action == 'release':repository.tags['v2.0.0'] = pull['head']['sha']
    with publications._service.core.ledger.store.transaction() as db:
        db.execute('UPDATE publication_poll_cursors SET next=0')
    return {'evidenceLevel': 'fake_owner_action_and_accelerated_poll_clock', 'action': action}
