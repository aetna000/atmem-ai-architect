# AtMem AI Architect

Design an application, review requirements, generate project files, run local checks, and download one complete handoff.

[Watch the demo →](https://x.com/AtMemAi/status/2119386028108910659)

```sh
npx --yes https://github.com/aetna000/atmem-ai-architect/releases/download/v0.2.6/atmem-architect-0.2.6.tgz
```

Version 0.2.6 is installable from the qualified GitHub release archive above. npm has accepted the same archive; public registry processing remains pending.

Requires Node.js 22+. First run installs checksum-verified Python, Terraform, and the pinned AtMem and emulator runtimes in your private application directory.

For a persistent command:

```sh
npm install -g https://github.com/aetna000/atmem-ai-architect/releases/download/v0.2.6/atmem-architect-0.2.6.tgz
atmemai
```

Explore the runnable AI example without connecting a model. Its ZIP includes costs, application source, infrastructure and local check evidence.

Choose your model under **AI providers** when creating your own project. Model usage may incur provider costs.

Run `atmemai --help` for all commands. Common commands include:

| Command | What it does |
| --- | --- |
| `atmemai` or `atmemai start` | Start Architect in the terminal and open the browser. Add `--no-open` to skip the browser. |
| `atmemai status [--json]` | Show installed and running versions, process state, project files, and AtMem memory locations. |
| `atmemai restart` / `atmemai stop` | Ask before replacing or stopping the active instance. Save open work before confirming. |
| `atmemai open` | Open the current local server in the browser. |
| `atmemai providers` | List supported model login methods. |
| `atmemai login codex` | Run native sign-in for Codex, Claude Code, Copilot, or Gemini CLI. |
| `atmemai login openai` | Set an API key for the current server session. Also supports `anthropic`, `gemini-api`, and `xai`. |
| `atmemai setup` / `atmemai doctor` | Install the private runtimes or inspect the installation. |

Data defaults to `~/.atmem-ai-architect`, respecting existing `~/.atforma` installations and `ATMEM_ARCHITECT_HOME`. Use `--data-dir PATH` to manage a separate installation. Use `--port PORT` to choose its web port. Running `atmemai` a second time for the same data directory asks before replacing that instance. A restart keeps the existing port unless you supply another. Upgrades preserve project data.

Native sign-in requires the provider CLI on PATH. API keys entered at the prompt or passed through the matching environment variable are kept in the running server's memory. To make a key available at subsequent starts, supply the variable in the server's environment. The original `atmem-architect` command remains available.

Packaged UI and AtMem startup are checked on Windows, macOS, and Linux. Full native Windows generation/export remains unqualified.

Native generation needs a supported signed-in agent. Independent Terraform/container checks require local tools and configuration.

Available cost estimates include explicit exclusions where prices or usage are missing. Cloud deployment is not automatic. Orca desktop integration is verified on macOS; Windows/Linux Orca execution remains unqualified.

[Configure application tests](https://github.com/aetna000/atmem-ai-architect/blob/main/docs/architecture/configuring-application-tests.md) · [Orca plugin](https://orca.dev/plugins/aetna000/atmem-ai-architect-orca)

AtMem-owned code is Apache-2.0. Bundled third-party licences and notices are retained.

Contact: [hello@atmem.ai](mailto:hello@atmem.ai) · [atmem.ai](https://atmem.ai)

## Version 0.2.6

Create and edit 28 architecture diagram types in the native drawing workspace. Drag, resize and rotate shapes; pan the canvas and zoom with wheel or pinch. Compact labels link to complete properties and numbered connection descriptions. Editable pages and SVG exports share readability checks.

Source documents and client handoffs remain private. Public examples use a synthetic AI knowledge assistant.

## Version 0.2.5

Requirements opens directly in a document editor with page formatting, tables, images, comment threads and tracked edits. Use `atmemai` to launch Architect, `atmemai status` to find its data, and `atmemai login NAME` to connect a model.

## Terraform apply emulation

Architect installs Terraform and its isolated emulator Python environment automatically on first startup. No separate setup script is required. On Board, choose **Emulate apply**. The real Terraform/provider lifecycle targets loopback AWS APIs, reads resources through the SDK, checks convergence and destroys the emulated resources. Reports identify measured behavior and gaps; they do not prove AWS deployment, IAM enforcement or actual compute execution.
