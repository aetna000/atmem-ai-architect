# Build application artifacts

Run `python3 build-runtime.py` before Terraform validation or planning, then `python3 -m unittest discover -s app-tests -p "*_test.py"`. Python 3.13 is the deployment runtime. The builder uses fixed ZIP metadata and sorted entries so identical inputs produce identical artifact hashes. SDK workloads install the complete pinned dependency set using wheel hashes, targeting Python 3.13 on Linux ARM64. No source distributions or install hooks are allowed. Record build/artifact-hashes.json with the reviewed plan.

Review dependency updates deliberately and rerun acceptance tests. Keep build/, ZIPs, state, backend configuration and deployment variable files out of source control; commit generated source and reviewed provider lock files. No AWS calls occur during this build.
