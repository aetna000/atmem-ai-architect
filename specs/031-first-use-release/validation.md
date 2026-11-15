# Local validation

- Native onboarding browser flow passed: example, eight reference checks, verified ZIP download, compact composer, introduction, voice settings, reset cancel/confirm and model setup. No model calls.
- Multi-turn conversation remains visible at 400/560/870/1440 px; composer stays reachable.
- Portable ZIP includes 85 files, generated code/Terraform and built runtime. Its digest and all retained qualification hashes pass.
- Reference evidence records 13 application/source-contract tests and two Terraform mock plans. No AWS deployment.
- Clean-installed npm candidate starts with AtMem 2.3.14, opens the example and verifies its ZIP download. No browser errors/model calls.
- Server suite: 523 tests, OK, 12 platform/environment skips, using pinned managed AtMem and isolated IBM runtime. Initial worktree runs lacked those runtime registrations; no product tests were weakened.
- JavaScript suite: 588 tests passed, including the portable-reference regression.

Publishing uses `.github/workflows/npm-release.yml` trusted npm authentication. Local npm login is not the release path. Registry publication and three-platform qualification are reported separately after workflow completion.
