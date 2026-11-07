# Implementation plan

1. Preserve and push milestone (done).
2. Validate the corrected connector output; repair stale scope regression test.
3. Run real-account plans/preflight for scenarios 02–07 without deployment.
4. Archive exact prompt rounds, diagrams, projects, generated source files, validation and sanitized account results under examples/aws.
5. Publish the operator runbook, per-scenario acceptance/cleanup criteria, and import/integrity tests.
6. Run live acceptance and cleanup sequentially once AWS grants sufficient Lambda quota. Keep deployment blocked until then.

Constitution: user authorized bounded AWS testing; results stay evidence-based; project files round-trip; secrets stay local; coverage is explicit; no memory writes; examples use existing UI; tests cover archive imports and integrity.
