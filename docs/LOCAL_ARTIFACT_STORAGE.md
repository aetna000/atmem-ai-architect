# Local artifact storage on MEM0

The owner requested heavy uncommitted files on MEM0. This machine's operator
profile is `.local/artifact-storage.json`; it and migration journals stay ignored
by Git. Bulk data lives under `/Volumes/MEM0/AtMem-AI-Architect`.

Release source archives and inactive research binaries/JARs retain their original
local paths through symlinks to checksum-verified external objects. The provider
mirror uses an APFS sparsebundle on MEM0, mounted at the original
`.local/provider-cache` path. MEM0 is ExFAT; the image retains Mac executable
permissions and filesystem behavior without changing worker read roots. Its
16 GiB capacity is virtual; physical storage grows with provider-cache content.

Project stores, session logs, source and Git remain local. The copy was verified
before removing local bulk copies; migration records remain both locally and on
MEM0. All four provider-family schema checks passed using the mounted mirror.
The migration is storage maintenance, not deployment or runtime acceptance.

Keep MEM0 mounted while using these artifacts. After reboot/reconnection, run
from the primary installed checkout:

```sh
python3 scripts/local-artifact-storage.py mount
python3 scripts/local-artifact-storage.py status
```

The helper verifies the configured external-volume UUID and image, preserves the
registered cache path, and refuses to mount over existing local files. It does not
format disks, unmount volumes, install providers or access cloud accounts.

New large archives and research downloads should go directly to the external
artifact directory, with stable local links when a tool requires the existing
path. Keep provider downloads in the mounted mirror. Do not move active databases
or project stores as ordinary files; this migration did not do so. Preserve exact
artifact hashes and existing qualification evidence.
