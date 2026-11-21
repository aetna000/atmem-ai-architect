-- Fresh owned installation only. Operator controls membership/source mappings;
-- application roles must never acquire their write permissions.
CREATE SCHEMA enterprise_auth;
REVOKE ALL ON SCHEMA enterprise_auth FROM PUBLIC;
CREATE TABLE enterprise_auth.schema_version(version integer PRIMARY KEY CHECK(version=1),source_sha256 text NOT NULL);
CREATE TABLE enterprise_auth.memberships(
 account_id text NOT NULL,principal_key text NOT NULL CHECK(principal_key ~ '^[0-9a-f]{64}$'),
 issuer text NOT NULL,subject text NOT NULL,active boolean NOT NULL DEFAULT false,
 PRIMARY KEY(account_id,principal_key)
);
CREATE TABLE enterprise_auth.source_mappings(
 account_id text NOT NULL,principal_key text NOT NULL,source_id text NOT NULL,
 source_subject text NOT NULL CHECK(length(source_subject) BETWEEN 1 AND 255),
 version bigint NOT NULL CHECK(version>0),active boolean NOT NULL DEFAULT false,
 PRIMARY KEY(account_id,principal_key,source_id),
 FOREIGN KEY(account_id,principal_key)REFERENCES enterprise_auth.memberships
);
CREATE TABLE enterprise_auth.attempts(
 state_sha256 text PRIMARY KEY CHECK(state_sha256 ~ '^[0-9a-f]{64}$'),
 account_id text NOT NULL,principal_key text NOT NULL,source_id text NOT NULL,
 mapping_version bigint NOT NULL,browser_sha256 text NOT NULL,
 flow_ciphertext text NOT NULL,expires_at timestamptz NOT NULL,consumed_at timestamptz,
 FOREIGN KEY(account_id,principal_key,source_id)REFERENCES enterprise_auth.source_mappings
);
CREATE INDEX enterprise_auth_attempts_expiry ON enterprise_auth.attempts(expires_at);
CREATE TABLE enterprise_auth.connections(
 account_id text NOT NULL,principal_key text NOT NULL,source_id text NOT NULL,
 mapping_version bigint NOT NULL,revision bigint NOT NULL CHECK(revision>0),
 credential_ciphertext text,status text NOT NULL CHECK(status IN('connected','refreshing','needs_reconnect','revoked')),
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(account_id,principal_key,source_id),
 FOREIGN KEY(account_id,principal_key,source_id)REFERENCES enterprise_auth.source_mappings,
 CHECK((status IN('connected','refreshing'))=(credential_ciphertext IS NOT NULL))
);
CREATE TABLE enterprise_auth.events(
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 account_id text NOT NULL,principal_key text NOT NULL,source_id text NOT NULL,
 event text NOT NULL CHECK(event IN('connect_started','connect_completed','refresh_completed','needs_reconnect','disconnected')),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
REVOKE ALL ON ALL TABLES IN SCHEMA enterprise_auth FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA enterprise_auth FROM PUBLIC;
