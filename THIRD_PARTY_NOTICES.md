# Third-party notices

## OpenArchFlow

Source: https://github.com/dmux/OpenArchFlow
Revision: `69450801847dcf23a7bc87b8aedd701f66281168`
Copyright (c) 2026 Rafael Sales. MIT License.

Copied/adapted modules now include AWS/Azure/generic/cloud-native/integration catalogues, templates, Mermaid and SQL parsers, Dagre layout and payload formatting. Exact paths, original hashes, destination hashes and modification status are recorded in `docs/merge-manifest.json`. AtMem AI Architect supplies its own React Flow 12 shell and provider-neutral graph adapters. Type-only imports were adapted, layout dimensions changed, and Mermaid label/wire parsing corrected. No upstream vendor icon assets, screenshots, videos, Next.js shell, analytics, SEO claims or application deployment code are bundled.

The full MIT copyright and permission notice is preserved in `public/licenses/openarchflow-LICENSE.txt`, distributed with the build. Each ported module carries an attribution header. Six earlier catalogue description adaptations remain attributed in `src/upstream-catalog.mjs`.

## AWS GenAI Solutions Architect Agent

Source: https://github.com/aws-samples/sample-genai-aws-solutions-architect-agent
Revision: `da49eb4e6b1528d84ca96f9147b8e1ddce6aec2d`
MIT No Attribution (MIT-0). Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

The source agent, rate limiter, configuration, prompts and supporting file tool are retained under `server/upstream/` with a package-relative import adaptation. AtMem AI Architect uses the composed agent and retry/rate-limiting path for configured Strands API providers; it supplies new neutral instructions and does not call the upstream automatic MCP/Bedrock initialization. The upstream file tool is not registered, and its original AWS-only prompt is never the active prompt. Streamlit and upstream media assets are excluded. Official local account adapters are implemented separately.

The full licence is retained in `public/licenses/aws-architect-LICENSE.txt`.

## AWS Labs MCP servers

Source: https://github.com/awslabs/mcp
Revision: `c6951b9a09d0860550ebabd1a4ba66e36cb7212e`
Apache License 2.0. Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

A disabled planning manifest records package metadata only. No AWS Labs server implementation or executable connector is bundled or launched. The root licence and NOTICE are preserved under `public/licenses/aws-mcp-LICENSE.txt` and `public/licenses/aws-mcp-NOTICE.txt`. Future copied server code requires applicable per-server notices and modification notices.

## Application and sidecar dependencies

Node dependencies retain their licences; full installed root legal texts are generated into `public/licenses/dependency-notices.txt`, with metadata in `docs/dependency-inventory.json`. Sidecar wheel legal texts are collected into `public/licenses/python-dependency-notices.txt`, with metadata in `docs/python-dependency-inventory.json`. A declared licence or scan is not proof that all files and distribution modes are cleared.

The application uses system fonts and Lucide glyphs; no official cloud icon packs are bundled. AtMem tokens and its identity mark are read from the user's private platform source, recorded in `docs/brand-source.json`, without changing the website. Original product code has no public open-source licence grant.

Claude Code, Codex, Gemini and Copilot CLI binaries are user-installed external programs, not redistributed in this repository. Their authentication, usage, model and subscription terms are separate from the licences of copied application code. The GitHub Copilot SDK is an installed dependency, and its declared licence and wheel notices are included in the sidecar inventory. Pulumi is a scaffold/export target; the SDK and CLI are not bundled or executed by the workbench.

Cloud and model product names identify compatibility and architecture concepts, not affiliation, certification or endorsement.

The `github-copilot-sdk` 1.0.28 wheel has no packaged root legal text. Its MIT licence was verified and supplemented from the matching upstream `v1.0.28` tag at `public/licenses/github-copilot-sdk-LICENSE.txt` (Copyright GitHub, Inc.). This supplementation does not clear external Copilot runtime distribution or model subscription rights.

## AtMem runtime and specialist references

The separate AtMem environment is pinned in `server/memory-requirements.txt`. Its installed package/version/licence inventory is `docs/memory-dependency-inventory.json`; wheel-provided legal texts are preserved in `public/licenses/memory-dependency-notices.txt`. Regenerate with `.memory-venv/bin/python scripts/python-notices.py --environment memory`. AtMem is accessed through its core SDK, not a redistributed native control-plane UI.

Pinned reference documents from AWS, Microsoft, Google, HashiCorp and Pulumi are listed with exact commits and SHA256 hashes in `agent-skills/upstream/manifest.json`. Each reference retains its repository licence in the corresponding provider directory. These documents are reference-only; companion scripts, tools and vendor assets are not bundled. The runtime loads AtMem AI Architect's separately reviewed first-party specialist guidance, never arbitrary fetched code.

## PDF export font

`public/fonts/NotoSans-Regular.ttf` is Noto Sans from the Noto Project, distributed under the SIL Open Font License 1.1. The full license is included at `public/fonts/OFL.txt`. Source: https://github.com/notofonts/noto-fonts/tree/main/hinted/ttf/NotoSans . PDF generation uses jsPDF; its license and dependency notices are included in `public/licenses/dependency-notices.txt`.

## Optional cross-cloud local emulation

Azurite 3.37.0 (Microsoft, MIT) and fake-gcs-server 1.56.1 (BSD-2-Clause) run as optional local processes. Azure Storage Blob and Google Cloud Storage Python SDKs are used only against explicitly injected local endpoints in this worker. Pinned setup inputs are under `scripts/cloud-emulators/` and `server/cloud-emulation-requirements.txt`; the GCS release is checksum verified. Installed dependencies and their notices are recorded in `docs/cloud-emulation-dependency-inventory.json` and `public/licenses/cloud-emulation-notices.txt`. IBM coverage reuses the separately noticed Moto S3 protocol model; no IBM emulator is claimed. The standalone GCS binary's transitive Go dependency legal review remains outside this installed-package inventory.

## Chat attachment readers

The local helper uses pypdf (BSD-3-Clause) for PDF text extraction and Pillow (MIT-CMU) for image validation. Their complete installed distribution notices, including bundled dependency notices where supplied, are included in `public/licenses/python-dependency-notices.txt`; versions are recorded in `docs/python-dependency-inventory.json`. DOCX extraction uses Python's standard library.
