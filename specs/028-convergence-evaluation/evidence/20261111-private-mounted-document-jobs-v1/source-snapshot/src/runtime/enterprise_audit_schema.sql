-- Fresh owned installation. Runtime can append, but cannot read/rewrite history.
CREATE SCHEMA enterprise_audit;
REVOKE ALL ON SCHEMA enterprise_audit FROM PUBLIC;
CREATE TABLE enterprise_audit.schema_version(
 version integer PRIMARY KEY CHECK(version=1),source_sha256 text NOT NULL
);
CREATE TABLE enterprise_audit.events(
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 account_id text NOT NULL,principal_key text NOT NULL CHECK(principal_key ~ '^[0-9a-f]{64}$'),
 trace_id uuid NOT NULL,query_id uuid,attempt integer CHECK(attempt BETWEEN 1 AND 3),
 event text NOT NULL CHECK(event IN('knowledge.answer','knowledge.release')),
 outcome text NOT NULL CHECK(outcome IN('answered','abstained','withheld','released')),
 source_count integer NOT NULL CHECK(source_count BETWEEN 1 AND 20),
 document_count integer CHECK(document_count BETWEEN 0 AND 80),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK((query_id IS NULL)=(attempt IS NULL)),
 CHECK((event='knowledge.answer' AND outcome IN('answered','abstained','withheld'))
    OR(event='knowledge.release' AND outcome IN('released','withheld'))),
 CHECK((outcome='withheld') OR document_count IS NOT NULL),
 CHECK(document_count IS NULL OR document_count<=source_count*4)
);
CREATE INDEX enterprise_audit_owner_time ON enterprise_audit.events(account_id,created_at);
CREATE INDEX enterprise_audit_query ON enterprise_audit.events(account_id,query_id,attempt);
REVOKE ALL ON ALL TABLES IN SCHEMA enterprise_audit FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA enterprise_audit FROM PUBLIC;
