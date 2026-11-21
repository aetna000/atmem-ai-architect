# Portable receiving Python CLI imports

The Azure diagnostic generated scripts/operator.py beside a receiving installer.
Ordinary script startup placed that directory on the import path, so standard-library
imports reached the project module and failed before installation. The failed native
report is retained in the Azure run history; the evaluator did not patch its export.

Fresh backend-owned handoffs now recommend distinctive generated module names,
explicit isolated entrypoints with fixed owned application imports, and actual CLI
qualification from a clean export. Existing client modules and old workspace pins
remain preserved. This is guidance for future generation; the already-running
frozen native session did not receive a rewritten handoff contract.

`target-probe-v1.json` executes in the actual Python3.13.18/Linux AMD64 checker.
Museum/operator and weather/json sibling collisions fail with ordinary invocation;
isolated invocation and distinctive module names pass in both domains. This is an
actual receiving-startup counterexample/transfer, not a test of a prose string.
`delivery-tests-v1.log` retains the existing delivery regression; the combined
scratch checkpoint's452 server tests also cover the final handoff text.

`source-v1.json` pins Python's primary command-line documentation at CPython3.13.18
revision0d4bd512fc429e3d4eacdd113c975e161f21644d with content SHA256 and review date.
The [Python documentation](https://docs.python.org/3.13/using/cmdline.html#cmdoption-I)
describes script-directory lookup and isolated mode. This guidance/probe does not
prove arbitrary packaging safety or a measured native-quality improvement.
