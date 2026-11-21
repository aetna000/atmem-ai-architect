import {BrainActivity} from "./BrainActivity.jsx";
import React, { useState } from "react";
import { Cloud, Code2, GitBranch, Plus, ShieldCheck, Sparkles, Upload } from "lucide-react";
import { PROVIDERS, pdmTemplate, template } from "./core.mjs";
import {
  UPSTREAM_TEMPLATES,
  importDiagram,
  loadUpstreamTemplate,
} from "./integrations.ts";
import { importPulumiSnapshot, snapshotToProject } from "./pulumi.mjs";
const PROVIDER_OPTIONS = [
  ["claude-code", "Claude", "account"],
  ["codex", "ChatGPT", "account"],
  ["copilot", "GitHub Copilot", "account"],
  ["gemini-cli", "Gemini", "account"],
  ["anthropic", "Claude", "key"],
  ["openai", "OpenAI", "key"],
  ["gemini-api", "Gemini", "key"],
  ["xai", "Grok", "key"],
  ["bedrock", "Amazon Bedrock", "aws"],
];
const DEFAULT_MODEL = { anthropic: "claude-opus-5-5" };
// Neutral monograms in each provider's familiar colour (no vendor logo files are bundled).
const MONO = {
  "claude-code": ["C", "#d97757"],
  codex: ["G", "#10a37f"],
  copilot: ["Co", "#24292f"],
  "gemini-cli": ["G", "#4285f4"],
  anthropic: ["C", "#b4583a"],
  openai: ["O", "#0d8a6a"],
  "gemini-api": ["G", "#1a73e8"],
  xai: ["X", "#000000"],
  bedrock: ["B", "#1f777c"],
};
export const EFFORT_LABEL = { none: "Instant", minimal: "Instant", low: "Fast", medium: "Balanced", high: "Deep", xhigh: "Deeper", max: "Max", ultra: "Ultra" };

// Pick the readable foreground for each solid provider badge background.
function badgeInk(hex){
 const channels=hex.replace('#','').match(/../g).map(v=>parseInt(v,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);
 const luminance=.2126*channels[0]+.7152*channels[1]+.0722*channels[2];
 return luminance>.179?'#000':'#fff';
}

// Check your connection: pick a provider, sign in from here if needed, check, continue.
export function Connections({ session, connection, onCheck, onSave, onRetry, welcome = false }) {
  const [choice, setChoice] = useState(connection?.provider || "claude-code"),
    [model, setModel] = useState(connection?.model || "claude-opus-5-5"),
    [key, setKey] = useState(""),
    [state, setState] = useState("idle"),
    [error, setError] = useState(""),
    [list, setList] = useState([]),
    [effort, setEffort] = useState(connection?.effort || ""),
    [reason, setReason] = useState(""),
    [keyStored, setKeyStored] = useState(0);
  const kind = PROVIDER_OPTIONS.find((o) => o[0] === choice)?.[2];
  const capability = session?.providers?.[choice];
  const name = PROVIDER_OPTIONS.find((o) => o[0] === choice)?.[1];
  const signedIn = capability?.signedIn;
  // Step 1 is signing in (or a working key); only then do models appear to choose from.
  const ready =
    !!session &&
    (kind === "account" ? capability?.installed && signedIn !== false : capability?.available);
  const listed = list.find((m) => m.id === model);
  const efforts = listed?.efforts || [];
  const choiceNow = { provider: choice, model: model.trim(), ...(effort && efforts.includes(effort) ? { effort } : {}) };
  // Real models and thinking levels, as the provider's own CLI reports them.
  React.useEffect(() => {
    if (!session) return;
    let live = true;
    fetch("/api/models", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.token}` },
      body: JSON.stringify({ provider: choice }),
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(Error(r.status === 404 ? "AtMem AI Architect's helper is out of date — restart it with npm run local." : "Couldn't load models."))))
      .then(({ models, reason }) => {
        if (!live) return;
        setList(models || []);
        setReason(reason || "");
        const keep = (models || []).find((m) => m.id === model);
        const pick = keep || models?.[0];
        if (pick) {
          setModel(pick.id);
          if (!pick.efforts?.includes(effort)) setEffort(pick.defaultEffort || pick.efforts?.[0] || "");
        } else setModel("");
      })
      .catch((e) => {
        if (!live) return;
        setError(e.message);
      });
    return () => {
      live = false;
    };
  }, [choice, session?.token, signedIn, capability?.available, keyStored]);

  async function signIn() {
    setError("");
    setState("signing-in");
    try {
      const response = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.token}` },
        body: JSON.stringify({ provider: choice }),
      });
      const result = await response.json();
      if (!response.ok) throw Error(result.detail || "Couldn't start sign-in.");
      if (result.url) window.open(result.url, "_blank", "noopener");
      // Wait for the provider's page to finish; the CLI reports when it's done.
      for (let i = 0; i < 60; i++) {
        await new Promise((r) => setTimeout(r, 2000));
        const latest = await onRetry();
        if (latest?.providers?.[choice]?.signedIn) return setState("idle");
      }
      setState("idle");
      setError("Sign-in didn't finish. Try again.");
    } catch (e) {
      setState("idle");
      setError(e.message);
    }
  }
  async function storeKey() {
    setError("");
    try {
      const response = await fetch("/api/credentials", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.token}` },
        body: JSON.stringify({ provider: choice, key: key.trim() }),
      });
      if (!response.ok) throw Error("Couldn't use that key.");
      setKey("");
      setKeyStored((n) => n + 1);
      await onRetry();
    } catch (e) {
      setError(e.message);
    }
  }
  async function check() {
    setError("");
    setState("checking");
    try {
      if (kind === "key" && key.trim()) await storeKey();
      await onCheck(choiceNow);
      setState("ok");
    } catch (e) {
      setState("idle");
      setError(e.message);
    }
  }
  const blocked =
    !ready ||
    !model ||
    (kind === "account" && !capability?.installed) ||
    (kind === "key" && !capability?.available && !key.trim()) ||
    (kind === "aws" && !capability?.available);
  return (
    <div className="connect">
      <h2>{welcome ? "AI providers" : "AI providers"}</h2>
      {!session && (
        <p className="error-box">
          Looks like AtMem AI Architect's helper isn't running. Start it with <code>npm run local</code>, then{" "}
          <button className="link" onClick={onRetry}>
            retry
          </button>
          .
        </p>
      )}
      <div className="provider-grid" role="radiogroup" aria-label="Provider">
        {PROVIDER_OPTIONS.map(([id, label, how]) => {
          const cap = session?.providers?.[id];
          return (
            <button
              key={id}
              role="radio"
              aria-checked={choice === id}
              aria-label={label}
              className={`provider-tile ${choice === id ? "on" : ""}`}
              disabled={state === "checking" || state === "signing-in"}
              onClick={() => {
                setChoice(id);
                setModel(DEFAULT_MODEL[id] || "");
                setList([]);
                setKey("");
                setError("");
                setState("idle");
              }}
            >
              <span className="mono" style={{ background: MONO[id][1], color:badgeInk(MONO[id][1]) }}>
                {MONO[id][0]}
              </span>
              <span>
                {label}
                <small>{how === "account" ? (cap?.signedIn ? "Signed in" : "Sign in") : how === "key" ? "API key" : "AWS credentials"}</small>
              </span>
              {cap?.signedIn && (
                <span className="signed" aria-hidden="true">
                  ✓
                </span>
              )}
            </button>
          );
        })}
      </div>
      {kind === "account" && session && (
        <div className="signin">
          {!capability?.installed ? (
            <span className="warn-text">{name} app not found on this computer.</span>
          ) : signedIn ? (
            <span className="ok-text">✓ Signed in</span>
          ) : state === "signing-in" ? (
            <span className="muted">Finish signing in on the page that opened…</span>
          ) : capability?.canSignInFromApp ? (
            <button className="btn" onClick={signIn}>
              Sign in to {name}
            </button>
          ) : (
            <span className="muted">Sign-in is checked when you press Check.</span>
          )}
        </div>
      )}
      {kind === "key" && (
        <label className="dialog-field">
          API key
          <input
            type="password"
            autoComplete="off"
            aria-label="Provider API key"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder={capability?.available ? "Already set" : "Paste key"}
          />
          {key.trim() && (
            <button type="button" className="btn ghost" onClick={storeKey}>
              Use this key
            </button>
          )}
        </label>
      )}
      {ready && (
        <>
      <label className="dialog-field">
        Model {!list.length&&!reason&&<BrainActivity size={22}/>}
        <select
          aria-label="Model"
          value={model}
          disabled={!list.length}
          onChange={(e) => {
            const m = list.find((x) => x.id === e.target.value);
            setModel(e.target.value);
            if (!m?.efforts?.includes(effort)) setEffort(m?.defaultEffort || m?.efforts?.[0] || "");
          }}
        >
          {list.length ? (
            list.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))
          ) : (
            <option value="">{!session ? "Waiting for AtMem AI Architect's helper…" : reason || "Loading your models…"}</option>
          )}
        </select>
      </label>
      {efforts.length > 0 && (
        <div className="dialog-field">
          Thinking
          <div className="seg effort" role="radiogroup" aria-label="Thinking">
            {efforts.map((e) => (
              <button key={e} role="radio" aria-checked={effort === e} className={effort === e ? "on" : ""} onClick={() => setEffort(e)}>
                {EFFORT_LABEL[e] || e}
              </button>
            ))}
          </div>
        </div>
      )}
        </>
      )}
      {error && (
        <p role="status" className="error-box">
          {error}
        </p>
      )}
      {state === "ok" ? (
        <>
          <p className="ok-text">
            ✓ Works — {name} · {listed?.name || model}
            {choiceNow.effort ? ` · ${EFFORT_LABEL[choiceNow.effort] || choiceNow.effort}` : ""}
          </p>
          <button className="button run-button full" onClick={() => onSave(choiceNow)}>
            Continue
          </button>
        </>
      ) : (
        <button className="button run-button full" disabled={blocked || state !== "idle"} onClick={check}>
          {state === "checking" ? <><BrainActivity/> Checking…</> : "Check"}
        </button>
      )}
    </div>
  );
}

export function TemplateDialog({ onLoad }) {
  return (
    <>
      <h2>Templates</h2>
      <div className="section-label">Predictive maintenance · runnable</div>
      <div className="template-list">
        {["aws", "azure", "gcp", "ibm"].map((p) => (
          <button key={p} onClick={() => onLoad(pdmTemplate(p))}>
            <Sparkles size={19} />
            <span>
              <strong>Predictive maintenance · {PROVIDERS[p].name}</strong>
              <small>Sensors → ML pipeline → GenAI insights → existing app</small>
            </span>
            <Plus size={16} />
          </button>
        ))}
      </div>
      <div className="section-label">Analytics assistant · runnable</div>
      <div className="template-list">
        {["aws", "azure", "gcp", "ibm"].map((p) => (
          <button key={p} onClick={() => onLoad(template(p))}>
            <Sparkles size={21} />
            <span>
              <strong>{PROVIDERS[p].name} · Predictive AI assistant</strong>
              <small>
                Data → model → AI → policy → response · local fixtures
              </small>
            </span>
            <Plus size={16} />
          </button>
        ))}
      </div>
      <div className="section-label">OPENARCHFLOW TEMPLATES · DESIGN ONLY</div>
      <div className="template-list">
        {UPSTREAM_TEMPLATES.map((t) => (
          <button key={t.id} onClick={() => onLoad(loadUpstreamTemplate(t.id))}>
            <Cloud size={19} />
            <span>
              <strong>{t.name}</strong>
              <small>{t.description}</small>
            </span>
            <Plus size={16} />
          </button>
        ))}
      </div>
    </>
  );
}
export function ImportDialog({ onLoad, onNotify }) {
  const [format, setFormat] = useState("mermaid"),
    [code, setCode] = useState(
      "flowchart LR\n  Data[Customer data]\n  Model[Prediction model]\n  Agent[AI assistant]\n  Data --> Model\n  Model --> Agent",
    );
  return (
    <>
      <div className="eyebrow">OPENARCHFLOW IMPORT ENGINE</div>
      <h2>Bring an existing design.</h2>
      <p>
        Parsers are integrated from the pinned upstream. Imported blocks are
        architecture references; they are not runnable cloud resources.
      </p>
      <label className="dialog-field">
        Format
        <select
          aria-label="Diagram import format"
          value={format}
          onChange={(e) => setFormat(e.target.value)}
        >
          <option value="mermaid">Mermaid flowchart</option>
          <option value="sql">SQL CREATE TABLE (basic syntax)</option>
        </select>
      </label>
      <textarea
        className="code-input"
        aria-label="Diagram source"
        value={code}
        onChange={(e) => setCode(e.target.value)}
      />
      <button
        className="button run-button full"
        onClick={() => {
          try {
            onLoad(importDiagram(code, format));
          } catch (error) {
            onNotify(error.message);
          }
        }}
      >
        <Upload size={15} />
        Import as architecture
      </button>
    </>
  );
}
export function PulumiDialog({
  snapshot,
  onSnapshot,
  onLoad,
  onExport,
  onNotify,
  environment,
}) {
  return (
    <>
      <div className="eyebrow">PULUMI · PREFERRED INFRASTRUCTURE PATH</div>
      <h2>Design ↔ managed resources.</h2>
      <p>
        Keep design intent and observed state separate, then review changes
        before adopting them.
      </p>
      <div className="pulumi-path">
        <span>Canvas</span>
        <GitBranch size={18} />
        <span>Pulumi program</span>
        <GitBranch size={18} />
        <span>Stack state</span>
      </div>
      <button className="button run-button full" onClick={onExport}>
        <Code2 size={15} />
        Export {environment} Pulumi scaffold
      </button>
      <p className="modal-fine">
        Scaffold only: metadata components and graph dependencies.
        Provider-specific cloud resource implementations are not generated yet.
      </p>
      <label className="snapshot-upload">
        <Upload size={20} />
        <strong>Import a Pulumi stack export</strong>
        <small>Metadata only · inputs, outputs and secrets discarded</small>
        <input
          type="file"
          accept=".json,application/json"
          aria-label="Import Pulumi snapshot"
          onChange={async (e) => {
            try {
              const file = e.target.files?.[0];
              if (!file) return;
              if (file.size > 10_000_000)
                throw Error("Snapshot must be smaller than 10 MB.");
              onSnapshot(importPulumiSnapshot(JSON.parse(await file.text())));
            } catch (error) {
              onNotify(error.message);
            }
            e.target.value = "";
          }}
        />
      </label>
      {snapshot && (
        <div className="snapshot-result">
          <strong>
            {snapshot.resources.length} resource references imported
          </strong>
          <p>{snapshot.notice}</p>
          <div className="snapshot-resources">
            {snapshot.resources.slice(0, 12).map((r) => (
              <div key={r.id}>
                <span>{PROVIDERS[r.provider].name}</span>
                <strong>{r.name}</strong>
                <small>{r.type}</small>
              </div>
            ))}
          </div>
          <button
            className="button subtle full"
            onClick={() => {
              try {
                onLoad(snapshotToProject(snapshot));
              } catch (error) {
                onNotify(error.message);
              }
            }}
          >
            Review these references on the canvas
          </button>
        </div>
      )}
      <div className="inspector-info">
        <ShieldCheck size={17} />
        <span>
          Pulumi import can generate code for existing resources. Refresh
          updates recorded state; it does not automatically rewrite source. This
          MVP imports snapshot metadata only. No Pulumi commands or cloud APIs
          are executed.
        </span>
      </div>
    </>
  );
}
export function FrontPanel({ project, run, onSelect }) {
  return (
    <section className="front-panel" aria-label="Front panel">
      {project.nodes.map((n, i) => {
        const step = run?.steps.find((s) => s.id === n.id);
        const o = step?.output;
        const value = o?.measures
          ? `${o.measures.filter((m) => m.pass).length}/${o.measures.length} ✓`
          : o?.work_order && n.data.kind === "tool"
            ? o.work_order.id
            : o?.drift && n.data.kind === "monitor"
              ? `PSI ${o.drift.psi}`
              : o?.prediction && n.data.kind === "predict"
                ? `${Math.round(o.prediction.failure_probability * 100)}%`
                : o?.training && n.data.kind === "train"
                  ? `P ${o.training.precision}`
                  : o?.coverage !== undefined && n.data.kind === "stream"
                    ? `${Math.round(o.coverage * 100)}%`
                    :
          step?.output?.churn_probability !== undefined
            ? `${Math.round(step.output.churn_probability * 100)}%`
            : step?.output?.assertions
              ? `${Object.values(step.output.assertions).filter(Boolean).length} ✓`
              : step?.status === "failed"
                ? "✕"
                : step
                  ? "✓"
                  : "—";
        return (
          <button
            key={n.id}
            onClick={() => onSelect(n.id)}
            className={`indicator ${step?.status || ""}`}
            title={step?.error || step?.status || "Not run"}
          >
            <span className="indicator-number">{i + 1}</span>
            <strong>{value}</strong>
            <span>{n.data.label}</span>
          </button>
        );
      })}
    </section>
  );
}
