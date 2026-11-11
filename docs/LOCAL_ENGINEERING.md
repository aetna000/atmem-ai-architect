# Local engineering Build candidate

This candidate adds persistent native engineering work behind the browser's Build tab. You describe the outcome, add updates while it works, inspect the conversation and local checks, then capture/download exact files. The Codex CLI is the first backend worker adapter; the browser uses project-bound backend APIs. Hosted transport and tenant isolation remain unfinished.

## Start in an installed checkout

Use the Node/Python dependencies in [Installation](INSTALLATION.md). The development environment qualified here uses Node26.5, Python3.14 and Codex0.167.1. The native worker's local macOS sandbox is qualified on this machine; other operating systems are unqualified. Sign in through your installed official Codex client outside the project; do not copy its credentials into the app, a brief or an operator JSON file. The application retains your selected model and effort exactly. This qualification uses `gpt-6.1-sol` / `high`; account entitlement is separate.

```sh
python3 scripts/engineering-preview.py --home /absolute/private/app-data --port 5278 --sidecar-port 8870
```

Choose a new app-data directory and free local ports. The home argument is application data; it does not change the process HOME or Codex's account directory. Open the printed numeric-loopback URL. Stop only this launcher's terminal with Ctrl+C. A missing validator/tool registration remains unavailable; the basic command does not silently find Docker, install tools or pull images.

For local checks, the operator explicitly supplies `--tools`, `--validators`, `--isolation-profiles` and `--validator-endpoint` registrations. These are private machine configuration, not receiving-project build inputs. Tools JSON has `readRoots` and `tools`; the latter admits python/node/terraform/providerMirror/dependencyMirror. Every tool must be within an explicitly approved root. Keep roots narrow and do not register credential directories. Validator definitions select cached immutable image IDs, executable arguments, platform, limits, optional reviewed isolation profile, file applicability and optional pinned runtime receipt. Public dependency mirrors are bounded hash-pinned flat catalogs with provenance/licenses; there is no runtime network resolver or installer. See the operator preparation/evaluation scripts and their `--help` before preparing a new environment. No cloud credentials are needed for local checks.

## Manual test card

1. Open Connections, choose Codex and your accessible exact model/effort. In Build, enter a fresh project intent and click Start work once.
2. Add two meaningful updates while it works. Reload the page. Verify the original request, ordered updates, exact selected configuration and continuing run are retained.
3. Switch to Design and back. Inspect progress without resubmitting the request. Design's graph and native files are currently separate review surfaces; changing one does not reconcile the other automatically.
4. On completion inspect the immutable package and each local report. A failed, skipped, absent or stale check remains a limitation. If a bounded automatic repair ran, inspect both original and repaired evidence.
5. If verification definitions have been updated after completion, choose **Recheck and repair** on the current package. Earlier reports remain available; a changed check plan can use at most the original request’s remaining repair allowance. An unchanged plan does not replay work.
6. Download the package; follow its public clean-environment build/test instructions. Receiving instructions must not require the worker's private `.tools` paths. Inspect Terraform and unresolved account inputs; do not apply it.
7. Close/reopen the candidate and select the saved project. Recover existing work if needed; uncertain execution must not be blindly replayed. Preserve its app-data directory and saved project file.

## Limits and rollback

This is a runnable local candidate, not complete architecture or cloud acceptance. Independent positive component/system checks and observed failures are recorded under specs029. The current original-case acceptance count and release/owner status live in its progress and release records; generated tests alone cannot establish acceptance. The original28/four-provider programme, shared graph/file work model and hosted isolation are still required. Reviewed knowledge is a small pinned corpus, not live comprehensive AtMem. Billing is deferred. No deployment is authorized.

Before testing a candidate, retain the prior source checkout, its app-data directory and a saved editable project file. Use a separate candidate checkout/home and separate ports. To roll back, stop only the candidate launcher and reopen the previous checkout with its own unchanged data. Do not delete stores, copy credentials, overwrite other workspaces or re-submit uncertain native runs. Keep artifact/check receipts from both versions. Local tags and archives are source backups; remote publication and deployment are separate actions.
