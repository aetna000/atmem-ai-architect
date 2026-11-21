# Bounded catalog operations

The catalog accepts at most 100 small UTF-8 documents. Every write supplies explicit subject and region ACLs; empty ACLs deny everyone. Use manage-catalog.py with a separate reviewed operator identity, the output table name, exact account/region and --confirm-write. End-user roles cannot write the catalog. New documents use a transactional capacity counter; updates and deletes require --expected-revision and fail on concurrent changes. Keep document files outside source control.

Install the hash-locked preflight dependencies first. Supply a JSON document containing exactly id, title, text, allowedSubjects and allowedRegions. Record the returned revision for subsequent updates/deletes. Do not put document contents in Terraform variables or state. Recovery, connector changes and source deletions must use the same conditional write contract.

Callers assume their generated scoped API role and sign POST /live/ask with SigV4. Identity is the stable IAM principal ID; employee region is an authoritative directory field. The body contains only question. Existing broad IAM permissions must be reviewed separately; end users must not have direct Lambda invoke or catalog write access.
