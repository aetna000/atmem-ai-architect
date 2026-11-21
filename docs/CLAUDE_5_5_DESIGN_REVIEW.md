# Claude Opus 5.5 design consultation

Requested model: `claude-opus-5-5`. Run through the installed, authenticated Claude Code CLI with tools disabled, safe mode, no session persistence, and no fallback model. Input was a product brief, not credentials or private source.

# AtMem AI Architect: Local Integration and Design Brief

**Scope:** Localhost only. No publication to atmem.ai, no hosted services, no automatic deployment. The future target is atmem.ai/AtMem AI Architect, so the contracts below are designed to survive that move without implementing it now.

---

## 1. Reuse Boundaries

**Principle:** Port pure logic and data into framework-free TypeScript packages. Rewrite UI against the existing React 19 / ReactFlow 12 shell. Use the Python sample as the backend reference, not as a UI.

| Source | Port (copy and adapt) | Rewrite | Retain as backend | Discard |
|---|---|---|---|---|
| OpenArchFlow (MIT @6945080) | AWS, Azure, generic and integration catalogue *data*; SimulationEngine and metrics; structured schema tools; import/export parsers; Terraform generators | Node and edge components (RF11→RF12); Zustand slices, mapped into the existing store | Bedrock and Gemini calls, re-expressed as provider adapters in the sidecar | Next.js app shell, API routes, any vendor icon assets |
| aws-samples agent (MIT-0 @da49eb4) | Phase workflow (discovery → architecture → cost → review) as a state machine; MCPClientManager pattern; RateLimiter | System prompt and tool descriptions (they forbid competing providers, so replace them) | Strands/BedrockModel as *one* model adapter | Streamlit UI |
| AWS Labs MCP (Apache-2.0) | — | — | Run as external child processes, optional and off by default | Vendoring |

**Repository shape:**
- `packages/model`: canonical Zod schema, graph and revision types, migrations from the MVP JSON and an OpenArchFlow import adapter. JSON Schema is emitted from this and pydantic models are generated from it.
- `packages/catalog`: provider-neutral block schema (category, ports, config schema, provider mappings) plus a coverage matrix.
- `packages/sim`: the ported SimulationEngine, decoupled from the store. It runs in a Web Worker, is deterministic with a seed, and is cancellable.
- `packages/iac`: the ported Terraform generators. Output is plan artifacts only.
- `apps/web`: the existing Vite app.
- `services/architect`: FastAPI bound to 127.0.0.1, with SQLite, agent sessions, run orchestration and MCP clients.

**Licensing:**
- Add `THIRD_PARTY_NOTICES.md` containing the full MIT text and copyright for OpenArchFlow.
- Add an MIT-0 provenance note. It is not required, but it keeps the audit trail clean.
- Add Apache-2.0 NOTICE text if MCP servers are ever bundled.
- Give each ported file a header: `Portions derived from dmux/OpenArchFlow@6945080 (MIT)`.
- Keep `vendor/PROVENANCE.json` with the pinned SHAs and the list of files taken.
- Private source is compatible with all three licences.
- Audit OpenArchFlow for vendor icon packs and strip them. Use neutral glyphs plus text provider badges instead.

---

## 2. Layout and Interaction Model (LabVIEW-like)

LabVIEW's split between a **Block Diagram** and a **Front Panel** maps onto two views of the same graph:

- **Diagram:** the topology.
- **Panel:** test inputs, controls, indicators and probe readouts for the current run.

**Shell:**
- **Top bar:** project and revision; mode switch (Design · Simulate · Test · Inventory · Plan); a Run button that turns into a broken-arrow icon when the graph is invalid (click it to open the error list); Cancel.
- **Left:** palette with search, grouped by function (Compute, Model, Tool, Data, Queue, Gateway, Integration). Provider is shown as a filter chip, not a top-level split, which reinforces provider equality. Each item shows a coverage badge.
- **Centre:** canvas.
- **Right dock (tabs):** Architect chat · Inspector · Proposals.
- **Bottom drawer (tabs):** Runs · Trace · Probes · Errors · Metrics.
- **Status bar:** backend state (`Local only` / `Sidecar connected`), zero-key indicator, active mode, head revision.

**Diagram grammar:**
- **Ports are typed** (payload, stream, control, credential reference, metric). Each type gets a colour *and* a shape (circle, chevron, diamond, square) *and* a wire pattern (solid, double, dashed, dotted). Colour is never the only signal.
- **Invalid connections are refused at drag time,** with a tooltip that gives the reason.
- **Probes:** click a wire to attach a numbered probe. The probe value appears in the Probes tab and as a small flag on the wire.
- **Execution highlighting:** an optional "light bulb" toggle. Data tokens move along wires, blocks pulse while running, and each block gets a corner badge (✓ pass, ✕ fail, ⊘ skipped, ◷ running, ⟲ stale).
- **Breakpoints:** a block-level toggle that pauses Test runs and lets you inspect payloads.
- **Subdiagrams:** groups collapse into a single block with exposed ports, LabVIEW SubVI-style.

**Visual identity (restrained AtMem):**
- Muted neutral canvas: about `#F3F3F1` in light mode and `#1C1E20` in dark, with low-contrast dot grid.
- One accent colour for selection and focus.
- Status colours always paired with icons.
- Body text at least 4.5:1 contrast; wires and port glyphs at least 3:1.
- Monospace for payloads.
- No marketing copy in the product chrome.

---

## 3. Five Distinct Planes

Every artifact carries a **plane tag**, a `designRevision`, an `inputsHash` and a provenance record. The planes are never silently merged.

| Plane | What it is | Credentials | Badge |
|---|---|---|---|
| **Design** | Versioned intent graph | None | — |
| **Simulation** | Synthetic latency, throughput, error and cost *estimates* from the heuristic engine | None (zero-key) | `SIM` |
| **Execution / Test** | Local fixture runs, or calls to user-configured *sandbox/staging* endpoints | Explicit opt-in per environment | `RUN` |
| **Observed inventory** | Read-only discovery snapshot with timestamp and source; shown as a *diff* against Design, never auto-applied | Explicit opt-in, read-only | `OBS` |
| **Deploy plan** | Terraform/plan artifacts for staging and production review | None to generate | `PLAN` |

Production is *plan export only*. A human applies it outside AtMem AI Architect.

Simulated numbers are always labelled as estimates, with the engine version and assumptions attached.

---

## 4. Agent-to-Validated-Proposal Protocol

**The agent never mutates the graph.**

**Agent tools:**
- `read_graph(rev)`
- `query_catalog`
- `simulate(rev|draft)`
- `estimate_cost`
- `lookup_docs` (MCP, if enabled)
- `propose_patch`

**Proposal envelope:**
```
{ id, sessionId, baseRevision, ops[] (typed add/update/remove/connect),
  rationale, assumptions[], citations[] (catalog ids / doc URIs),
  phase, riskFlags[] }
```

**Server pipeline:**
1. **Schema validation** against the generated pydantic and Zod models.
2. **Semantic validation:** referential integrity, port type compatibility, catalogue existence, config schema, cycle rules.
3. **Policy validation:** no secrets in config, no ops that trigger deployment, no inventory writes.
4. **Dry-run apply** produces a diff, re-runs validators and, optionally, runs a simulation delta.
5. **If rejected:** structured errors go back to the agent, with at most 2 repair attempts. After that the proposal is surfaced as `rejected`, with reasons.

**Proposal states:** `draft → validated | rejected → presented → accepted (whole or per-op) | dismissed`.

Acceptance creates a new revision (undoable) and records `proposalId` in the revision log.

**Staleness:** if `head ≠ baseRevision`, the server attempts an automatic rebase only when the ops touch disjoint IDs, then re-validates. Otherwise the proposal is marked `stale` and offers "Ask architect to rebase." This extends the MVP's existing revision-bound proposals.

**Phases and the neutral prompt:**
- The four phases become a visible stepper in the chat tab. The user can skip or re-enter any phase.
- Replace the review lens with neutral pillars: reliability, security, cost, performance, operations, sustainability.
- Cite provider-specific frameworks only when a source is actually retrieved.
- **Offline architect:** a deterministic, template- and rule-based proposer built on the catalogue. It keeps the chat functional with zero keys and is clearly labelled.

---

## 5. Cancellation and Stale Results

- **Every job** (run, simulation, agent turn, MCP call) gets a `jobId` and a monotonic `seq` on its events.
- **Browser:** an `AbortController` per job. The worker sim checks a cancel token between nodes.
- **Server:** `POST /jobs/{id}/cancel` sets a cooperative cancel flag. MCP and model calls have timeouts. The ported RateLimiter applies per provider.
- **Late events** for cancelled or superseded jobs are dropped by `jobId`/`seq`.
- **Results are stamped** `{jobId, designRevision, inputsHash}`. When the graph changes, affected block payloads dim with "from rev N" and the badge becomes ⟲. They are kept for comparison, never presented as current.
- **Starting a new run** on the same scope supersedes the old one, with a toast that offers to keep both.

---

## 6. Keyboard and Accessibility

**Navigation:**
- `F6` / `Shift+F6` cycle palette → canvas → right dock → bottom drawer.
- On the canvas: arrow keys do spatial navigation between blocks, `Tab` moves through ports, and `Enter` opens the Inspector.

**Keyboard wiring:**
- With a port focused, `W` opens a searchable "Connect to…" combobox listing only compatible targets.

**Shortcuts:**

| Key | Action |
|---|---|
| `Ctrl/⌘+Enter` | Run |
| `Esc` | Cancel run / close dialog |
| `P` | Probe the focused wire |
| `B` | Breakpoint |
| `Del` | Remove |
| `Ctrl+Z` / `Shift+Ctrl+Z` | Undo / redo |
| `/` | Palette search |
| `?` | Shortcut sheet |

**Outline view:** an editable, screen-reader-friendly table of blocks and connections, equivalent to the canvas.

**Other requirements:**
- `aria-live="polite"` for run progress and `assertive` for failures.
- Respect `prefers-reduced-motion`, which disables token animation.
- Focus rings at least 2px with 3:1 contrast.
- Hit targets at least 24px; ports get an enlarged invisible hit area.

---

## 7. Minimum Local Milestone (M1)

1. **Packages extracted:** `model`, `catalog`, `sim`, `iac`, with ported upstream code, notices and provenance in place.
2. **Catalogue:**
   - AWS, Azure, generic and integration ported and normalised.
   - A hand-authored GCP and IBM *starter* set covering the same core categories.
   - The coverage matrix is visible in the palette.
3. **Simulation:** the ported engine runs in a Web Worker. It is cancellable and seeded, and its per-block metrics appear in the Trace and Metrics tabs.
4. **Sidecar (`127.0.0.1` only):**
   - Random per-launch bearer token passed to the web app.
   - SQLite storing graphs, revisions, runs and proposals.
   - SSE for job events.
5. **Architect:**
   - Phase state machine plus the full proposal pipeline.
   - Offline architect by default.
   - Bedrock (via Strands) and Gemini adapters, enabled only when the user explicitly configures them through the standard SDK credential chain.
   - The app never reads or stores credential files itself.
6. **Optional MCP:** AWS Labs servers launched from a user-supplied command, read-only. Off by default.
7. **Plan export:** Terraform for AWS and Azure via the ported generators, with an optional local `terraform validate` if the binary exists. No `apply` anywhere.
8. **Zero-key guarantee:** with no sidecar and no environment variables, Design, Simulate, fixture Test, the offline architect (limited, in-browser) and JSON import/export all still work.

---

## 8. Candid Integration Gaps

- **RF11 → RF12:** node and edge components need rewriting, not copying. Measured dimensions, hooks and type generics all differ.
- **State:** OpenArchFlow's Zustand store conflicts with the MVP store. Port its *actions* as pure reducers; do not run two stores.
- **Provider parity is a goal, not an M1 fact:**
  - The GCP catalogue is absent upstream, and IBM must be authored from scratch.
  - Pricing via MCP is AWS-only. Azure has a public retail price API. GCP and IBM pricing need separate work or user keys.
  - Terraform coverage is AWS/Azure-weighted.
  - Show the gaps in the coverage matrix rather than hiding them.
- **Simulation fidelity:** the metrics are heuristic and unvalidated against real systems. They must stay labelled as estimates.
- **Two languages:** TS and Python contract drift is a real risk. Mitigate it with JSON Schema generated from Zod and a CI contract test.
- **Agent runtime:** OpenArchFlow's Gemini code is TS and the sample is Python. Consolidate on the Python sidecar and port prompts only.
- **Review content:** the sample's Well-Architected logic is AWS-specific, so expect substantial rewriting for the neutral pillars.
- **Upstream tracking:** use subtree vendoring at the pinned SHAs and schedule periodic diff review. Do not track `main`.

---

## 9. Acceptance Checklist

**Provenance**
- [ ] `THIRD_PARTY_NOTICES.md`, `PROVENANCE.json` and file headers are present.
- [ ] No vendor icon assets are in the bundle.

**Binding and zero-key**
- [ ] The sidecar binds to 127.0.0.1 only and rejects requests without the token.
- [ ] There is no outbound network traffic in zero-key mode (verified with the network panel).
- [ ] Fresh clone + `npm i` + `npm run dev` gives a working Design/Simulate/Test without the sidecar.

**Planes and safety**
- [ ] Every result shows a plane badge and its revision. Stale results are visibly marked.
- [ ] Observed inventory is shown only as a diff and never auto-applied.
- [ ] No code path executes `terraform apply` or any deploy call.
- [ ] No credentials are read except through the user-enabled SDK chain, and none are persisted.

**Proposals and jobs**
- [ ] Agent output reaches the graph only through validated proposals. An invalid proposal shows its errors, and a stale proposal cannot be applied.
- [ ] Cancelling a run within 500 ms stops further block events, and late events are discarded.

**Catalogue and contracts**
- [ ] The coverage matrix is accurate for AWS, Azure, Google and IBM.
- [ ] The MVP JSON and an OpenArchFlow export both import losslessly, or report what was dropped.
- [ ] The pydantic/Zod contract test passes.

**Accessibility**
- [ ] A full build-wire-run-probe flow can be completed by keyboard alone.
- [ ] The outline view is equivalent to the canvas.
- [ ] Axe reports no serious violations, contrast targets are met, and reduced motion is honoured.
