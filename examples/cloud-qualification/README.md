# Four-cloud examples and qualification evidence

These are synthetic qualification projects, not production deployments. The target is full AI applications, not storage-only coverage. Use the [AI evidence matrix](MATRIX.md) to open projects for IoT, logs/traces, RAG, chatbots, version control, predictive maintenance, support, call-center/CRM, cloud operations and cybersecurity on AWS, Azure, Google Cloud and IBM.

In AtMem AI Architect, choose **More → Open project file**, select a linked `project.atmem-ai-architect.json`, then inspect the board, Requirements, **Emulate & improve**, and Outputs. Loading a project does not import an old pass into the current UI. Run a new emulation for the currently generated artifact.

## What this archive proves

- `manifest.json` preserves each run and SHA-256 hashes of its archived files. Prior failures remain present.
- `real-model-browser-run` means a real signed-in architect account client (Claude or Codex, recorded per run) answered prompts through the actual app UI. `prompt-history.json` records requests/responses; screenshots and downloaded project/Terraform files preserve what was produced. The initial frozen runner had no memory runtime; later Codex repeats include the real AtMem runtime. The dedicated browser suite separately tests AtMem memory operations. These runs are not a model quality benchmark.
- `synthetic-contract-fixture` means a hand-authored typed storage contract tested against real Terraform provider schemas/mock plans and local storage APIs. It is not represented as a model-generated design.
- `exact-model-output-native-validation` means the exact downloaded Terraform from a model/UI run was copied and validated without regeneration. Input file hashes tie it to that run.
- `fixture-model-browser-regression` uses a model transport fixture with the real generator, service endpoint and storage emulator to check correction/retest/Undo/bounds/provider-failure behavior.
- `ai-assessment.json` applies a bounded static graph assessment to archived workspaces and links separate runtime evidence. It cannot establish that every requirement is correctly designed or implemented.
- `cloudPlan` and `deployment` remain **not_run** for this archive. Earlier authorized AWS evidence remains separately preserved under `../aws`.

A later repeat was interrupted by provider failures; a separate minimal CLI diagnostic confirmed Claude’s session limit. Failed repeats are preserved, and the matrix retains earlier loadable projects while recording the latest attempt separately. Follow-up checks use the already signed-in Codex client.

The first broad model run exposed misleading reassurance: empty checks were described as a sound design. The mentor evidence prompt and displayed evidence summary were corrected, followed by real-model repeats. The browser regression suite also exercises a supported permission correction, fresh retesting, Undo invalidation and the automatic-loop bound. A missing native application implementation remains a product gap even when the mentor conversation improves.

## Reproduce

Install the optional backends as described in [Cloud emulation](../../docs/CLOUD_EMULATION.md). Then:

```sh
npm test
npm run test:server
npm run test:emulation
npm run test:emulation:clouds
npm run test:emulation:browser
# Explicit real model usage, no cloud deployment:
npm run test:mentor:live -- aws,azure,gcp,ibm
npm run test:mentor:live -- aws --ai
```

The last command runs all ten AI families for the chosen cloud. Substitute `azure`, `gcp` or `ibm`. Every scenario submits a user prompt, opens the emulation view, runs the local endpoint, receives automatic mentoring, and exports the result. A failing/incomplete application makes the runner exit nonzero; a helpful response cannot turn it green.

Archive a completed run with `python3 scripts/archive-cloud-qualification.py .local/cloud-mentor/<run>`, then regenerate the matrix with `node scripts/assess-ai-qualification.mjs`. Native validation of exact model output uses `node scripts/qualify-model-terraform.mjs .local/cloud-mentor/<storage-run>`.

## Remaining application work

The seven bounded AWS application scenarios have generated runtimes and local emulation coverage. Azure/GCP/IBM currently have native storage foundations, not full AI application generation. Broader scenarios deliberately keep their full component and integration scope visible and block deployment. Next implementation work is tracked in [specification 024](../../specs/024-ai-workload-qualification/spec.md), with acceptance criteria in the scenario registry. No diagram, mock plan or emulator report constitutes production approval.
