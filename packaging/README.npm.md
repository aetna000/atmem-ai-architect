# AtMem AI Architect

Design an application, review requirements, generate project files, run local checks, and download one complete handoff.

[Watch the demo →](https://x.com/AtMemAi/status/2119386028108910659)

```sh
npx @atmem/architect
```

Requires Node.js 22+. First run installs checksum-verified Python and the pinned AtMem runtime in your private application directory.

For a persistent command:

```sh
npm install -g @atmem/architect
atmem-architect
```

Choose your model under **AI providers**. Model usage may incur provider costs.

Options: `--port 5174`, `--no-open`, `--data-dir PATH`, `--setup`, `--doctor`, `--version`.

Data defaults to `~/.atmem-ai-architect`, respecting existing `~/.atforma` installations and `ATMEM_ARCHITECT_HOME`. Upgrades preserve project data.

Packaged UI and AtMem startup are checked on Windows, macOS, and Linux. Full native Windows generation/export remains unqualified.

Native generation needs a supported signed-in agent. Independent Terraform/container checks require local tools and configuration.

Available cost estimates include explicit exclusions where prices or usage are missing. Cloud deployment is not automatic. Orca desktop integration is verified on macOS; Windows/Linux Orca execution remains unqualified.

[Configure application tests](https://github.com/aetna000/atmem-ai-architect/blob/main/docs/architecture/configuring-application-tests.md) · [Orca plugin](https://orca.dev/plugins/aetna000/atmem-ai-architect-orca)

AtMem-owned code is Apache-2.0. Bundled third-party licences and notices are retained.
