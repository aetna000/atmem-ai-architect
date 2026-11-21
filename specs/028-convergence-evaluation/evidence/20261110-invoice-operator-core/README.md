# Operator initialization checkpoint

The generator now exports a shared operator initialization core. Complete native
bindings, account UUID and namespace are validated before opening a connection.
The CLI preserves its preview and explicit execution boundary. Azure principal
mapping remains a separate postgres phase. A database-local advisory transaction
lock serializes the initial schema check/create across deployments. Autocommit is
rejected before role creation; retries preserve exact role ownership and passwords.

Actual concurrent empty-database initialization and retries pass against owned
loopback PostgreSQL 17 and 18. Tests authenticate both created IBM-profile SQL
logins and reject audit deletion, malformed deployment inputs and autocommit.
These are local native-profile SQL tests, not IBM cloud authentication.

71 API/operator checks, 7 dedicated PG18 operator checks, 305 JavaScript tests,
208 server tests and the build pass. The build retains its known chunk-size warning.
See qualification.json and the immutable raw receipt/logs and source snapshot.

This is a checkpoint, not full workflow acceptance. Native operator job delivery,
scheduled retention, monitoring and whole state/Spec Kit/registry integration are
next. Existing image receipts refer to older exact source/images and are not reused
as proof of these new bytes. Complete medium conversations and the final 28-case
matrix and held-out variants remain pending. No cloud operation was performed.
