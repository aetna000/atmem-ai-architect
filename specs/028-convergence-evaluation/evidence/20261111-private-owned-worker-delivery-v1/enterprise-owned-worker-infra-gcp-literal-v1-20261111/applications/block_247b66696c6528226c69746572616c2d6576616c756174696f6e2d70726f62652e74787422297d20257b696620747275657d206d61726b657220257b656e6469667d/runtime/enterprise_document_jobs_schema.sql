-- Fresh installation only; metadata-only cleanup intent, never document content.
CREATE SCHEMA enterprise_document_jobs;
REVOKE ALL ON SCHEMA enterprise_document_jobs FROM PUBLIC;
CREATE TABLE enterprise_document_jobs.schema_version(
 version integer PRIMARY KEY CHECK(version=1),source_sha256 text NOT NULL
);
CREATE TABLE enterprise_document_jobs.jobs(
 account_id text NOT NULL REFERENCES enterprise_auth.company_bindings(account_id),
 target_sha256 text NOT NULL CHECK(target_sha256 ~ '^[0-9a-f]{64}$'),
 request_id text NOT NULL CHECK(request_id ~ '^[0-9a-f]{64}$'),
 owner_token uuid NOT NULL,
 phase text NOT NULL CHECK(phase IN('input_pending','job_pending','job_running','succeeded')),
 state text NOT NULL CHECK(state IN('active','cleaning','pending','settling')),
 expires_at timestamptz NOT NULL,next_attempt_at timestamptz NOT NULL,
 cleanup_token uuid,cleanup_until timestamptz,
 failures integer NOT NULL DEFAULT 0 CHECK(failures BETWEEN 0 AND 1000000),
 settle_until timestamptz,settle_round integer NOT NULL DEFAULT 0 CHECK(settle_round BETWEEN 0 AND 4),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(account_id,target_sha256,request_id),
 CHECK((state='cleaning')=(cleanup_token IS NOT NULL AND cleanup_until IS NOT NULL))
);
CREATE INDEX enterprise_document_jobs_due ON enterprise_document_jobs.jobs(account_id,target_sha256,state,next_attempt_at,expires_at);
REVOKE ALL ON ALL TABLES IN SCHEMA enterprise_document_jobs FROM PUBLIC;
