-- Fresh owned installation only; cached derivatives are not source authority.
CREATE SCHEMA enterprise_extractions;
REVOKE ALL ON SCHEMA enterprise_extractions FROM PUBLIC;
CREATE TABLE enterprise_extractions.schema_version(
 version integer PRIMARY KEY CHECK(version=1),source_sha256 text NOT NULL
);
CREATE TABLE enterprise_extractions.documents(
 account_id text NOT NULL,parser_revision text NOT NULL CHECK(parser_revision ~ '^[0-9a-f]{64}$'),
 content_key text NOT NULL CHECK(content_key ~ '^[0-9a-f]{64}$'),
 state text NOT NULL CHECK(state IN('building','ready')),
 lease_token uuid,lease_until timestamptz,value_ciphertext text,expires_at timestamptz NOT NULL,
 PRIMARY KEY(account_id,parser_revision,content_key),
 CHECK((state='ready')=(value_ciphertext IS NOT NULL)),
 CHECK((state='building')=(lease_token IS NOT NULL AND lease_until IS NOT NULL))
);
CREATE INDEX enterprise_extractions_expiry ON enterprise_extractions.documents(account_id,expires_at);
REVOKE ALL ON ALL TABLES IN SCHEMA enterprise_extractions FROM PUBLIC;
