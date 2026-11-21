# Public release privacy

Keep client source documents, generated handoffs, screenshots and client audit reports
in restricted storage outside this repository. Public examples use synthetic data.
Do not merge a branch whose ancestry contains restricted client material.

`scripts/release-privacy-check.py` scans tracked source and recursive ZIP/TAR/npm
archives. It checks confidential text patterns, filenames and exact private-file
digests without printing the client policy or matching content. Distribution mode
also rejects local runtime paths. Escaping archive links are rejected; safe aliases
are inspected without extracting or following them.

Maintainers configure the private policy through the repository Actions secret
`ATMEM_RELEASE_PRIVACY_POLICY`. Main/tag packaging and publication require it.
Fork pull requests run the structural checks without exposing this secret; they
cannot substitute for the required policy check on the published artifact.

```sh
python3 scripts/release-privacy-check.py --tracked --policy /private/policy.json --require-policy
python3 scripts/release-privacy-check.py --package --policy /private/policy.json --require-policy candidate.tgz
```

The policy JSON accepts `patterns` (case-insensitive regular expressions) and
`file_sha256` (exact private binary fingerprints). Only private local reports may
retain matching paths. Never upload such reports as public CI artifacts.

This is a release boundary check, not OCR or a proof that arbitrary anonymous data
is safe. Renamed screenshots and unseen confidential paraphrases still require a
human review. A previously published Git object may remain cached or copied even
after its public references are removed; host-side cache removal is separate.
