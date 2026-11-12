"""Queue INSERT fixtures only; worker execution is qualified separately."""
import procrastinate
FIXTURE_CONTRACT={'id':'synthetic-fixture-v1','endpointSha256':'0'*64,'scope':'synthetic-account','mappingVersion':1}

def fixture_tasks(dsn,namespace):
    app=procrastinate.App(connector=procrastinate.SyncPsycopgConnector(conninfo=dsn,kwargs={'options':'-c search_path=pg_catalog,workflow,pg_temp'}))
    @app.task(name='qualification_extract_'+namespace,queue='qe-'+namespace[:16])
    def extract(operation_id):
        raise RuntimeError('This INSERT-only fixture must not be used as a worker')
    @app.task(name='qualification_dispatch_'+namespace,queue='qd-'+namespace[:16])
    def dispatch(operation_id):
        raise RuntimeError('This INSERT-only fixture must not be used as a worker')
    return app,extract,dispatch
