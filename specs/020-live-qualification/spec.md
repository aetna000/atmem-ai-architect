# Bounded live AWS qualification

Authorization: user approved Sydney AWS tests within a total $20 budget, after local confidence is established. User approved a regional Lambda quota request of 1,001; it is an account concurrency ceiling, not a spending commitment. Generated functions retain individual concurrency caps.

Start with the already-qualified storage scenario. Render the actual prompt-derived project with explicit qualification lifecycle, preserving security/access controls. Production and staging destruction protection remain unchanged. Use only fresh isolated resources, a fresh scoped test identity, reviewed create-only plans, bounded synthetic data and a durable journal. Validate exact bytes/versions, anonymous denial and authenticated deletion denial. Remove only resources created by this test; retain cleanup evidence and fail if leftovers remain.

AWS currently reports a Lambda quota of 10. The quota request is CASE_OPENED; compute deployment remains blocked until the actual regional setting supports reservations. Never remove function limits to bypass that prerequisite.
