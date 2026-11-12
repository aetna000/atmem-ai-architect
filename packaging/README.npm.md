# AtMem AI Architect — local preview

Design an application, review requirements and choices, generate and verify locally,
and download a project handoff. AtMem memory is included in an isolated runtime.

```sh
npx @atmem/architect@preview
```

For a persistent command:

```sh
npm install -g @atmem/architect@preview
atmem-architect
```

Requires Node.js 22 or newer and internet access for first setup. First run downloads a
checksum-verified uv release, managed Python 3.13 and the application/AtMem dependencies.
No system Python, Git checkout, administrator privileges or Docker is required to open
the app. Choose a model/login in Connections. Model usage may incur your provider's costs.

Options: `--port 5174`, `--no-open`, `--data-dir PATH`, `--setup`, `--doctor`, `--version`.
Runtime tools and project data live in `~/.atmem-ai-architect`, respecting existing
`~/.atforma` installations and `ATMEM_ARCHITECT_HOME`. Package upgrades do not delete them.
Use `--data-dir` for an external disk. Stop the local service with Ctrl+C.

This is an alpha preview. Cloud deployment is not included. Native coding needs an
installed/signed-in supported agent; independent container/Terraform checks need explicit
local tools/validator configuration. Missing checks remain visible. Provider pricing does
not yet cover every service. Windows/Linux installers must pass the release matrix;
local Mac checks alone do not establish support on the other systems.

Bundled third-party licences are in `public/licenses` and `agent-skills/upstream`.
Application licensing has not been changed by this packaging work (`UNLICENSED`).
