"""Image-owned ephemeral PostgreSQL fixture for isolated Python checks.

Run only after the trusted artifact bootstrap drops to the nonroot check identity.
The server and check share their own container; no host/remote database, secret,
network, source-selected executable or persistent data directory is accepted.
"""
import os
import secrets
from pathlib import Path
import subprocess
import sys
import tempfile

PG_BIN=Path('/opt/atmem/pg-bin')
PG_LIB='/opt/atmem/postgres-libs'
DSN_ENV='ATMEM_TEST_POSTGRES_DSN'


class FixtureUnavailable(RuntimeError):pass


def run(arguments):
    if os.getuid()==0:raise FixtureUnavailable('SQL checks require the dropped nonroot identity')
    if not arguments or arguments[0]not in {'-m','-c'}:raise ValueError('Use an explicit Python module or probe command')
    # The outer controller owns the hard deadline/container cleanup. Normal exit
    # also stops PostgreSQL before removing only this private temporary directory.
    with tempfile.TemporaryDirectory(prefix='atmem-sql-',dir='/tmp')as folder:
        root=Path(folder);data=root/'data';socket=root/'socket';socket.mkdir(mode=0o700)
        password=secrets.token_hex(24);password_file=root/'password';password_file.write_text(password);password_file.chmod(0o600)
        log=root/'postgres.log';environment={'PATH':str(PG_BIN)+':/usr/bin:/bin','HOME':str(root),'LANG':'C.UTF-8','LD_LIBRARY_PATH':PG_LIB}
        def pg(name,*args,timeout=15):
            with log.open('ab')as stream:return subprocess.run([str(PG_BIN/name),*args],env=environment,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
        ready=False
        try:
            initialized=pg('initdb','-D',str(data),'--username=atmem_test','--auth-local=scram-sha-256','--auth-host=reject','--pwfile='+str(password_file),'--encoding=UTF8','--locale=C.UTF-8','--no-instructions')
            if initialized.returncode:raise FixtureUnavailable('Private PostgreSQL initialization failed; no fallback database was used')
            options="-c listen_addresses='' -c unix_socket_directories="+str(socket)+" -c unix_socket_permissions=0700 -c shared_buffers=16MB -c max_connections=32 -c work_mem=1MB -c maintenance_work_mem=8MB -c wal_buffers=1MB -c max_wal_size=64MB -c min_wal_size=32MB -c jit=off -c log_statement=none -c log_min_error_statement=panic -c log_parameter_max_length_on_error=0"
            started=pg('pg_ctl','-D',str(data),'-l',str(log),'-o',options,'-w','-t','10','start')
            if started.returncode:raise FixtureUnavailable('Private PostgreSQL startup failed; no fallback database was used')
            ready=True
            environment_for_tests={**os.environ,'PGHOST':str(socket),'PGPORT':'5432','PGUSER':'atmem_test','PGDATABASE':'postgres',DSN_ENV:'host='+str(socket)+' dbname=postgres user=atmem_test password='+password+' connect_timeout=3','ATMEM_TEST_POSTGRES_MAJOR':'17','ATMEM_TEST_POSTGRES_DATA':str(data),'ATMEM_TEST_POSTGRES_BIN':str(PG_BIN)}
            # Never let an inherited service/password file redirect even test SQL.
            for name in ['PGSERVICE','PGSERVICEFILE','PGPASSFILE','PGPASSWORD','PGHOSTADDR']:environment_for_tests.pop(name,None)
            environment_for_tests['PGPASSWORD']=password
            result=subprocess.run([sys.executable,*arguments],env=environment_for_tests)
            return result.returncode
        finally:
            if ready:
                stopped=pg('pg_ctl','-D',str(data),'-w','-t','10','-m','immediate','stop')
                if stopped.returncode:raise RuntimeError('Private PostgreSQL shutdown was not confirmed')


if __name__=='__main__':
    try:raise SystemExit(run(sys.argv[1:]))
    except FixtureUnavailable:
        sys.stderr.write('ATMEM_SQL_FIXTURE_UNAVAILABLE\n');raise SystemExit(69)
    except (ValueError,RuntimeError,subprocess.TimeoutExpired):
        # Server logs/source can contain client data; never copy them into errors.
        sys.stderr.write('Isolated PostgreSQL fixture failed; no external database was used.\n');raise SystemExit(2)
