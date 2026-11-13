# AtMem AI Architect

[![npm](https://img.shields.io/npm/v/%40atmem%2Farchitect)](https://www.npmjs.com/package/@atmem/architect)
[![Release](https://img.shields.io/github/v/release/aetna000/atmem-ai-architect)](https://github.com/aetna000/atmem-ai-architect/releases/latest)

Design architecture, capture requirements, generate project files, run local checks, and download one complete handoff.

**[Watch the demo →](https://x.com/AtMemAi/status/2119386028108910659)**

## Run

Requires Node.js 22 or newer.

```sh
npx @atmem/architect
```

First run installs isolated Python and AtMem runtimes. Open the printed address and choose your model under **AI providers**.

For a persistent command:

```sh
npm install -g @atmem/architect
atmem-architect
```

[Stable release notes](docs/releases/v0.2.1.md) · [Application test configuration](docs/architecture/configuring-application-tests.md) · [Installation and troubleshooting](docs/INSTALLATION.md) · [Package options](packaging/README.npm.md) · [npm package](https://www.npmjs.com/package/@atmem/architect)

## Workflow

**Board → Requirements → Choices → Review → Delivery**

- Start in chat, import a document, or open a project.
- Review generated requirements, cloud choices, and placement.
- Costs update automatically; **Recalculate** refreshes available prices. Missing charges stay visible.
- Generate application files and inspect local check results.
- Explore files and download one ZIP containing code, specifications, costs, and evidence.

## AtMem memory

Searchable tables, cursor pagination, local user profiles, actor provenance, and scoped external RAG or memory providers.

[Context provider configuration](specs/029-general-purpose-engine/evidence/20261113-memory-dashboard/context-providers.md) · [Measured dashboard limits](specs/029-general-purpose-engine/evidence/20261113-memory-dashboard/README.md)

## Develop

Requires Node.js 22.12+ and Python 3.11+.

```sh
npm ci --ignore-scripts
python3 -m venv .venv
.venv/bin/python -m pip install -r server/requirements.txt
npm run setup:memory
npm run local
```

On Windows, use `.venv\Scripts\python.exe` instead of `.venv/bin/python`.

## Verification and limits

Windows, macOS, and Linux pass packaged UI and real AtMem startup checks. Full native Windows generation/export remains unqualified.

Native engineering needs an installed, signed-in agent. Independent Terraform/container checks require local tools and configuration.

Cost estimates remain partial where service prices or usage are missing. No cloud deployment happens automatically.

Open in Orca requires its CLI; actual desktop launch remains unverified.

[Local engineering](docs/LOCAL_ENGINEERING.md) · [Training](docs/TRAINING.md) · [Voice](docs/VOICE.md) · [Cloud emulation](docs/CLOUD_EMULATION.md)

## Licence

AtMem-owned code: [Apache-2.0](LICENSE). Third-party code retains its original licences and notices.
