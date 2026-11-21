-- Apply only through the reviewed migration role, in its own database/schema.
-- Queue schema is supplied by the pinned Procrastinate dependency, not copied here.
CREATE TABLE workflow.schema_version (
    version integer PRIMARY KEY CHECK (version = 1),
    source_sha256 text NOT NULL,
    queue_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE workflow.accounts (
    id uuid PRIMARY KEY
);
CREATE TABLE workflow.memberships (
    account_id uuid NOT NULL REFERENCES workflow.accounts(id),
    subject text NOT NULL CHECK (octet_length(subject) BETWEEN 1 AND 500),
    roles text[] NOT NULL CHECK (cardinality(roles) > 0 AND roles <@ ARRAY['user','reviewer','supervisor','owner']::text[]),
    active boolean NOT NULL DEFAULT true,
    authorization_lock bigint NOT NULL DEFAULT 0,
    PRIMARY KEY (account_id, subject)
);
CREATE TABLE workflow.operations (
    id uuid PRIMARY KEY,
    account_id uuid NOT NULL REFERENCES workflow.accounts(id),
    workflow_key text NOT NULL CHECK (octet_length(workflow_key) BETWEEN 1 AND 128),
    kind text NOT NULL CHECK (kind IN ('document','draft','account_change')),
    dedup_key text NOT NULL CHECK (octet_length(dedup_key) BETWEEN 1 AND 200),
    created_by text NOT NULL,
    source_ref jsonb NOT NULL CHECK (jsonb_typeof(source_ref) = 'object'),
    destination_contract jsonb NOT NULL CHECK (jsonb_typeof(destination_contract) = 'object'),
    state text NOT NULL CHECK (state IN ('pending','processing','review','approved','dispatching','unknown','sent','dead')),
    result jsonb,
    result_revision integer NOT NULL DEFAULT 0,
    approved_hash text,
    approved_by text,
    lease_token uuid,
    lease_until timestamptz,
    execution_epoch bigint NOT NULL DEFAULT 0,
    attempts integer NOT NULL DEFAULT 0,
    queue_job_id bigint,
    receipt jsonb,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (account_id, workflow_key, kind, dedup_key),
    UNIQUE (id, account_id),
    FOREIGN KEY (account_id, created_by) REFERENCES workflow.memberships(account_id, subject),
    FOREIGN KEY (account_id, approved_by) REFERENCES workflow.memberships(account_id, subject),
    CHECK ((lease_token IS NULL) = (lease_until IS NULL))
);
CREATE INDEX workflow_operations_recovery ON workflow.operations(state, lease_until);
CREATE TABLE workflow.results_history (
    operation_id uuid NOT NULL,
    account_id uuid NOT NULL,
    revision integer NOT NULL CHECK (revision > 0),
    result jsonb NOT NULL CHECK (jsonb_typeof(result) = 'object' AND octet_length(result::text) <= 70000),
    actor text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (operation_id,revision),
    FOREIGN KEY (operation_id,account_id) REFERENCES workflow.operations(id,account_id)
);
CREATE TABLE workflow.events (
    sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    operation_id uuid NOT NULL,
    account_id uuid NOT NULL,
    event text NOT NULL,
    actor text NOT NULL,
    detail jsonb NOT NULL CHECK (jsonb_typeof(detail) = 'object' AND octet_length(detail::text) <= 2000),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (operation_id, account_id) REFERENCES workflow.operations(id, account_id)
);
CREATE INDEX workflow_events_operation ON workflow.events(account_id, operation_id, sequence);
