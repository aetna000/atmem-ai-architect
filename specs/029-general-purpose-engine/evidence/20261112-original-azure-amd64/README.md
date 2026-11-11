# Original Azure ticket tool: declared image component

The original exposed Azure ticket-triage artifact remains unchanged at
`bea50c6b0677d3d20b74a6916780edf79a0fe7c4e8208901a42f561d985afdad`.
Its frozen22 criteria and original source0b8fe07 are retained in
`../20261111-native-azure-primary/`. No new model inference or source repair was
submitted for this component check.

The exact declared Node26.13.0/bookworm-slim Linux AMD64 platform descriptor was
observed from the official public repository, cached anonymously and supplied as
a separate receiving build input. All packaged-runtime files match the original
source bytes. The unchanged Dockerfile has one parameterized FROM, COPY/USER/CMD
and no RUN/ADD/custom frontend. Build uses network-none/pull-false and an empty
Docker auth configuration on the separate MEM0-backed VM.

`image-component-v1.json` binds actual image, base descriptor, original artifact,
source hashes and independent probe. Actual Node26.13.0/Linux x86_64/UID1000 imports
the image's five application modules and passes six direct contract groups: required
20000/documented20480 UTF8 bytes, non-BMP byte boundaries, invalid types/surrogates/
caller controls,480/240-code-point output boundaries, enum/extra-field denial and
raw/escaped/nested duplicate-key rejection. `probe-image.mjs` is the exact oracle.
No source/dependency version or target architecture was substituted.

Heavy context, registry descriptors, build/probe output remain on MEM0 at
`.local/external-artifacts/original-azure-amd64/v1`. The public base is a disclosed
qualification input, not security/publisher-signature approval. No credentials or
account call were used. This closes the declared-image/module/contract component;
actual connected HTTP/browser/Entra/model-policy/infra and all22 whole-project
criteria remain independently unqualified. Original acceptance stays1/28.
