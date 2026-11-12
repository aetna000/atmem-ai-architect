// Review, Estimate and Deploy steps of the AtMem AI Architect journey.
import React from "react";
import { ATTRIBUTES, acceptRisk, blockers } from "./review.mjs";
import { DISCLAIMER, INPUTS, PROJECT_SIZES, setProjectSize, setPrice, setUsage } from "./estimate.mjs";
import { deploymentSteps } from "./document.mjs";
import { GATE } from "./engagement.mjs";
import { DetailedCharges, ConsultingView, ResourcesView } from "./DeliveryViews.jsx";
import { resourcePlan } from "./resources.mjs";

const money = (v, c) => (v == null ? "—" : `${c || ""} ${v.toLocaleString("en", { maximumFractionDigits: 2 })}`.trim());

function Accept({ onAccept }) {
  const [open, setOpen] = React.useState(false),
    [reason, setReason] = React.useState(""),
    [owner, setOwner] = React.useState("");
  if (!open)
    return (
      <button className="link small" onClick={() => setOpen(true)}>
        Accept risk
      </button>
    );
  return (
    <div className="revise">
      <input aria-label="Why accept" placeholder="Why is this acceptable?" value={reason} onChange={(e) => setReason(e.target.value)} />
      <input aria-label="Risk owner" placeholder="Owner" value={owner} onChange={(e) => setOwner(e.target.value)} />
      <button className="btn" disabled={!reason.trim() || !owner.trim()} onClick={() => onAccept(reason, owner)}>
        Accept
      </button>
    </div>
  );
}

export function ReviewView({ project, findings, onChange, onOpen, onAddRequirement }) {
  const names = Object.fromEntries(project.nodes.map((n) => [n.id, n.data.label]));
  const block = blockers(findings);
  const open = findings.filter((f) => f.status === "open");
  return (
    <section className="doc" aria-label="Review">
      <header className="doc-head">
        <h2>Review</h2>
        <p className="muted">
          {block.length
            ? `${block.length} blocker${block.length > 1 ? "s" : ""} to fix before deployment.`
            : open.length
              ? `No blockers. ${open.length} thing${open.length > 1 ? "s" : ""} worth a look.`
              : "Nothing open. Rules run on every change."}
        </p>
      </header>
      <details className="extra"><summary>Agreed choices and consequences</summary>{(project.decisions||[]).filter(d=>d.status==='Accepted').map(d=><article key={d.id||d.subject}><strong>{d.title||d.subject}</strong><p>{d.decision}</p>{d.context&&<p>{d.context}</p>}{d.consequences&&<p>{d.consequences}</p>}</article>)}</details>
      {ATTRIBUTES.map(([id, label]) => {
        const fs = findings.filter((f) => f.attribute === id);
        if (!fs.length) return null;
        return (
          <div key={id} className="finding-group">
            <h3>{label}</h3>
            {fs.map((f) => (
              <article key={f.key} className={`finding sev-${f.severity} ${f.status}`}>
                <div className="finding-head">
                  <span className={`sev ${f.severity}`}>{f.severity}</span>
                  <strong>{f.statement}</strong>
                </div>
                <p className="muted">{f.rationale}</p>
                <p>{f.action}</p>
                <div className="finding-foot">
                  {f.components.map((c) => (
                    <button key={c} className="chip" onClick={() => onOpen(c)}>
                      {names[c] || c}
                    </button>
                  ))}
                  <span className="muted small">{f.source}</span>
                  {["AVL-001", "PRF-001"].includes(f.rule) && f.status === "open" && (
                    <button className="link small" onClick={() => onAddRequirement(f.rule === "AVL-001" ? "availability" : "performance")}>
                      Add target
                    </button>
                  )}
                  {f.status === "accepted" ? (
                    <span className="small">
                      Accepted by {f.acceptance.owner}: {f.acceptance.reason}
                    </span>
                  ) : (
                    <Accept onAccept={(reason, owner) => onChange(acceptRisk(project, f, reason, owner))} />
                  )}
                </div>
              </article>
            ))}
          </div>
        );
      })}
    </section>
  );
}

export function EstimateView({ project, result, onChange, onEstimate, busy=false, pricing }) {
  const e = result;
  return (
    <section className="doc" aria-label="Estimate">
      <header className="doc-head">
        <h2>1. Cost estimate</h2>
        <p className="muted">Choose a size; usage and available regional prices are calculated for you. {DISCLAIMER}</p>
      </header>
      <fieldset disabled={busy||pricing?.busy}><legend>How large do you expect this project to be?</legend>
        <div className="row">{PROJECT_SIZES.map(size=><button type="button" className="btn" key={size.id} aria-pressed={project.estimate?.projectSize===size.id} onClick={()=>{const next=setProjectSize(project,size.id);onChange(next);onEstimate?.(next);}}>{size.label}</button>)}</div>
        <details className="cost-assumptions"><summary>Planning assumptions</summary><p className="muted small">Small: 10,000 requests / 10 GB; Medium: 100,000 / 100 GB; Large: 1 million / 1 TB; Extra Large: 10 million / 10 TB per month. Existing usage figures take priority. Model assumptions: 3,000 tokens per request and 730 endpoint hours; training usage needs separate agreement.</p></details>
      </fieldset>
      {pricing?.busy&&<p role="status">Calculating costs…</p>}{pricing?.errors?.map((error,i)=><p className="warn-text" key={i}>{error.component&&`${error.component}: `}{error.reason} <button className="link" disabled={busy||pricing?.busy} onClick={()=>onEstimate?.(project)}>Retry pricing</button></p>)}
      {onEstimate&&project.estimate?.projectSize&&<button className="link" disabled={busy||pricing?.busy} onClick={()=>onEstimate(project)}>Refresh prices</button>}
      <div className="totals">
        <div>
          <small className="muted">Estimated subtotal / month</small>
          <strong>{e.lines.some((l) => l.cost != null) ? e.expected===0&&e.preciseExpected>0?`< ${money(0.01,e.currency)}`:money(e.expected, e.currency) : "—"}</strong>
        </div>
        <div>
          <small className="muted">Range</small>
          <span>
            {e.lines.some((l) => l.cost != null) ? `${money(e.low, e.currency)} – ${money(e.high, e.currency)}` : "—"}
          </span>
        </div>
        <div>
          <small className="muted">Status</small>
          <span className={e.complete ? "ok-text" : "warn-text"}>
            {e.complete ? "All entered charges estimated" : e.mixedCurrencies ? "Currency needs review" : "Partial estimate · see exclusions"}
          </span>
        </div>
        {e.budget && (
          <div>
            <small className="muted">Budget</small>
            <span className={e.budget.comparable && e.expected > e.budget.amount ? "bad-text" : ""}>
              {e.budget.currency} {e.budget.amount.toLocaleString("en")}
              {e.budget.comparable ? (e.expected > e.budget.amount ? " · over" : " · within") : " · not compared"}
            </span>
          </div>
        )}
      </div>
      <p className="muted small">The subtotal includes priced charges only. Architect needs to resolve unpriced services before this becomes a full estimate.</p>
      {e.drivers.length > 0 && (
        <p className="small">
          Biggest drivers: {e.drivers.map((d) => `${d.component} (${money(d.cost, d.price.currency)})`).join(", ")}
        </p>
      )}
      {e.lines.some(l=>l.cost==null)&&<p role="status">{e.lines.filter(l=>l.cost==null).length} charges await {e.lines.some(l=>l.quantity==null)?'usage assumptions or service pricing':'service pricing'}. {onEstimate?'Available prices are fetched automatically. Review the listed exclusions or retry pricing; you do not need to enter every charge.':'Service prices must be connected before these charges can be calculated.'}</p>}
      <details className="extra"><summary>Cost breakdown and price sources</summary><div className="resource-schedule" aria-label="Estimate breakdown">{e.lines.map(l=><article key={l.id}><strong>{l.component} · {l.driver}</strong><span>{l.cost==null?'Not yet estimated':money(l.cost,l.price.currency)+'/month'}</span><small>{l.note||l.price?.note}</small><small>{l.quantity??'Usage unresolved'} {l.unit}{l.price&&<> · {l.price.source}{l.price.url&&<> · <a href={l.price.url} target="_blank" rel="noreferrer">price source</a></>}</>}</small></article>)}</div></details>
      <details className="extra"><summary>Adjust usage assumptions and prices</summary>
      {e.lines.some((l) => !l.detailed) && <>
      <div className="doc-sub">
        <h3>Usage</h3>
      </div>
      <div className="usage">
        {INPUTS.filter((i) => e.lines.some((l) => l.inputs.includes(i.id))).map((i) => {
          const u = e.usage[i.id];
          return (
            <label key={i.id} className="field">
              {i.label}
              <input
                aria-label={i.label}
                inputMode="decimal"
                placeholder={u.value != null ? String(u.value) : "unknown"}
                value={project.estimate?.usage?.[i.id] ?? ""}
                onChange={(ev) => onChange(setUsage(project, i.id, ev.target.value))}
              />
              <small className={u.source === "needed" ? "warn-text" : "muted"}>
                {u.source === "needed" ? "needed by a line below" : `${u.value?.toLocaleString("en")} ${i.unit} · ${u.source}`}
              </small>
              {i.hint && <small className="muted">{i.hint}</small>}
            </label>
          );
        })}
      </div>
      </>}
      {e.lines.some((l) => !l.detailed) &&
      <div className="doc-sub">
        <h3>Lines</h3>
        <span className="muted small">Price per unit, with where it came from.</span>
      </div>
      }
      {e.lines.some((l) => !l.detailed) ? (
        <div className="lines">
          {e.lines.filter((l) => !l.detailed).map((l) => {
            const p = project.estimate?.prices?.[l.id] || {};
            const set = (patch) => onChange(setPrice(project, l.id, patch));
            return (
              <div key={l.id} className={`line ${l.status.replace(" ", "-")}`}>
                <span>
                  <strong>{l.component}</strong>
                  <small className="muted">
                    {l.driver} · {l.quantity == null ? `needs ${l.missing.map((m) => INPUTS.find((i) => i.id === m).label.toLowerCase()).join(", ")}` : `${l.quantity.toLocaleString("en")} ${l.unit}`}
                  </small>
                </span>
                <input
                  aria-label={`${l.component} unit price`}
                  inputMode="decimal"
                  placeholder={`price / ${l.unit}`}
                  value={p.price ?? ""}
                  onChange={(ev) => set({ price: ev.target.value === "" ? undefined : Number(ev.target.value) })}
                />
                <input aria-label={`${l.component} currency`} className="cur" value={p.currency || "USD"} onChange={(ev) => set({ currency: ev.target.value.toUpperCase().slice(0, 3) })} />
                <input aria-label={`${l.component} price source`} placeholder="source or URL" value={p.url || (p.source && p.source !== "entered by you" ? p.source : "")} onChange={(ev) => set({ url: ev.target.value })} />
                <span className="cost">{l.cost == null ? <em className="muted">{l.status}</em> : money(l.cost, l.price.currency)}</span>
              </div>
            );
          })}
        </div>
      ) : (
        !project.nodes.length && <p className="muted">Sketch a design first; lines appear for each component that has a running cost.</p>
      )}
      {e.notCosted.length > 0 && <p className="muted small">Not costed in this release: {e.notCosted.join(", ")}.</p>}
      <div className="row small">
        <label className="inline">
          Low ×
          <input aria-label="Low factor" value={e.factors.low} onChange={(ev) => onChange({ ...project, estimate: { ...(project.estimate || {}), low: Number(ev.target.value) || 0 } })} />
        </label>
        <label className="inline">
          High ×
          <input aria-label="High factor" value={e.factors.high} onChange={(ev) => onChange({ ...project, estimate: { ...(project.estimate || {}), high: Number(ev.target.value) || 0 } })} />
        </label>
      </div>
      </details>
      <details className="extra"><summary>Advanced charge worksheet</summary><DetailedCharges project={project} onChange={onChange} /></details>
      {e.lines.some((l) => l.detailed) && <div className="resource-schedule" aria-label="Detailed cost breakdown">{e.lines.filter((l) => l.detailed).map((l) => <article key={l.id}><strong>{l.component} · {l.driver}</strong><span>{l.quantity ?? "?"} {l.unit} × {l.price ? money(l.price.price, l.price.currency) : "price needed"} = {l.cost == null ? l.status : money(l.cost, l.price.currency)}/month</span></article>)}</div>}
      <details className="extra"><summary>What we still need for a full estimate · {e.gaps.length} worksheet gaps</summary><ul>{e.gaps.map((g,i) => <li key={i}>{g}</li>)}</ul><p className="muted small">Check networking, security, logging, backups, support, licences, taxes and delivery effort. A detailed worksheet still needs validation against the selected services.</p></details>
      <details className="extra"><summary>Optional delivery effort estimate</summary><ConsultingView project={project} onChange={onChange} /></details>
    </section>
  );
}

export function DeployView({ project, findings, environment, onEnvironment, onPlan, onPulumi, onDocument, onPack, onTerraform, onChange }) {
  const block = blockers(findings);
  const infrastructure = resourcePlan(project);
  const gate = project.gate || {};
  return (
    <section className="doc" aria-label="Deploy">
      <header className="doc-head">
        <h2>Deploy</h2>
        <p className="muted">A reviewable plan and document. AtMem AI Architect never provisions anything on its own.</p>
      </header>
      <div className="ready no">
        <strong>{block.length ? "Not ready for deployment" : "No automated review blockers"}</strong>
        {!block.length && <p className="small">{infrastructure.gaps.length ? `${infrastructure.gaps.length} infrastructure and integration tasks remain.` : "Infrastructure and account validation are still required."}</p>}
        {block.length > 0 && (
          <ul>
            {block.map((f) => (
              <li key={f.key}>{f.statement}</li>
            ))}
          </ul>
        )}
      </div>
      <div className="row">
        <div className="seg">
          {["staging", "production"].map((env) => (
            <button key={env} className={environment === env ? "on" : ""} onClick={() => onEnvironment(env)}>
              {env[0].toUpperCase() + env.slice(1)}
            </button>
          ))}
        </div>
        <button className="btn primary" onClick={onDocument}>
          Deployment document
        </button>
        <button className="btn primary" onClick={onPack}>Download delivery pack</button>
        <button className="btn" onClick={onTerraform}>Terraform sketch</button>
        <button className="btn" onClick={onPlan}>
          Export {environment} plan
        </button>
        <button className="btn ghost" onClick={onPulumi}>
          Pulumi
        </button>
      </div>
      <p className="muted small">The delivery pack includes the specification, diagram, decisions, estimates, resource schedule, editable project and Terraform sketch, all from the current snapshot. Change the project and regenerate it.</p>
      <p className="warn-text small">Deployment access and execution are not connected. Resource coverage and implementation work are listed below; automated review alone cannot establish deployment readiness.</p>
      <ResourcesView project={project} />
      <div className="doc-sub">
        <h3>Draft steps</h3>
        <span className="muted small">Validate against the provider's documentation before use.</span>
      </div>
      <ol className="steps-list">
        {deploymentSteps(project).map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ol>
      <details className="extra">
        <summary>Scale gate — scale only when value exceeds cost and risk</summary>
        {GATE.map((g) => (
          <label key={g.id} className="field">
            {g.label}
            <textarea
              rows={2}
              aria-label={g.label}
              placeholder={g.hint}
              value={gate[g.id] || ""}
              onChange={(e) => onChange({ ...project, gate: { ...gate, [g.id]: e.target.value } })}
            />
          </label>
        ))}
      </details>
    </section>
  );
}

// Test run companion card: what's in scope and whether the success measures passed.
export function TestCard({ project, run, onOpen }) {
  const tested = run && run.revision === project.revision && run.status !== "running";
  const results = Object.fromEntries((tested ? run.steps : []).flatMap((s) => (s.output?.measures || []).map((m) => [m.label, m])));
  const outputs = project.nodes.filter((n) => n.data.measures?.length);
  return (
    <aside className="deploy build" aria-label="Test">
      <h3>Test run</h3>
      <p className="small">Runs each block in order with built-in sample data, on this computer. No AI model is called, nothing touches a cloud account, and it costs nothing.</p>
      <p className="muted small">Faded blocks are outside the prototype scope.</p>
      {outputs.length ? (
        <ul className="checks">
          {outputs.flatMap((n) =>
            n.data.measures.map((m) => {
              const r = results[m.label];
              return (
                <li key={n.id + m.label} className={r ? (r.pass ? "ok" : "bad") : ""}>
                  <button className="link-plain" onClick={() => onOpen(n.id)}>
                    {m.label} {m.op} {String(m.target)}
                    {r && <span className="muted"> · {String(r.value)}</span>}
                  </button>
                </li>
              );
            }),
          )}
        </ul>
      ) : (
        <p className="muted small">Success measures live on a final check block.</p>
      )}
    </aside>
  );
}

const when = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  const mins = Math.round((Date.now() - d) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  if (mins < 60 * 24) return `${Math.round(mins / 60)} h ago`;
  return d.toLocaleDateString();
};

// Projects saved under your account on this computer, with a rubbish bin.
export function ProjectsDialog({ list, currentId, onOpen, onNew, onBin, onRestore, onPurge, folder }) {
  const [confirm, setConfirm] = React.useState(null);
  return (
    <div className="projects">
      <div className="row-between">
        <h2>Projects</h2>
        <button className="button run-button" onClick={onNew}>
          New project
        </button>
      </div>
      {list.projects.length ? (
        <ul className="project-list">
          {list.projects.map((p) => (
            <li key={p.id} className={p.id === currentId ? "current" : ""}>
              <button className="open" onClick={() => onOpen(p.id)} disabled={p.id === currentId}>
                <strong>{p.name}</strong>
                <small>
                  {p.id === currentId ? "open now" : when(p.updatedAt)} · {p.blocks} block{p.blocks === 1 ? "" : "s"}
                </small>
              </button>
              <button className="icon bin" aria-label={`Move ${p.name} to the bin`} title="Move to bin" onClick={() => onBin(p.id)}>
                🗑
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">No saved projects yet. Your current one saves itself as you work.</p>
      )}
      {list.bin.length > 0 && (
        <details className="bin-list">
          <summary>Rubbish bin · {list.bin.length}</summary>
          <ul className="project-list">
            {list.bin.map((p) => (
              <li key={p.id}>
                <span className="open">
                  <strong>{p.name}</strong>
                  <small>binned {when(p.binnedAt)}</small>
                </span>
                <button className="btn" onClick={() => onRestore(p.id)}>
                  Restore
                </button>
                {confirm === p.id ? (
                  <button className="btn danger" onClick={() => (onPurge(p.id), setConfirm(null))}>
                    Delete forever?
                  </button>
                ) : (
                  <button className="btn ghost danger" onClick={() => setConfirm(p.id)}>
                    Delete
                  </button>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
      <p className="modal-fine">{folder || "~/.atforma"}</p>
    </div>
  );
}
