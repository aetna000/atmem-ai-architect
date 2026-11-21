import React from "react";
import { consultingEstimate, WORK_PHASES, setDetail } from "./estimate.mjs";
import { resourcePlan } from "./resources.mjs";
const amount = (n, c) => n == null ? "Not estimated" : `${c} ${n.toLocaleString("en", { maximumFractionDigits: 2 })}`;
const number = (s) => s === "" || !Number.isFinite(Number(s)) || Number(s) < 0 ? undefined : Number(s);

export function DetailedCharges({ project, onChange }) {
  const lines = project.estimate?.details || [];
  const components = project.nodes.filter((n) => n.data.kind !== "note");
  const change = (details) => onChange({ ...project, estimate: { ...(project.estimate || {}), details } });
  return <details className="extra" aria-label="Detailed cloud charges">
    <summary>Model detailed cloud costs</summary>
    <p className="muted small">Add each billable dimension: for example input tokens, output tokens, requests, compute, storage and transfer. Detailed lines replace the coarse ROM line for that component. Enter a zero-cost line and explain why for an existing or free component.</p>
    {lines.map((l, index) => {
      const set = (patch) => onChange(setDetail(project, l.id, patch));
      return <fieldset className="charge-editor" key={l.id}>
        <legend>Charge {index + 1}</legend>
        <div className="delivery-fields">
          <label className="field">Component<select aria-label={`Charge ${index + 1} component`} value={l.componentId} onChange={(e) => set({ componentId: e.target.value })}>
            {!components.some((n) => n.id === l.componentId) && <option value={l.componentId}>Removed component — reassign</option>}
            {components.map((n) => <option key={n.id} value={n.id}>{n.data.label}</option>)}
          </select></label>
          {[['description','Charge description'],['quantity','Monthly quantity'],['unit','Unit'],['price','Unit price'],['currency','Currency'],['service','Service or SKU'],['region','Price region'],['source','Price source or quote'],['date','Price date']].map(([key,label]) => <label className="field" key={key}>{label}<input aria-label={`Charge ${index + 1} ${label.toLowerCase()}`} type={key === 'date' ? 'date' : 'text'} inputMode={['quantity','price'].includes(key) ? 'decimal' : undefined} value={l[key] ?? ''} onChange={(e) => set({ [key]: ['quantity','price'].includes(key) ? number(e.target.value) : key === 'currency' ? e.target.value.toUpperCase().slice(0,3) : e.target.value })} /></label>)}
        </div>
        <button className="btn ghost danger" onClick={() => change(lines.filter((x) => x.id !== l.id))}>Remove charge {index + 1}</button>
      </fieldset>;
    })}
    <button className="btn" disabled={!components.length} onClick={() => change([...lines, { id: `charge-${crypto.randomUUID()}`, componentId: components[0].id, description: "", unit: "", currency: "USD", source: "", date: new Date().toISOString().slice(0,10), region: "", service: "" }])}>Add cloud charge</button>
  </details>;
}

export function ConsultingView({ project, onChange }) {
  const c = project.estimate?.consulting || {}, result = consultingEstimate(project);
  const set = (patch) => onChange({ ...project, estimate: { ...(project.estimate || {}), consulting: { ...c, ...patch } } });
  return <details className="extra" aria-label="Consulting and build estimate">
    <summary>Consulting and build estimate · one-off</summary>
    <p className="muted small">Enter person-days and your day rate; no rates or effort are assumed. Give the basis, scope and exclusions. Use zero days with a reason if a phase is out of scope. Person-days are effort, not calendar duration.</p>
    <label className="field">Consulting currency<input aria-label="Consulting currency" value={c.currency || "USD"} onChange={(e) => set({ currency: e.target.value.toUpperCase().slice(0,3) })} /></label>
    <div className="totals"><div><small>Expected one-off subtotal</small><strong>{amount(result.expected, result.currency)}</strong></div><div><small>Range</small><span>{result.low == null ? '—' : `${amount(result.low, result.currency)} – ${amount(result.high, result.currency)}`}</span></div><div><small>Status</small><span>{result.complete ? "All work packages estimated" : "Incomplete — work packages need estimates"}</span></div></div>
    {WORK_PHASES.map(([id,label]) => {
      const phase = c.phases?.[id] || {};
      const edit = (patch) => set({ phases: { ...(c.phases || {}), [id]: { ...phase, ...patch } } });
      return <fieldset className="charge-editor" key={id}><legend>{label}</legend><div className="delivery-fields">
        {[['lowDays','Low days'],['days','Expected days'],['highDays','High days'],['rate','Day rate']].map(([key,name]) => <label className="field" key={key}>{name}<input aria-label={`${label} ${name.toLowerCase()}`} inputMode="decimal" value={phase[key] ?? ''} onChange={(e) => edit({ [key]: number(e.target.value) })} /></label>)}
        <label className="field delivery-basis">Basis, scope and exclusions<textarea rows={2} aria-label={`${label} basis`} value={phase.basis || ''} onChange={(e) => edit({ basis: e.target.value })} /></label>
      </div></fieldset>;
    })}
    <p className="muted small">Separate from cloud running costs. Taxes, licences, ongoing support and migration are excluded unless explicitly included.</p>
  </details>;
}

export function ResourcesView({ project }) {
  const plan = resourcePlan(project);
  return <details className="extra" aria-label="Cloud resource schedule"><summary>Resources and infrastructure coverage · {plan.rows.length} components</summary>
    <p className="muted small">Derived from the current diagram. Generic services need confirmation. S3 foundation code covers buckets and their controls; drawn wires still need application integration and IAM.</p>
    <div className="resource-schedule">{plan.rows.map((r) => <article key={r.id}><strong>{r.label}</strong><span>{r.provider.toUpperCase()} · {r.service} · {r.region}</span><small>{r.existing ? "Existing system" : r.selection} · {r.terraform}</small><small>{r.resources.join(', ') || 'Resource types to confirm'}</small><small>Cost dimensions: {r.costDrivers}</small></article>)}</div>
    {plan.gaps.length > 0 && <p className="warn-text small">{plan.gaps.length} resource or integration tasks remain. The full list is included in the delivery pack.</p>}
  </details>;
}
