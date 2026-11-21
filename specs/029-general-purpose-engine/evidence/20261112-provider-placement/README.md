# Provider placement checkpoint

GE-005 remains in progress. This is engine development, not alpha.4 or an
additional original-project qualification. Three runnable increments are offered;
one original project is locally qualified, owner acceptance is zero, and overall
quality remains unmeasured.

Configured regions previously survived in the resource schedule without binding
the supplied-image Terraform destination. The frozen old compiler produced an
Australian example for a European AWS design while claiming infrastructure
complete. `before-aws.json` binds its original bytes; `before-aws-native/test.log`
records four generated passes followed by the independent placement failure.
The generated implementation was not edited for that comparison.

The reusable mechanism now retains configured canonical regions as validated
inputs, locks known destinations across composition namespaces/provider aliases,
and requires an explicit input when placement is unresolved. Unsupported values
remain blocking scope. A configured region may still be a proposal: generation
does not accept a decision, and review approval defaults false. Identifier syntax
is not a service availability catalogue or a compliance guarantee.

Azure uses a read-only native environment lookup and checks its normalized location
and exact ARM ID against the supplied reference. IBM uses a read-only native
project lookup and checks its region/account. Existing environments/projects are
not created, imported or replaced. Independent artifact inspection checks these
bindings and the closed resource/query footprint of each supplied-image unit;
changing metadata cannot disable these checks. This is not a complete IAM-policy
or whole-composition ownership proof.

Final evidence:

- `js-tests-final.log`: 501 passed, zero failed/skipped.
- `server-tests.log`: 428 passed; server code was unchanged by final metadata edits.
- `build-final.log`: production build passed.
- `generated-v4-manifest.json`: exact generated files and separately authored
  assertion hashes; heavy working packages are on MEM0.
- `native-v4/summary.json`: all twelve packages passed native init without backend,
  validate and 82 mock-provider plan runs. Per provider: standalone container,
  container plus unrelated invoice workflow, and two containers in distinct regions.
  Independent assertions cover retained placement, aliases, rejected changes and
  foreign Azure environment/IBM account/project placement.
- `service-{aws,azure,gcp,ibm}-v4/receipt.json`: actual public server generation,
  independent admission and both modules' native checks passed, with respectively
  15, 19, 16 and 20 mock runs (70 total).
- `references.json`: six pinned primary provider documents/source snapshots with
  review date and SHA256. `source-manifest.json` binds the engine/checker sources.

Native tools used Terraform 1.17.1 with cached AWS 6.72.0, Azure 4.81.0,
Google 7.46.2 and IBM 2.9.0 providers. All test runs use `command = plan` and mock
providers. Parent review gates can defer child data reads until apply; separately
executed unit plans exercise the checks with resolved fixture data. No real cloud
read, account plan, apply, image execution or connected-system acceptance occurred.

Earlier v2/v3 records are retained historical runs, not added to final counts.
The partial v1 helper generation failed before qualification and is excluded.
Evaluation fixtures and assertions are visible and authored during development;
they are not blinded holdouts or new original-case acceptances.

Reproduce with `node scripts/engine-evaluation/compile-placement-probes.mjs` and
a fresh MEM0 output directory, then run
`python3 scripts/engine-evaluation/check-placement-probes.py --packages <directory>
--evidence <fresh-directory>`. Use `.venv/bin/python` for the separate
`check-composition-service.py` runner; its arguments and receipts retain the
project, Terraform and mirror paths. Preserve earlier evidence directories.

Next: reference/import/create lifecycle parity, deeper identity/network policy,
composition state custody, browser/export qualification and a frozen runnable
alpha.4. The remaining seven increments and all 28 original/unfamiliar complete
local systems remain required. The owner preview and running work were untouched.
