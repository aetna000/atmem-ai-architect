# Install and start AtMem AI Architect

AtMem AI Architect runs locally in your browser. The npm preview includes the UI,
local service and isolated AtMem memory runtime.

## npm preview

Install Node.js 22 or later, then run:

```sh
npx @atmem/architect@preview
```

First run downloads checksum-verified uv, managed Python 3.13 and hash-locked
application dependencies into your application data directory. No Git checkout,
system Python or Docker is required to open the app. Keep the terminal open;
Ctrl+C stops it. Open the printed address, normally http://127.0.0.1:5174.

Use `--port 5175` if the port is occupied, `--data-dir PATH` for an external disk,
`--no-open` to open the browser yourself, or `--doctor` for installation status.
Upgrades retain existing project data, including legacy `~/.atforma` installations.
Choose a model in Connections. Native coding agents and optional independent
Terraform/container checks require their own local tools. No cloud deployment occurs.

The following instructions are for developing from source.

## 1. Check prerequisites

Install Git, Node.js 22.12 or later, and Python 3.11 or later. Current local
verification uses Node 26 and Python 3.14. A provider account or API key is
optional: Local patterns works without either.

```sh
node --version
python3 --version
git --version
```

## 2. Get the source

```sh
git clone https://github.com/aetna000/atmem-ai-architect.git
cd atmem-ai-architect
npm ci --ignore-scripts
```

Review the repository's [README](../README.md), notices and current limits.
Keep application credentials out of this checkout and out of project files.

## 3. Install the local services

On macOS or Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r server/requirements.txt
npm run setup:memory
```

The architect service uses `.venv`. AtMem uses the separate `.memory-venv`
because its cryptographic dependencies differ from the model SDK environment.
Setup downloads dependencies; it does not sign in to a provider or provision
cloud resources. AtMem AI Architect currently pins its own tested AtMem runtime; do not
replace its memory requirements merely because a newer AtMem package exists.

On Windows PowerShell, the corresponding source setup is:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r server/requirements.txt
python scripts/setup-memory.py
```

The launcher selects the Windows virtualenv executable. Native Windows
execution has not been browser-qualified; these commands are not a claim
of completed Windows acceptance. Report problems with OS and tool versions.

## 4. Start the application

```sh
npm run local
```

Keep this terminal open and visit **http://127.0.0.1:5174**. The local agent
service listens on **http://127.0.0.1:8766**. Use the numeric loopback address.
Stop the launcher with **Ctrl+C** when finished. This does not delete saved
project files or AtMem AI Architect's memory store.

For a frontend-only local preview, `npm run dev` runs the zero-key interface.
It does not start the Python service needed for connected model requests.
A static website host cannot supply that local service.

## 5. Choose your architect

Open **Connections**. Start with **Local patterns** for a zero-key exploration.
For a model-connected interview, choose an official account client or a
supported model API connection. Install and sign in to only the desired native
client, then select an accessible model or its `default` setting.

The existing README documents the Claude, Codex, Copilot and Gemini client
sign-in commands. AtMem AI Architect does not copy their account tokens. Account login,
subscription entitlement and individual model availability are separate checks.
API-key billing is separate from subscription usage. Enter keys through the
local Connections dialog or the documented service environment, never in a
project, diagram, chat example or source file.

## 6. Run your first project

Continue with [the hands-on training guide](TRAINING.md). Describe an idea,
review the diagram and requirements, compare clouds, estimate from explicit
assumptions, then inspect and download a delivery pack. The application does
not apply cloud changes.

## Troubleshooting

- **Missing local sidecar:** check that `.venv` exists and the requirements
  installation succeeded. Run the commands from the repository directory.
- **Browser cannot connect:** leave `npm run local` running and inspect its
  terminal for a port conflict or service error. Do not expose the service
  publicly to fix a local connection problem.
- **Provider/model unavailable:** check that the chosen official client is
  installed and signed in, and that the model is available to that account.
  Local patterns remains an alternative; it is not a live model session.
- **Memory unavailable:** rerun the documented memory setup and inspect the
  error. The architect can still use the current project; do not delete
  encryption keys or overwrite another AtMem store as a repair.
- **Terraform checks unavailable:** Terraform is optional. A generated draft,
  provider schema check, real cloud plan and deployment are different stages.

AtMem AI Architect stores new app-owned memory under `~/.atmem-ai-architect/memory` (existing installations retain their previous directory) (or the configured
`ATMEM_ARCHITECT_HOME`), separate from `~/.atmem`. Save an editable project file before
upgrading or starting over. Preserve your files, memory store and keys.
For backend hosting boundaries, read [self-hosting](SELF_HOSTING.md).
