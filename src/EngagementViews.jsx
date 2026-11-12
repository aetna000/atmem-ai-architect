import {InlineNote} from './HelpNote.jsx';
import {BrainActivity} from "./BrainActivity.jsx";
import {systemDescription,requirementExplanation} from './system-description.mjs';
import { resolveCommentRevision } from "./consultation.mjs";
// Consultant views: Discover (qualify), Options and Decisions (design), Build card.
import React from "react";
import { requirementNumber } from "./derive.mjs";
import { Plus, Trash2 } from "lucide-react";
import {
  BRIEF_FIELDS,
  CRITERIA,
  GATE,
  LEVELS,
  OPTIONS,
  STATUSES,
  VERDICTS,
  defaultAssessment,
  newDecision,
  optionScore,
} from "./engagement.mjs";
import { OPTION_NAMES } from "./pack.mjs";
import {
  decisionHistory,
  measureProblem,
  reviseDecision,
} from "./records.mjs";

const area = (props) => <textarea rows={2} {...props} />;

// One understood topic: read as text; edit only when asked.
function Known({ topic, value, onSave }) {
  const [editing, setEditing] = React.useState(false);
  return (
    <div className={`known-item ${topic.state}`}>
      <dt>
        {topic.label}
        {topic.state === "assumed" && <em> · assumed</em>}
        {!editing && (
          <button className="link small" aria-label={`Edit ${topic.label}`} onClick={() => setEditing(true)}>
            Edit
          </button>
        )}
      </dt>
      {editing ? (
        <dd>
          <textarea autoFocus rows={2} aria-label={topic.label} defaultValue={value} onBlur={(e) => (onSave(e.target.value), setEditing(false))} />
        </dd>
      ) : (
        <dd>{value}</dd>
      )}
    </div>
  );
}

// What we've understood from the chat, as a small card on the board.
export function DiscoverView({ project, onChange, topics, open = true, onToggle }) {
  const brief = project.brief || {};
  const useCases = project.useCases || [];
  const setCase = (i, patch) =>
    onChange({ ...project, useCases: useCases.map((u, j) => (j === i ? { ...u, ...patch } : u)) });
  const facts = (project.facts || []).filter((f) => f.name !== "cloud.preference" && f.name !== "data.sensitive");
  const heard = topics.filter((t) => t.state !== "open");
  if (!open) return null;
  return (
    <section className="notes-card" aria-label="Discover">
      <div className="doc-sub">
        <h3>What we know so far</h3>
      </div>
      {heard.length > 0 && (
        <>
          <p className="muted small">Your words — edit anything.</p>
          {facts.length > 0 && (
            <div className="facts">
              {facts.map((f) => (
                <span key={f.id} className={`chip ${f.conflictsWith ? "missing" : ""}`} title={`${f.text} (${f.madeAt})`}>
                  {typeof f.value === "number" ? f.value.toLocaleString("en") : String(f.value)} {f.unit}
                  <button aria-label={`Forget ${f.unit}`} onClick={() => onChange({ ...project, facts: project.facts.filter((x) => x.id !== f.id) })}>
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
          <dl className="known">
            {heard.map((t) => (
              <Known
                key={t.id}
                topic={t}
                value={brief[t.id] || ""}
                onSave={(value) => onChange({ ...project, brief: { ...brief, [t.id]: value } })}
              />
            ))}
          </dl>
          <p className="muted small">
            Still to cover, whenever you're ready:{" "}
            {topics.filter((t) => t.state === "open").map((t) => t.label.toLowerCase()).join(", ") || "nothing — that's everything for now."}
          </p>
        </>
      )}
      <details className="extra">
        <summary>Comparing ideas? Qualify use cases</summary>
        <div className="cases compact">
          {useCases.map((u, i) => (
            <div key={u.id} className={`case verdict-${u.verdict.replace(" ", "-").toLowerCase()}`}>
              <input aria-label="Use case" placeholder="Idea" value={u.title} onChange={(e) => setCase(i, { title: e.target.value })} />
              <div className="seg verdicts">
                {VERDICTS.map((v) => (
                  <button key={v} className={u.verdict === v ? "on" : ""} onClick={() => setCase(i, { verdict: v })}>
                    {v}
                  </button>
                ))}
              </div>
              <button className="icon" aria-label="Remove use case" onClick={() => onChange({ ...project, useCases: useCases.filter((_, j) => j !== i) })}>
                <Trash2 size={13} />
              </button>
            </div>
          ))}
          <button
            className="link small"
            onClick={() =>
              onChange({
                ...project,
                useCases: [...useCases, { id: `uc-${Date.now()}`, title: "", value: "Medium", risk: "Medium", fit: "Medium", verdict: "Park", reason: "" }],
              })
            }
          >
            + Add use case
          </button>
        </div>
      </details>
    </section>
  );
}

export function OptionsView({ project, onDiscuss, onPreview, onChoose, onContinue, busy }) {
  const notes = project.assessment?.notes || {};
  const ready = Object.values(notes).some(Boolean);
  const selected = [...(project.decisions||[])].reverse().find(d=>d.subject==='platform.cloud'&&d.status==='Accepted')?.decision;
  return <section className="doc" aria-label="Choices">
    <header className="doc-head"><h2>Choices</h2></header>
    <button className="btn" onClick={() => onDiscuss('Help me compare AWS, Azure, Google Cloud and IBM for this design. Ask one useful question about my priorities, then refine the comparison from my answer. Populate optionAssessment when enough is known. Keep the diagram unchanged.')}>Discuss cloud options</button>
    {selected && <p className="cloud-selection" role="status"><strong>Selected: {OPTION_NAMES[selected]}</strong> <button className="btn primary" disabled={busy} onClick={onContinue}>Review →</button></p>}
    <DecisionsView project={project} onDiscuss={onDiscuss} embedded/>
    <h3>Cloud alternatives</h3>

    {['current','aws','azure','gcp','ibm'].filter(id => notes[id]).map(id => <article className="consultation-summary" key={id}>
      <h3>{OPTION_NAMES[id]}{selected===id ? " · Selected" : ""}</h3><InlineNote label={`About ${OPTION_NAMES[id]}`}>{notes[id].replace(/^(?:AtMem AI Architect|At[Ff]orma) proposal — confirm: /,'')}</InlineNote>
      <button className="link" onClick={() => onDiscuss(`Explain how ${OPTION_NAMES[id]} fits our design and the main tradeoff. Ask one question to help me decide; keep this as a discussion until I explicitly choose.`)}>Discuss this option</button>
      {id!=="current" && <><button className="link" onClick={()=>onPreview(id)}>Preview service architecture</button><button className="btn primary" disabled={busy||selected===id} onClick={()=>onChoose(id)}>{selected===id ? `${OPTION_NAMES[id]} selected` : `${OPTION_NAMES[id]} →`}</button></>}
    </article>)}
  </section>;
}

export function DecisionsView({ project, onDiscuss, embedded=false }) {
  const all = project.decisions || [];
  const choices = all.filter(d => !d.subject?.startsWith('design.'));
  const current = choices.filter(d => d.status !== 'Superseded');
  const sketches = all.filter(d => d.subject?.startsWith('design.'));
  const labels = {'platform.cloud':'Cloud provider','cloud.region':'Region','data.country':'Country / data residency','infrastructure.tool':'Infrastructure tool'};
  return <section className={embedded?undefined:"doc"} aria-label="Decisions">
    <header className="doc-head"><h2>Selected choices</h2></header>
    <button className="btn" onClick={() => onDiscuss('Review our current design and explicit choices. Explain the next choice we need to make and ask me one useful question. Do not treat a sketch or a suggestion as an accepted decision.')}>Discuss the next choice</button>
    {!current.length && <p className="muted">No choices selected.</p>}
    {current.map(d => <article className="consultation-summary" key={d.id}>
      <h3>{labels[d.subject] || d.title}</h3><p>{OPTION_NAMES[d.decision] || d.decision || 'Still being discussed'}</p>
      <small className="muted">{d.status === 'Accepted' ? 'Confirmed in our conversation' : 'Proposed — still to discuss'}</small>
      {(d.context||d.consequences)&&<InlineNote label="Decision details"><p>{d.context}</p><p>{d.consequences}</p></InlineNote>}
      <button className="link" onClick={() => onDiscuss(`Let’s revisit our choice about ${labels[d.subject] || d.title}: ${d.decision}. Explain the tradeoff and ask what I would like to change before updating it.`)}>Revisit in chat</button>
      {choices.some(h => h.subject===d.subject && h.status==='Superseded') && <details className="extra"><summary>Earlier choices</summary>{choices.filter(h => h.subject===d.subject && h.status==='Superseded').map(h=><p key={h.id}>{h.decision} {h.reason && `— ${h.reason}`}</p>)}</details>}
    </article>)}
    {!!sketches.length && <details className="extra"><summary>Diagram change history</summary>{sketches.map(d=><p key={d.id}>{d.title} · {d.decision}</p>)}</details>}
  </section>;
}

export function BuildCard({ project, run, onChange, onOpen, environment, onEnvironment, onPlan, onPulumi, onPack }) {
  const scope = project.nodes.filter((n) => n.data.poc);
  const tested = run && run.revision === project.revision && run.status !== "running";
  const results = Object.fromEntries(
    (tested ? run.steps : []).flatMap((s) => (s.output?.measures || []).map((m) => [m.label, m])),
  );
  const outputs = project.nodes.filter((n) => n.data.measures?.length);
  const gate = project.gate || {};
  const unowned = (project.decisions || []).filter((d) => !d.owner?.trim()).length;
  return (
    <aside className="deploy build" aria-label="Build">
      <h3>Prototype</h3>
      <p className="muted small">
        {scope.length}/{project.nodes.length} blocks in scope · faded blocks are out
      </p>
      <h4>Success criteria</h4>
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
        <p className="muted small">Add measures to the final check block.</p>
      )}
      <h4>Scale gate</h4>
      {GATE.map((g) => (
        <label key={g.id} className="field">
          {g.label}
          {area({
            "aria-label": g.label,
            placeholder: g.hint,
            value: gate[g.id] || "",
            onChange: (e) => onChange({ ...project, gate: { ...gate, [g.id]: e.target.value } }),
          })}
        </label>
      ))}
      {unowned > 0 && <p className="warn-text small">{unowned} decision{unowned > 1 ? "s" : ""} without an owner</p>}
      <div className="seg">
        {["staging", "production"].map((env) => (
          <button key={env} className={environment === env ? "on" : ""} onClick={() => onEnvironment(env)}>
            {env[0].toUpperCase() + env.slice(1)}
          </button>
        ))}
      </div>
      <div className="row">
        <button className="btn" onClick={onPlan}>
          Export {environment} plan
        </button>
        <button className="btn ghost" onClick={onPulumi}>
          Pulumi
        </button>
      </div>
      <button className="btn primary" onClick={onPack}>
        Client pack
      </button>
    </aside>
  );
}

export function MeasuresEditor({ measures = [], disabled, onChange }) {
  const set = (i, patch) => onChange(measures.map((m, j) => (j === i ? { ...m, ...patch } : m)));
  return (
    <div className="measures">
      <h4>Success measures</h4>
      {measures.map((m, i) => (
        <div key={i} className="measure">
          <input aria-label="Measure label" disabled={disabled} value={m.label} onChange={(e) => set(i, { label: e.target.value })} />
          <input aria-label="Measure field" disabled={disabled} className="mono" value={m.path} onChange={(e) => set(i, { path: e.target.value })} />
          <select aria-label="Measure operator" disabled={disabled} value={m.op} onChange={(e) => set(i, { op: e.target.value })}>
            <option>{">="}</option>
            <option>{"<="}</option>
            <option>{"=="}</option>
          </select>
          <input
            aria-label="Measure target"
            disabled={disabled}
            value={String(m.target)}
            onChange={(e) => {
              const v = e.target.value;
              set(i, { target: v === "true" ? true : v === "false" ? false : v !== "" && !isNaN(Number(v)) ? Number(v) : v });
            }}
          />
          <button className="icon" aria-label="Remove measure" disabled={disabled} onClick={() => onChange(measures.filter((_, j) => j !== i))}>
            <Trash2 size={13} />
          </button>
        </div>
      ))}
      <button
        className="btn ghost"
        disabled={disabled}
        onClick={() => onChange([...measures, { label: "New measure", path: "status", op: "==", target: "passed" }])}
      >
        <Plus size={13} /> Add measure
      </button>
    </div>
  );
}

function RequirementComments({ requirement, comments, onSave, onRemove, target, number, onReview, onResolve, reviewing, onDiscuss }) {
  const [open,setOpen]=React.useState(false), [text,setText]=React.useState(''), [quote,setQuote]=React.useState('');
  const editor=React.useRef(null);
  React.useEffect(()=>{if(target?.id===requirement.id){setQuote(target.quote);setOpen(true);}},[target,requirement.id]);
  React.useEffect(()=>{if(open){editor.current?.focus();editor.current?.scrollIntoView({block:'nearest'});}},[open,target]);
  const save=review=>{onSave(text.trim(),quote,review);setText('');setOpen(false);};
  return <aside className="requirement-comments" aria-label={`Comments on ${requirement.id}`}>
    {comments.filter(c=>!['reviewed','dismissed'].includes(c.status)).map(c=><div className="requirement-comment" key={c.id}>
      <strong>Your feedback on {number}</strong>{c.selectedText && <blockquote>{c.selectedText}</blockquote>}<p>{c.text}</p>
      {c.status==='proposed' ? <div className="requirement-revision">
        <h5>Suggested revision — not applied yet</h5><p className="revision-label">Current wording</p><p>{c.before}</p>
        <p className="revision-label">Proposed wording</p><p className="revision-after">{c.after}</p><p>{c.explanation}</p>
        <button className="requirement-add-comment" onClick={()=>onResolve(c.id,true)}>Apply this revision</button>
        <button className="link" onClick={()=>onResolve(c.id,false)}>Keep current wording</button>
      </div> : <><p className="comment-status">{c.reviewMessage || 'Saved feedback. Ask AtMem AI Architect to suggest wording, then review the change here.'}</p><button className="requirement-add-comment" disabled={reviewing} onClick={()=>onReview([c])}>{reviewing?<><BrainActivity/> Preparing suggestions…</>:'Suggest a revision'}</button><button className="link" onClick={()=>onDiscuss(`Help me clarify my feedback on ${number} (${requirement.id}): ${c.text}. Ask one question before proposing a change.`)}>Discuss feedback</button></>}
      <button className="link" onClick={()=>onRemove(c.id)} aria-label={`Remove comment ${c.id}`}>Remove</button>
    </div>)}
    {comments.some(c=>['reviewed','dismissed'].includes(c.status)) && <section className="comment-history"><h4>Feedback history</h4>{comments.filter(c=>['reviewed','dismissed'].includes(c.status)).map(c=><div key={c.id}><p>{c.text}</p><small>{c.status==='reviewed'?'Revision applied':'Original wording kept'}</small>{c.after&&<p>{c.after}</p>}</div>)}</section>}
    {!open ? <button className="requirement-add-comment" onClick={()=>{setQuote('');setOpen(true);}}>Comment or request a change</button> : <div className="comment-composer">
      <strong>Feedback on {number}</strong>{quote && <blockquote>{quote}</blockquote>}
      <textarea ref={editor} aria-label={`Comment on ${requirement.id}`} value={text} maxLength={500} onChange={e=>setText(e.target.value)} placeholder="What doesn’t fit, what’s missing, or what would you like explained?" />
      <p className="comment-status">AtMem AI Architect will suggest new wording below. You decide whether to apply it.</p>
      <button className="btn" disabled={!text.trim()||reviewing} onClick={()=>save(true)}>Suggest a revision</button>
      <button className="link" disabled={!text.trim()} onClick={()=>save(false)}>Save for later</button>
      <button className="link" onClick={()=>{setOpen(false);setText('');}}>Cancel</button>
    </div>}
  </aside>;
}

export function RequirementsView({checks,onContinue, project, onDiscuss, onChange, onReview, reviewing, onUpload, onOpenProject }) {
  const [commentMenu,setCommentMenu]=React.useState(null), [commentTarget,setCommentTarget]=React.useState(null);
  React.useEffect(()=>{
    if(!commentMenu)return;
    const dismiss=()=>setCommentMenu(null);
    const key=e=>{if(e.key==='Escape')dismiss();};
    document.addEventListener('pointerdown',dismiss);document.addEventListener('keydown',key);window.addEventListener('resize',dismiss);
    return ()=>{document.removeEventListener('pointerdown',dismiss);document.removeEventListener('keydown',key);window.removeEventListener('resize',dismiss);};
  },[commentMenu]);
  function textMenu(event,r) {
    const selection=window.getSelection();
    if(!selection?.rangeCount || selection.isCollapsed)return;
    const range=selection.getRangeAt(0), element=event.currentTarget;
    if(!element.contains(range.startContainer) || !element.contains(range.endContainer))return;
    const quote=selection.toString().trim();if(!quote)return;
    event.preventDefault();event.stopPropagation();
    setCommentMenu({id:r.id,quote:quote.slice(0,1500),x:Math.max(8,Math.min(event.clientX,window.innerWidth-250)),y:Math.max(8,Math.min(event.clientY,window.innerHeight-70))});
  }
  const needs = project.needs || [];
  const comments = project.extensions?.requirementComments || [];
  const pending = comments.filter(c=>c.status==='open' && needs.some(r=>r.id===c.requirementId));
  const saveComments = value => onChange({...project,extensions:{...project.extensions,requirementComments:value}});

  const names = Object.fromEntries(project.nodes.map(n => [n.id, n.data.label]));
  const titles = {suggested:'Suggestions still to discuss',functional:'Functional requirements',security:'Security and access',compliance:'Data governance and compliance',availability:'Availability and recovery',reliability:'Reliability',performance:'Performance',scalability:'Capacity and growth',maintainability:'Operations and maintainability',cost:'Cost constraints',other:'Quality requirements'};
  const groups = new Map();
  for (const r of needs) {
    const key = r.source==='agent' ? 'suggested' : r.kind === 'functional' ? 'functional' : r.category || 'other';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(r);
  }
  const questions = (project.openQuestions || []).filter(q=>q.status==='open');
  const purpose = project.brief?.application || project.requirements;
  const system=systemDescription(project);
  return <section className="doc requirements-document" aria-label="Requirements">
    <div className="requirements-actions">
      {!!pending.length && <button className="btn" disabled={reviewing} onClick={()=>onReview(pending.slice(0,6))}>{reviewing?'Reviewing comments…':'Suggest revisions for saved feedback'} ({Math.min(6,pending.length)})</button>}
    </div>
    {commentMenu && <div className="ctx-menu requirement-text-menu" role="menu" aria-label="Selected text actions" style={{left:commentMenu.x,top:commentMenu.y}} onPointerDown={e=>e.stopPropagation()}>
      <button role="menuitem" ref={node=>node?.focus({preventScroll:true})} onClick={()=>{setCommentTarget({...commentMenu,nonce:Date.now()});setCommentMenu(null);}}>Comment on selected text</button>
    </div>}
    <article className="requirements-paper" aria-label="Requirements document">
      <header className="requirements-cover">
        <p className="document-kicker">AtMem AI Architect · Working requirements</p>
        <h2>{project.name || 'Solution requirements'}</h2>
        <p className="document-subtitle">Where we’ve reached</p>
        <p>This document brings together the requirements developed from our board and discussion. Proposed requirements remain open for review as the design evolves.</p>
        <p className="document-meta">Design revision {project.revision || 1} · Working draft</p>
      </header>
      <section className="requirements-chapter"><h3>Purpose and scope</h3>
        <p>{purpose || 'We are developing the scope together. Describe the outcome you want in chat, and this document will grow with the design.'}</p>
      </section>
      <section className="requirements-chapter"><h3>How the system works</h3><p>{system.overview}</p>{system.flows.map((f,i)=><div className="system-interaction" key={f.id}><h4>{i+1}. {f.title}</h4><p>{f.description}</p><p>{f.contract}</p><p className="document-meta">Proposed verification: {f.validation}</p></div>)}</section>
      <section className="requirements-chapter"><h3>Component responsibilities and design rationale</h3>{system.components.map(c=><section key={c.id} id={`component-spec-${c.id}`} className="system-component"><h4>{c.name}</h4><p className="document-meta">{c.service} · {c.placement}</p><p>{c.purpose}</p><p>{c.boundary}</p><h5>Inputs and outputs</h5><ul>{[...c.inputs,...c.outputs].map((v,i)=><li key={i}>{v}</li>)}</ul>{!c.inputs.length&&!c.outputs.length&&<p>No connections are drawn for this component.</p>}<h5>Contribution to requirements</h5>{c.requirements.length?<ul>{c.requirements.map(r=><li key={r}>{r}</li>)}</ul>:<p>No requirement is explicitly linked to this component yet.</p>}<h5>Implementation and verification</h5><p>{c.implementation}</p><p className="document-meta">Engineering considerations, to be confirmed during implementation:</p><ul>{c.engineering.map(v=><li key={v}>{v}</li>)}</ul></section>)}</section>
      {[...groups].sort(([a],[b])=>(a==='suggested')-(b==='suggested')).map(([key,rows])=>{const Tag='section';return <Tag className="requirements-chapter" key={key}>
        {key==='suggested'?<h4>Suggestions still to discuss ({rows.length})</h4>:<h3>{titles[key] || 'Additional requirements'}</h3>}
        {key==='suggested'&&<p className="document-meta">These are early considerations, not agreed requirements. We’ll discuss the most relevant ones as the design develops.</p>}
        {rows.map(r=><div className="requirement-paragraph" key={r.id}>
          <h4 className="requirement-number">{requirementNumber(project,r.id)}</h4>
          <p className="requirement-text" onContextMenu={event=>textMenu(event,r)}>{r.statement}</p>
          {r.measure && <p className="acceptance-target">Acceptance target: {r.measure.metric} {r.measure.op} {r.measure.target} {r.measure.unit || ''}.</p>}
          <p className="document-meta">{r.source === 'agent' ? 'Proposed for discussion' : 'Recorded from our discussion'}{r.links?.length ? ` · Related design: ${r.links.map(id=>names[id] || 'earlier component').join(', ')}` : ''}</p>
          <div className="requirement-reason"><p><strong>{r.rationale?"Why this matters.":"Design explanation (guidance)."}</strong> {requirementExplanation(r)}</p>{r.basis&&<p className="document-meta">Basis: {r.basis}</p>}<button className="link document-discuss" onClick={()=>onDiscuss(`Explain why ${requirementNumber(project,r.id)} (${r.id}) is needed: ${r.statement}. Use the actual board and discussion as evidence, distinguish assumptions, explain the consequence of leaving it out, and ask whether it fits my needs.`)}>Explain why we need this</button></div>
          <RequirementComments onReview={onReview} reviewing={reviewing} onDiscuss={onDiscuss} onResolve={(id,accept)=>onChange(resolveCommentRevision(project,id,accept))} target={commentTarget} number={requirementNumber(project,r.id)} requirement={r} comments={comments.filter(c=>c.requirementId===r.id)} onSave={(text,selectedText,review)=>{const comment={id:crypto.randomUUID(),requirementId:r.id,text,selectedText,statement:r.statement,status:'open',createdAt:new Date().toISOString()};saveComments([...comments,comment]);if(review)onReview([comment]);}} onRemove={id=>saveComments(comments.filter(c=>c.id!==id))} />
        </div>)}
        <button className="link document-discuss" onClick={()=>onDiscuss(`Let's discuss the ${titles[key] || key} section of our requirements document further. Current requirements: ${rows.map(r=>`${r.id}: ${r.statement}`).join('; ')}. Ask one useful question and refine the document from my answer.`)}>Discuss this section further in chat</button>
      </Tag>;})}
      {!needs.length && <section className="requirements-chapter"><h3>Requirements to develop</h3><p>As we discuss the idea and shape the board, AtMem AI Architect will summarise the functional requirements, constraints and acceptance targets here.</p></section>}
      {!!project.assumptions?.length && <section className="requirements-chapter"><h3>Assumptions to validate</h3>{project.assumptions.map(a=><p key={a.id}>{a.statement}</p>)}</section>}
      {!!questions.length && <section className="requirements-chapter"><h3>Open questions</h3>{questions.map(q=><p key={q.id}>{q.question}</p>)}<button className="link document-discuss" onClick={()=>onDiscuss(`Help resolve the open questions in our requirements document, one at a time. Start with the question that most affects the design.`)}>Let’s work through these in chat</button></section>}
      {checks&&<section className="requirements-chapter"><h3>Design checks and decisions</h3>{checks}</section>}
      <footer className="document-footer">{onContinue&&<button className="btn primary" disabled={reviewing} onClick={onContinue}>Continue to Choices →</button>}</footer>
    </article>
  </section>;
}
