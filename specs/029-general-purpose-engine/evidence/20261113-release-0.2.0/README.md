# AtMem AI Architect 0.2.0 release

PR #4 merged into main after all 582 unit tests and Windows/macOS/Linux installed UI/AtMem checks passed. Release 0.2.0 is public and Latest on GitHub, without a prerelease flag. The repository-linked GitHub npm package is public. npm completed automated review; its latest tag resolves to 0.2.0, with provenance and an integrity value identical to the CI artifact.

A fresh registry installation reports 0.2.0. A fresh installation from the public GitHub asset starts the UI and real AtMem; profile, paged memory, creator identity, audit and forget checks pass with no model calls. README links npm and the supplied video.

Failures retained: an unprefixed candidate/file.tgz was interpreted as a GitHub package spec; ./candidate/file.tgz fixes it. New CI unit checks originally lacked .venv/bin/python; CPython 3.13 plus hash-locked requirements fixes it. Tests were retained. npm's automated review delayed public availability; release notes were updated only after registry verification.

Scope: installation/UI/AtMem qualification and the separately recorded dashboard read benchmark. Full native Windows generation/export, actual Orca launch, broad generated-project acceptance and the separately paused engine programme are not promoted by this release. No cloud deployment occurred.
