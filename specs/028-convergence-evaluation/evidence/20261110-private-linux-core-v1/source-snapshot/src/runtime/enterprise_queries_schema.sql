-- Fresh installation only. Queue and domain state share one transaction.
CREATE TABLE enterprise_queries.schema_version(
 version integer PRIMARY KEY CHECK(version=1),source_sha256 text NOT NULL,queue_version text NOT NULL
);
CREATE TABLE enterprise_queries.requests(
 id uuid PRIMARY KEY,account_id text NOT NULL,principal_key text NOT NULL,
 session_sha256 text NOT NULL,request_key uuid NOT NULL,
 question_mac text NOT NULL,question_ciphertext text,
 state text NOT NULL CHECK(state IN('queued','running','ready','failed','cancelled','expired')),
 attempt integer NOT NULL DEFAULT 0 CHECK(attempt BETWEEN 0 AND 3),
 lease_token uuid,lease_until timestamptz,result_ciphertext text,
 error_code text CHECK(error_code IN('source','setup','signin','unavailable','answer')),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),expires_at timestamptz NOT NULL,
 UNIQUE(account_id,principal_key,session_sha256,request_key),
 FOREIGN KEY(account_id,principal_key)REFERENCES enterprise_auth.memberships,
 CHECK((state='running')=(lease_token IS NOT NULL AND lease_until IS NOT NULL)),
 CHECK((state='ready')=(result_ciphertext IS NOT NULL))
);
CREATE INDEX enterprise_queries_requests_recovery ON enterprise_queries.requests(state,lease_until,expires_at);
CREATE INDEX enterprise_queries_jobs_domain ON enterprise_queries.procrastinate_jobs((args->>'query_id'),task_name,status);
CREATE TABLE enterprise_queries.events(
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 query_id uuid NOT NULL,account_id text NOT NULL,principal_key text NOT NULL,
 event text NOT NULL CHECK(event IN('submitted','claimed','ready','released','retry_pending','failed','cancelled','expired')),
 attempt integer NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
