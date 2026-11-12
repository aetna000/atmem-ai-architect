import {StarPrompt,STAR_URL} from './StarPrompt.jsx';
import {prefillAcceptedSettings} from './engineering-defaults.mjs';
import {LocationChoices} from './LocationChoices.jsx';
import {InlineNote} from './HelpNote.jsx';
import {ProjectChecks} from './ProjectChecks.jsx';
import {useEngineeringStatus} from './useEngineeringStatus.mjs';
import {ChatResizeHandle} from './ChatResizeHandle.jsx';
import {copyProject} from './project-copy.mjs';
import './journey-workspace.css';
import {synchronizeEngineeringIntent,applyArchitectureChange} from './architecture-work.mjs';
import {applyArtifactWork} from './artifact-work.mjs';
import {hasArchitectureDesign} from './design-build-flow.mjs';
import {ArchitectureTurn,EarlierArchitectureActivity} from './ArchitectureActivity.jsx';
import {recordArchitectureTurn,finishArchitectureTurn,architectureChatEntries} from './architecture-activity.mjs';
import {version as appVersion} from "../package.json";
import {restoreQueuedMessages,nextIntakeBatch,restoreIntakePaused} from './work-intake.mjs';
import {emulationGuidance,guidanceMessage} from './emulation-guidance.mjs';
import {readCanvasView,saveCanvasView,arrangeOverview} from './canvas-view.mjs';
import {BlockRequirements} from './BlockRequirements.jsx';
import {componentReviews,markComponentReviewed,applyComponentReview,editBlockRequirement,reviewIssueLabel} from './component-review.mjs';
import {ComponentReview,ReviewBadge} from './ComponentReview.jsx';
import {newQuestion} from './records.mjs';
import {useChatScroll} from './useChatScroll.jsx';
import {CONTAINER_SERVICES} from './container-contracts.mjs';
import {verifiedReceipt} from './validation-receipt.mjs';
import { conversationMessages, withConversation } from "./conversation.mjs";
import {ChatMessage} from "./ChatMessage.jsx";
import {readAttachments,ATTACHMENT_ACCEPT} from "./chat-attachments.mjs";
import {BrainActivity} from "./BrainActivity.jsx";
import {useEmulation} from './useEmulation.jsx';
import {EmulationPanel} from './EmulationPanel.jsx';
import {EngineeringPanel} from './EngineeringPanel.jsx';
import {emulationPrompt,guardEmulationCorrection,groundEmulationMessage,emulationCoachReady} from './emulation-feedback.mjs';
import {projectIdFromUrl} from './project-links.mjs';
import { diagramAttention } from "./diagram-attention.mjs";
import { VoiceDictation } from "./voice-conversation.mjs";
import {OpenAIVoicePanel} from './OpenAIVoicePanel.jsx';
import { OutputsView } from "./OutputsView.jsx";
import { outputBundle } from "./output-bundle.mjs";
import { TerraformView } from "./TerraformView.jsx";
import { journey, advanceJourney, acknowledgeStage, DESIGN_SECTIONS,journeySectionId,completedStages, designSection, journeyAction } from "./journey.mjs";
import "@xyflow/react/dist/style.css";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Handle,
  Position,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  useReactFlow,
} from "@xyflow/react";
import {
  AlertTriangle,
  ArrowUp,
  Paperclip,
  StickyNote,
  Scan,
  ArrowDownToLine,
  Check,
  ChevronRight,
  GitBranch,
  Maximize2,
  ChevronsLeftRight,
  ChevronsRightLeft,
  MoreHorizontal,
  PanelRightClose,
  PanelRightOpen,
  Play,
  Plus,
  Search,
  Trash2,
  Undo2,
  Redo2,
  RotateCcw,
  X,
  Database,
  Activity,
  Sparkles,
  ShieldCheck,
  CheckCheck,
  Code2,
  Cloud,
  LayoutTemplate,
  ZoomIn,
  ZoomOut,
  Radio,
  History,
  Workflow,
  FlaskConical,
  Package,
  Gauge,
  UserCheck,
  AppWindow,
  PencilRuler,
  ScanSearch,
  Calculator,
  Rocket,
  BrainCircuit,
  Waypoints,
  Mic,
  Square,
  Eraser,
  LayoutGrid,
  ArrowLeft,
  ArrowRightToLine,
  ArrowRightFromLine,
  FolderOpen,
  Moon,
  Sun,
} from "lucide-react";
import { roleOf } from "./review.mjs";
import {
  CATALOG,
  PROVIDERS,
  pdmTemplate,
  checkProject,
  orderProject,
  executeBlock,
  validateImport,
  propose,
  makePlan,
} from "./core.mjs";
import { layerOf, proposalDiff, systemView } from "./levels.mjs";
import { consult, keepEngagement, newDecision, recommendationDecision } from "./engagement.mjs";
import { adrMarkdown, OPTION_NAMES } from "./pack.mjs";
import { deploymentDocument } from "./document.mjs";
import { withDerived } from "./derive.mjs";
import { MemoryPanel, ContextUsed } from "./MemoryPanel.jsx";
import { defaultAssessment } from "./engagement.mjs";
import { setUsage } from "./estimate.mjs";
import { applyPriceQuotes, fetchPlanningPrices, storageNodes, lambdaNodes, googleNodes } from "./pricing.mjs";
import { applyDecisionUpdates, applyRequirementDrafts, proposeCommentRevisions } from "./consultation.mjs";
import { terraformSketch } from "./terraform.mjs";
import { WORKFLOWS, conceptSignature, essentialsKnown, nextQuestion, opening, progress, sketch, understand } from "./discovery.mjs";
import { review } from "./review.mjs";
import { setProjectSize, estimate } from "./estimate.mjs";
import { DeployView, EstimateView, ProjectsDialog, ReviewView, TestCard } from "./JourneyViews.jsx";
import { newRequirement } from "./records.mjs";
import { DiscoverView, OptionsView, DecisionsView, MeasuresEditor, RequirementsView } from "./EngagementViews.jsx";
import { fromProjectFile, parseProjectFile, toProjectFile, MAX_FILE_BYTES } from "./project-file.mjs";
import { linkedTo, slugSubject } from "./records.mjs";
import "./atmem-tokens.css";
import "./brand.css";
import "./atflow.css";
import {
  UPSTREAM_CATALOG,
  autoLayout,
  importUpstreamProject,
  prettyPayload,
} from "./integrations.ts";
import {
  Connections,
  TemplateDialog,
  ImportDialog,
  PulumiDialog,
  FrontPanel,
} from "./WorkbenchDialogs.jsx";
import { discoverLocalAgent, projects as projectStore, requestArchitect } from "./local-agent.mjs";
import { EFFORT_LABEL } from "./WorkbenchDialogs.jsx";
import { pulumiScaffold } from "./pulumi.mjs";
import { zipSync, strToU8 } from "fflate";

// Each browser starts fresh; earlier projects are opened deliberately (⋯ → Open project file).
const STORAGE = "atforma-workspace-v3";
// A new project starts empty: the user describes what they want first.
const emptyProject = () => ({ id: crypto.randomUUID(), version: 1, revision: 1, name: "New project", provider: "tools", requirements: "", nodes: [], edges: [] });
const ALL_CATALOG = [...CATALOG, ...UPSTREAM_CATALOG];
const KIND_ICON = {
  source: Database,
  predict: Activity,
  agent: Sparkles,
  guard: ShieldCheck,
  output: CheckCheck,
  tool: Code2,
  resource: Cloud,
  stream: Radio,
  history: History,
  features: Workflow,
  train: FlaskConical,
  registry: Package,
  monitor: Gauge,
};
// Scenario, label, block kind it needs.
// Role → AWS-architecture-style colour and icon, so the board reads like infrastructure.
const ROLE_STYLE = {
  data: ["#7aa116", Database],
  ingest: ["#8c4fff", Waypoints],
  index: ["#c925d1", ScanSearch],
  llm: ["#01a88d", BrainCircuit],
  model: ["#01a88d", Activity],
  monitor: ["#e7157b", Gauge],
  guard: ["#dd344c", ShieldCheck],
  human: ["#5f6b7a", UserCheck],
  app: ["#1f777c", AppWindow],
  output: ["#1f777c", CheckCheck],
};
const LAYER_COLOR = { data: "#7aa116", ml: "#01a88d", intelligence: "#01a88d", integration: "#e7157b", governance: "#dd344c", delivery: "#1f777c" };
const MODE_ICON = { design: PencilRuler, review: ShieldCheck, estimate: Calculator, deploy: Rocket };
const SCENARIOS = [
  ["happy", "Normal day", null],
  ["sensor-dropout", "Sensor dropout", "stream"],
  ["weak-model", "Weak model", "train"],
  ["drift", "Drift", "monitor"],
  ["ungrounded", "Ungrounded insight", "agent"],
  ["missing", "Missing input field", "source"],
  ["denied", "Access denied", "guard"],
  ["tool-error", "App unavailable", "tool"],
];
// Discovery is woven into Design: you talk, the architect draws.
const MODES = [
  ["design", "Design"],
  ["review", "Review"],
  ["estimate", "Estimate"],
  ["deploy", "Delivery draft"],
];
const PROMPTS = {
  design: ["Compare all four clouds"],
  review: ["Review risks", "How do I test this?"],
  estimate: ["What drives cost?"],
  deploy: ["What evidence do we need to scale?"],
};
const STATUS_GLYPH = {
  passed: <Check size={13} />,
  failed: <X size={13} />,
  running: <BrainActivity size={24} />,
};

// Terraform mark from Simple Icons (CC0), https://simpleicons.org/?q=terraform.
function TerraformIcon(){return <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M1.44 0v7.575l6.561 3.79V3.787zm21.12 4.227l-6.561 3.791v7.574l6.56-3.787zM8.72 4.23v7.575l6.561 3.787V8.018zm0 8.405v7.575L15.28 24v-7.578z"/></svg>;}

// The AtMem.ai mark, same artwork as atmem.ai/brand/icon-on-light.svg.
// Ink follows currentColor; the dot follows the theme (see .atmem-dot).
function Mark({ size = 20 }) {
  return (
    <svg className="atmem-mark" width={size} height={size} viewBox="-154.35 -151.35 308.7 308.7" aria-hidden="true">
      <g transform="translate(0 2)">
        <path d="M-91.7 74.24 L0 -88 L91.7 74.24 M-66.7 30 H66.7" fill="none" stroke="currentColor" strokeWidth="26" strokeLinejoin="round" />
        <path
          d="M-142 96a38 38 0 1 0 76 0a38 38 0 1 0 -76 0ZM-116 96a12 12 0 1 0 24 0a12 12 0 1 0 -24 0ZM66 96a38 38 0 1 0 76 0a38 38 0 1 0 -76 0ZM92 96a12 12 0 1 0 24 0a12 12 0 1 0 -24 0Z"
          fill="currentColor"
          fillRule="evenodd"
        />
        <circle className="atmem-dot" cx="0" cy="-88" r="40" />
      </g>
    </svg>
  );
}

// Which architect the user chose; absent on first visit, so we ask before anything else.
const CONNECTION = "atforma-connection-v1";
function readConnection() {
  try {
    const c = JSON.parse(localStorage.getItem(CONNECTION) || "null");
    // Older builds stored "offline"; the architect now always needs a real model.
    return c && typeof c.provider === "string" && c.provider !== "offline"
      ? { provider: c.provider, model: String(c.model || ""), ...(c.effort ? { effort: String(c.effort) } : {}) }
      : null;
  } catch {
    return null;
  }
}
function saveConnection(c) {
  try {
    localStorage.setItem(CONNECTION, JSON.stringify({ provider: c.provider, model: c.model, effort: c.effort }));
  } catch {}
}
function readSaved() {
  try {
    const raw = localStorage.getItem(STORAGE);
    const p = validateImport(raw ? JSON.parse(raw) : emptyProject());
    return withDerived(p.id ? p : { ...p, id: crypto.randomUUID() });
  } catch {
    return validateImport(emptyProject());
  }
}

function handlePosition(side, fallback) {
  return Position[side?.[0]?.toUpperCase() + side?.slice(1)] || fallback;
}

function BlockNode({ data, selected }) {
  const p = PROVIDERS[data.provider] || PROVIDERS.tools;
  const [color, RoleIcon] = ROLE_STYLE[roleOf({ data })] || ["#5f6b7a", KIND_ICON[data.kind] || Cloud];
  return (
    <div
      className={`blk kind-${data.kind} ${data.origin === "existing" ? "existing" : ""} ${selected ? "selected" : ""} ${data.dim ? "dim" : ""} state-${data.runState || "idle"}`}
      style={{ "--provider": p.color, "--role": color }}
    >
      {data.kind !== "source" && (
        <Handle type="target" position={handlePosition(data.inputPosition, Position.Left)} />
      )}
      <span className="blk-icon">
        <RoleIcon size={18} />
      </span>
      <span className="blk-text">
        <strong>{data.label}</strong>
        {data.service&&<small className="blk-service">{data.service}</small>}
        {(data.origin === "existing" || data.provider !== "tools") && (
          <small>
            <i className="pdot" />
            {data.origin === "existing" ? "your system" : p.name}
          </small>
        )}
        {data.blockReview&&<ReviewBadge item={data.blockReview} onClick={data.onReview}/>}
      </span>
      <span className="blk-state">{STATUS_GLYPH[data.runState]}</span>
      {data.kind !== "output" && (
        <Handle type="source" position={handlePosition(data.outputPosition, Position.Right)} />
      )}
    </div>
  );
}

function LayerNode({ data, selected }) {
  return (
    <div className={`layer ${selected ? "selected" : ""} state-${data.status}`} style={{ "--role": LAYER_COLOR[data.layer] || "#5f6b7a" }}>
      <Handle type="target" position={Position.Left} isConnectable={false} />
      <div className="layer-head">
        <strong>{data.label}</strong>
        <span className="blk-state">{STATUS_GLYPH[data.status]}</span>
      </div>
      <small>
        {data.blocks.length} block{data.blocks.length === 1 ? "" : "s"}
        {data.status !== "idle" && ` · ${data.done}/${data.blocks.length} passed`}
      </small>
      {data.reviewSummary&&<button className="topology-review-summary nodrag" onClick={e=>{e.stopPropagation();data.onReview?.();}} aria-label={`Open block review for ${data.label}`}>{data.reviewSummary.issues.length?reviewIssueLabel(data.reviewSummary.issues):`${data.reviewSummary.reviewed}/${data.blocks.length} designs reviewed`}</button>}
      <button className="topology-drill-hint nodrag" onClick={e=>{e.stopPropagation();data.onExplore?.();}}>Explore components <ChevronRight size={12}/></button>
      <span className="layer-providers">
        {data.providers.map((id) => (
          <span key={id} title={PROVIDERS[id].name} style={{ background: PROVIDERS[id].color }} />
        ))}
      </span>
      <Handle type="source" position={Position.Right} isConnectable={false} />
    </div>
  );
}

// A comment: a sticky note on the board. Never part of the system; arrows may point from it.
function NoteNode({ id, data, selected }) {
  const [text, setText] = useState(data.label);
  const box = useRef(null);
  useEffect(() => { if (document.activeElement !== box.current) setText(data.label); }, [data.label]);
  // A comment you just added is ready to type into.
  useEffect(() => {
    if (data.fresh) setTimeout(() => box.current?.focus(), 30);
  }, [data.fresh]);
  return (
    <div className={`note sticky-note ${selected ? "selected" : ""}`}>
      <Handle type="target" position={Position.Left} />
      <textarea
        ref={box}
        className="nodrag"
        aria-label="Comment"
        placeholder="Write a comment…"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onBlur={() => text !== data.label && data.onText?.(id, text)}
      />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
const nodeTypes = { resource: BlockNode, layer: LayerNode, note: NoteNode };

function Palette({ onAdd, onClose, disabled }) {
  const [query, setQuery] = useState(""),
    [provider, setProvider] = useState("all"),
    [scope, setScope] = useState("ai");
  const items = ALL_CATALOG.filter(
    (c) =>
      (scope === "all" ||
        (scope === "ai" &&
          (c.kind !== "resource" ||
            /AI|Machine Learning|Analytics/i.test(c.category || ""))) ||
        (scope === "run" && c.kind !== "resource")) &&
      (provider === "all" || c.provider === provider) &&
      `${c.label} ${c.description} ${PROVIDERS[c.provider].name}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  return (
    <div className="palette" role="dialog" aria-label="Add block">
      <div className="palette-search">
        <Search size={14} />
        <input
          autoFocus
          aria-label="Search blocks"
          placeholder="Search blocks"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") onClose();
            if (e.key === "Enter" && items[0]) onAdd(items[0]);
          }}
        />
        <select aria-label="Block scope" value={scope} onChange={(e) => setScope(e.target.value)}>
          <option value="ai">AI</option>
          <option value="run">Runnable</option>
          <option value="all">All</option>
        </select>
        <button type="button" className="icon" aria-label="Close component picker" title="Close component picker" onClick={onClose}><X size={16}/></button>
      </div>
      <div className="chips">
        {["all", ...Object.keys(PROVIDERS)].map((id) => (
          <button
            key={id}
            className={provider === id ? "on" : ""}
            onClick={() => setProvider(id)}
          >
            {id === "all" ? "All" : id === "tools" ? "Tools" : id === "gcp" ? "Google" : PROVIDERS[id].name}
          </button>
        ))}
      </div>
      <div className="palette-list">
        {items.map((item) => (
          <button
            key={item.id}
            className="palette-item"
            draggable={!disabled}
            disabled={disabled}
            onDragStart={(e) => e.dataTransfer.setData("application/atforma-block", item.id)}
            onClick={() => onAdd(item)}
          >
            {React.createElement(KIND_ICON[item.kind] || Cloud, { size: 15 })}
            <span>{item.label}</span>
            <span className="dot" title={PROVIDERS[item.provider].name} style={{ background: PROVIDERS[item.provider].color }} />
          </button>
        ))}
        {!items.length && <p className="muted pad">No blocks match.</p>}
      </div>
    </div>
  );
}

function Linked({ project, id, hideNeeds = false }) {
  const { needs, assumptions, questions } = linkedTo(project, id);
  if (!needs.length && !assumptions.length && !questions.length) return null;
  return (
    <div className="linked">
      {!hideNeeds&&needs.map((r) => (
        <p key={r.id}>
          <strong>Requirement</strong> {r.statement}
          {r.measure && <span className="mono"> · {r.measure.metric} {r.measure.op} {String(r.measure.target)}{r.measure.unit}</span>}
        </p>
      ))}
      {assumptions.map((a) => (
        <p key={a.id}>
          <strong>Assumption</strong> {a.statement} <span className="muted">· {a.madeAt}</span>
        </p>
      ))}
      {questions.map((q) => (
        <p key={q.id}>
          <strong>{q.status==='answered'?'Answered question':'Open question'}</strong> {q.question}{q.status==='answered'&&q.answer&&<span className="recorded-answer">Answer: {q.answer}</span>}
        </p>
      ))}
    </div>
  );
}

function BlockDetail({ project, node, run, probe, busy, reviewItems, onReviewConfirm, onReviewDiscuss, onReviewQuestion, onReviewResolve, onRequirementSave, onWorkModelChange, onChange, onRemove, onOpen, onBack,onSpec }) {
  const trace = run?.steps.find((s) => s.id === node.id);
  const inputs = project.edges.filter((e) => e.target === node.id);
  const outputs = project.edges.filter((e) => e.source === node.id);
  const nameOf = (id) => project.nodes.find((n) => n.id === id)?.data.label;
  const set = (patch) => onChange({ ...node, data: { ...node.data, ...patch } });
  const setConfig = (patch) => set({ config: { ...node.data.config, ...patch } });
  const p = PROVIDERS[node.data.provider];
  return (
    <section className="detail" aria-label="Block detail">
      <div className="detail-navigation">
        <button className="back" onClick={onBack} aria-label="Back to the board">
          <ArrowLeft size={15} /><kbd>Esc</kbd>
        </button>
      </div>
      <div className="detail-col">
        <h3 aria-label="Inputs" title="Inputs"><ArrowRightToLine size={20}/></h3>
        {inputs.length ? (
          inputs.map((e) => (
            <button key={e.id} className="terminal" onClick={() => onOpen(e.source)}>
              <span>{nameOf(e.source)}</span>
              <small>{e.label || "data"}</small>
            </button>
          ))
        ) : (
          <p className="muted">None — this block starts the flow.</p>
        )}
        {trace && (
          <>
            <h4>Received</h4>
            <pre>{prettyPayload(trace.input)}</pre>
          </>
        )}
      </div>
      <div className="detail-core" style={{ "--provider": p.color }}>
        <div className="detail-title">
          <span className="blk-provider" />
          <input
            aria-label="Block name"
            disabled={busy}
            value={node.data.label}
            onChange={(e) => set({ label: e.target.value })}
          />
        </div>
        <button className="link" onClick={onSpec}>Specification ↗</button>
        <BlockRequirements project={project} nodeId={node.id} busy={busy} onSave={onRequirementSave}/>
        <ComponentReview key={node.id} item={reviewItems.find(r=>r.id===node.id)} items={reviewItems} busy={busy} onOpen={onOpen} onConfirm={onReviewConfirm} onDiscuss={onReviewDiscuss} onQuestion={onReviewQuestion} onResolve={onReviewResolve} onDetailAnswer={patch=>onChange({...node,data:{...node.data,...patch,...(patch.config?{config:{...node.data.config,...patch.config}}:{})}})}/>
        <details className="component-settings"><summary>Component settings</summary><div className="fields">
          <label>
            Provider
            <select disabled={busy} value={node.data.provider} onChange={(e) => set({ provider: e.target.value })}>
              {Object.entries(PROVIDERS).map(([id, v]) => (
                <option key={id} value={id}>{v.name}</option>
              ))}
            </select>
          </label>
          <label>
            Behaviour
            <select
              aria-label="Execution behaviour"
              disabled={busy}
              value={node.data.kind}
              onChange={(e) => set({ kind: e.target.value })}
            >
              <option value="resource">Architecture component</option>
              <option value="source">Source fixture</option>
              <option value="predict">Model fixture</option>
              <option value="agent">Agent fixture</option>
              <option value="guard">Policy fixture</option>
              <option value="output">Assertions</option>
              <option value="tool">Tool / app fixture</option>
              <option value="stream">Sensor stream</option>
              <option value="history">Maintenance history</option>
              <option value="features">Feature pipeline</option>
              <option value="train">Training pipeline</option>
              <option value="registry">Model registry</option>
              <option value="monitor">Model monitor</option>
            </select>
          </label>
          <label>
            Region
            <input
              disabled={busy}
              value={node.data.config?.region || ""}
              onChange={(e) => setConfig({ region: e.target.value })}
            />
          </label>
          <label>
            Data class
            <select
              disabled={busy}
              value={node.data.config?.classification || "Internal"}
              onChange={(e) => setConfig({ classification: e.target.value })}
            >
              <option>Public</option>
              <option>Internal</option>
              <option>Confidential</option>
            </select>
          </label>
          <label>
            Status
            <select aria-label="Block status" disabled={busy} value={node.data.origin === "existing" ? "existing" : "proposed"} onChange={(e) => set({ origin: e.target.value })}>
              <option value="proposed">Proposed</option>
              <option value="existing">Client's existing system</option>
            </select>
          </label>
          {node.data.origin === "existing" && <label className="field-wide">
            Existing system handling
            <select aria-label="Existing system handling" disabled={busy} value={node.data.deploymentMode === "create" ? "create" : node.data.binding === "existing-service" ? "reference" : "contract"} onChange={e => set(e.target.value === "create" ? {deploymentMode:"create",implementation:"container-service",binding:undefined} : {deploymentMode:undefined,binding:e.target.value === "reference" ? "existing-service" : undefined,...(node.data.deploymentMode === "create" ? {implementation:undefined}:{})})}>
              <option value="contract">Typed integration contract</option>
              <option value="reference">Reference only — preserve existing service</option>
              {CONTAINER_SERVICES[node.data.provider]?.service === node.data.service && <option value="create">Existing application — create a new private deployment</option>}
            </select>
            <small>{node.data.deploymentMode === "create" ? "Creates a new private container deployment from your supplied image. Application behavior and connections require tests." : "Preserves an existing deployment without creating or importing it. Its connections require tests."}</small>
          </label>}
          <label className="check">
            <input type="checkbox" aria-label="In prototype scope" disabled={busy} checked={!!node.data.poc} onChange={(e) => set({ poc: e.target.checked })} />
            In prototype scope
          </label>
        </div></details>
        <Linked project={project} id={node.id} hideNeeds/>
        {node.data.kind === "output" && (
          <MeasuresEditor measures={node.data.measures} disabled={busy} onChange={(measures) => set({ measures })} />
        )}
        {trace ? (
          <div className={`trace ${trace.status}`}>
            {STATUS_GLYPH[trace.status]} {trace.status[0].toUpperCase() + trace.status.slice(1)} · {trace.duration} ms
            {trace.error && <p className="error-box">{trace.error}</p>}
          </div>
        ) : (
          <p className="muted">Not run yet. Run a test to see payloads.</p>
        )}
        <button className="btn ghost danger" disabled={busy} onClick={onRemove}>
          <Trash2 size={13} /> Remove block
        </button>
      </div>
      <div className={`detail-col ${probe ? "probed" : ""}`}>
        <h3 aria-label="Outputs" title="Outputs"><ArrowRightFromLine size={20}/></h3>
        {outputs.length ? (
          outputs.map((e) => (
            <button key={e.id} className="terminal" onClick={() => onOpen(e.target)}>
              <span>{nameOf(e.target)}</span>
              <small>{e.label || "data"}</small>
            </button>
          ))
        ) : (
          <p className="muted">None — this block ends the flow.</p>
        )}
        {trace && (
          <>
            <h4>Produced{probe ? ` · probe on “${probe.label || "data"}”` : ""}</h4>
            <pre>{prettyPayload(trace.output)}</pre>
          </>
        )}
      </div>
    </section>
  );
}

const brief = (p) => !!p.brief?.application?.trim();
// The concept to draw right away: a first sketch once the idea is recognised, and a redraw
// on the stated cloud while the design is still a sketch. Anything richer is the model's job.
function conceptFor(was, now) {
  if (!now.workflow) return null;
  const proposal = sketch(now);
  if (!now.nodes.length) return proposal;
  // Keep refining only the concept we drew ourselves; once the user edits the board, it's theirs.
  const untouched = now.conceptSig && conceptSignature(now) === now.conceptSig;
  return untouched && conceptSignature(proposal.next) !== now.conceptSig ? proposal : null;
}
// Small, factual signals of what the harness did with a message.
function harnessSignals(was, now) {
  const grew = (k) => (now[k]?.length || 0) - (was[k]?.length || 0);
  const out = [];
  if (now.workflow && now.workflow !== was.workflow) out.push(`skill: ${WORKFLOWS.find((w) => w.id === now.workflow)?.name}`);
  const topics = Object.keys(now.brief || {}).filter((k) => now.brief[k]?.trim() && !was.brief?.[k]?.trim());
  if (topics.length) out.push(`noted ${topics.join(", ")}`);
  if (grew("facts") > 0) out.push(`+${grew("facts")} fact${grew("facts") > 1 ? "s" : ""}`);
  if (grew("needs") > 0) out.push(`+${grew("needs")} requirement${grew("needs") > 1 ? "s" : ""}`);
  if (grew("assumptions") > 0) out.push("assumption logged");
  if (grew("openQuestions") > 0) out.push("open question");
  return out;
}
const welcome = (project) => ({
  role: "assistant",
  text: project.nodes.length || project.brief?.application?.trim()
    ? `Good to see you again — let's keep going.\n\n${opening(project)}`
    : `What would you like to build?`,
});

const THEME = "atmem-architect-theme";
// Light is the default; dark only when the user chose it.
function savedTheme() {
  try {
    return localStorage.getItem(THEME) === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}
document.documentElement.dataset.theme = savedTheme();

function readChatView(id){try{const value=JSON.parse(localStorage.getItem('atmem-chat-view:'+id)||'null');return value&&Number.isSafeInteger(value.start)&&value.start>=0&&Array.isArray(value.turnIds)?value:{start:0,turnIds:[]};}catch{return {start:0,turnIds:[]};}}
const pricingSignature=p=>JSON.stringify([p.id,p.estimate?.projectSize||'small',p.estimate?.usage,p.facts,p.decisions?.filter(d=>d.status==='Accepted'&&['cloud.region','data.country'].includes(d.subject)),[...storageNodes(p),...lambdaNodes(p),...googleNodes(p)].map(n=>[n.id,n.data.provider,n.data.service,n.data.config])]);
function App() {
  const [starOffer,setStarOffer]=useState(0);
  const [project, setProject] = useState(readSaved);
  const projectRef = useRef(project);
  projectRef.current = project;
  const [initialCanvasView] = useState(()=>readCanvasView(project));
  const [topologyPositions,setTopologyPositions] = useState(initialCanvasView.positions);
  const [mode, setMode] = useState("design"),
    [peek, setPeek] = useState(null),
    [picked, setPicked] = useState(() => new Set()),
    [saved, setSaved] = useState({ projects: [], bin: [], folder: "" }),
    [ctx, setCtx] = useState(null),
    [drawLive, setDrawLive] = useState(() => {
      try {
        return localStorage.getItem("atforma-draw-live") !== "off";
      } catch {
        return true;
      }
    }),
    [designView, setDesignView] = useState("board"),
    [level, setLevel] = useState(initialCanvasView.level),
    [focus, setFocus] = useState(initialCanvasView.focus),
    [selected, setSelected] = useState(initialCanvasView.selected),
    [messages, setMessagesState] = useState(() => conversationMessages(projectRef.current, [welcome(projectRef.current)])),
    [reviewView, setReviewView] = useState("findings"),
    [input, setInput] = useState(()=>{try{return localStorage.getItem('atmem-chat-draft:'+projectRef.current.id)||'';}catch{return '';}}),
    [pending, setPending] = useState(null),
    [busy, setBusy] = useState(false),
    [scenario, setScenario] = useState("happy"),
    [run, setRun] = useState(null),
    [runStates, setRunStates] = useState({}),
    [history, setHistory] = useState([]),
    [future, setFuture] = useState([]),
    [toast, setToast] = useState(""),
    [modal, setModal] = useState(() => (readConnection() ? null : "welcome")),
    [menu, setMenu] = useState(false),
    [palette, setPalette] = useState(false),
    [issuesOpen, setIssuesOpen] = useState(false),
    [chatOpen, setChatOpen] = useState(true),
    [theme, setTheme] = useState(savedTheme),
    [environment, setEnvironment] = useState("staging"),
    [storageError, setStorageError] = useState(false),
    [view, setView] = useState("diagram"),
    [probe, setProbe] = useState(null),
    [snapshot, setSnapshot] = useState(null),
    [measured, setMeasured] = useState({});
  const setMessages=useCallback(updater=>setMessagesState(previous=>{
    const next=typeof updater==='function'?updater(previous):updater;
    if(typeof updater!=='function')return next;
    return next.map((m,i)=>m.createdAt||previous.includes(m)||(i<previous.length&&previous[i]?.role===m.role&&previous[i]?.text===m.text)?m:{...m,createdAt:new Date().toISOString()});
  }),[]);
  const draftOwner=useRef(project.id);
  useEffect(()=>{
    if(draftOwner.current!==project.id){draftOwner.current=project.id;try{setInput(localStorage.getItem('atmem-chat-draft:'+project.id)||'');}catch{setInput('');}return;}
    try{localStorage.setItem('atmem-chat-draft:'+project.id,input);}catch{}
  },[project.id,input]);
  const [chatView,setChatView]=useState(()=>readChatView(project.id));
  useEffect(()=>setChatView(readChatView(project.id)),[project.id]);
  function changeChatView(value){setChatView(value);try{localStorage.setItem('atmem-chat-view:'+project.id,JSON.stringify(value));}catch{}}
  const messagesRef=useRef(messages);messagesRef.current=messages;
  const [session, setSession] = useState(null),
    [connection, setConnection] = useState(readConnection),
    [agentBusy, setAgentBusy] = useState(false);
  const [workspaceView,setWorkspaceView]=useState('canvas'),[buildRequest,setBuildRequest]=useState(null);
  const [memorySync,setMemorySync]=useState(null);
  const currentMemory=memorySync?.projectId===project.id?memorySync:null;
  const memoryLabel=!session?'AtMem memory':currentMemory?.enabled===false?'AtMem off':currentMemory?.status==='unavailable'?'AtMem unavailable':currentMemory?.pending>0||currentMemory?.status==='sync_failed'?'AtMem sync pending':currentMemory?.status==='ready'?'AtMem on':'AtMem memory';
  const buildView=false;
  const hasDesign=hasArchitectureDesign(project);
  function chooseWorkspace(value){if(value==='build'){setMode('review');setDesignView('board');setReviewView('findings');}setWorkspaceView('canvas');}
  function buildCurrentDesign(intent){
    if(!hasArchitectureDesign(projectRef.current)||busy||agentBusy||pending)return;
    setBuildRequest({id:crypto.randomUUID(),projectId:projectRef.current.id,...(intent==='test'?{intent:'test'}:{})});chooseWorkspace('build');
  }

  useEffect(()=>{saveCanvasView(project,{level,focus,selected,positions:topologyPositions});},[project.id,level,focus,selected,topologyPositions]);
  const emulation=useEmulation(project,environment,session);
  const emulationWorking=emulation.running||(agentBusy&&!!emulation.result);
  const [pricingState,setPricingState]=useState({busy:false,errors:[]});
  const [generationPending,setGenerationPending]=useState(false);
  const [checking,setChecking]=useState(false),[checkReceipt,setCheckReceipt]=useState(null);
  const engineeringStatus=useEngineeringStatus(session,project.id);
  const [architectAction,setArchitectAction]=useState('Architect is working…');
  const pricingRequest=useRef(0);
  const pricingAttempt=useRef(new Set());
  const pricingKey=pricingSignature(project);
  async function refreshEstimate(selected){
    if(!session?.token)return;
    const resolved=prefillAcceptedSettings(selected);
    const requested=resolved.estimate?.projectSize?resolved:setProjectSize(resolved,'small');
    if(requested!==selected)updateEngagement(requested);
    const request=++pricingRequest.current;pricingAttempt.current.add(pricingSignature(requested));
    const baseline=JSON.stringify([requested.estimate?.prices,requested.estimate?.details]);
    const identity=JSON.stringify([requested.id,requested.estimate?.projectSize,requested.estimate?.usage,requested.facts,requested.nodes]);
    setPricingState({busy:true,errors:[]});
    try{
      const result=await fetchPlanningPrices(session,requested),live=projectRef.current;
      if(request!==pricingRequest.current)return;
      if(JSON.stringify([live.id,live.estimate?.projectSize,live.estimate?.usage,live.facts,live.nodes])!==identity||JSON.stringify([live.estimate?.prices,live.estimate?.details])!==baseline){setPricingState({busy:false,errors:[]});return;}
      // Merge only the fetched pricing fields; preserve concurrent design and conversation edits.
      updateEngagement({...live,estimate:{...live.estimate,prices:result.project.estimate?.prices,details:result.project.estimate?.details}});
      setPricingState({busy:false,errors:result.errors});
    }catch(error){if(request===pricingRequest.current)setPricingState({busy:false,errors:[{reason:error.message}]});}
  }
  useEffect(()=>{
    if(!session?.token||!project.nodes.length)return;
    if(pricingAttempt.current.has(pricingKey))return;
    pricingAttempt.current.add(pricingKey);void refreshEstimate(project);
  },[mode,session?.token,pricingKey]);
  const [chatWidth,setChatWidth]=useState(()=>{try{const n=Number(localStorage.getItem('atmem-architect-chat-width'));return Number.isFinite(n)&&n>=320&&n<=900?n:360;}catch{return 360;}});
  function resizeChat(width){setChatWidth(width);try{localStorage.setItem('atmem-architect-chat-width',String(width));}catch{}}
  const [dismissedStarts,setDismissedStarts]=useState(()=>{try{const ids=JSON.parse(localStorage.getItem('atforma-dismissed-starts-v1')||'[]');return Array.isArray(ids)?ids.filter(id=>typeof id==='string').slice(-64):[];}catch{return [];}});
  function dismissStart(){setDismissedStarts(ids=>{const next=[...ids.filter(id=>id!==project.id),project.id].slice(-64);try{localStorage.setItem('atforma-dismissed-starts-v1',JSON.stringify(next));}catch{}return next;});}
  const [emulationOpen,setEmulationOpen]=useState(false),[treeOpen,setTreeOpen]=useState(false);
  useEffect(()=>{if(!treeOpen)return;const close=e=>{if(e.type==="keydown"?e.key==="Escape":!e.target.closest(".component-navigator,.palette"))setTreeOpen(false);};document.addEventListener("pointerdown",close);document.addEventListener("keydown",close);return()=>{document.removeEventListener("pointerdown",close);document.removeEventListener("keydown",close);};},[treeOpen]);
  const consultationAttempts = useRef(new Set());
  const agentAbort = useRef(null);
  const messageInput = useRef(null);
  const intakeRef=useRef(restoreQueuedMessages(messages,project.id));
  const [intake,setIntake]=useState(intakeRef.current),[intakePaused,setIntakePausedState]=useState(()=>restoreIntakePaused(messages)||intakeRef.current.length>0);
  const [intakeIssue,setIntakeIssue]=useState(null);
  const intakePausedRef=useRef(intakePaused);
  function setIntakePaused(value){intakePausedRef.current=value;setIntakePausedState(value);}
  const carryIntent=useRef(null);
  function updateIntake(next){intakeRef.current=next;setIntake(next);}
  function setRequestState(ids,state){setMessages(list=>list.map(m=>ids.includes(m.requestId)?{...m,workState:state}:m));}
  useEffect(()=>{
    setIntakePaused(restoreIntakePaused(messages)||restoreQueuedMessages(messages,project.id).length>0);
    setIntakeIssue(null);
    const restored=restoreQueuedMessages(messages,project.id).filter(q=>!intakeRef.current.some(old=>old.id===q.id));
    if(restored.length)updateIntake([...intakeRef.current,...restored]);
  },[project.id]);
  useEffect(()=>{
    if(buildView||agentBusy||agentAbort.current||busy||pending||intakePausedRef.current||!session||!connection)return;
    const batch=nextIntakeBatch(intakeRef.current,project.id);
    setIntakeIssue(batch?.blocked?batch.reason:null);if(!batch||batch.blocked)return;
    updateIntake(intakeRef.current.filter(q=>!batch.ids.includes(q.id)));
    setRequestState(batch.ids,'processing');
    const history=carryIntent.current?.projectId===project.id?[{role:'user',text:carryIntent.current.text},...messages.slice(-10)]:messages;
    void send(batch.message,'chat',null,null,{alreadyLogged:true,requestIds:batch.ids,attachments:batch.attachments,history});
  },[buildView,agentBusy,busy,pending,intakePaused,intake,session,connection,project.id]);
  const voice = useRef(null),openaiVoice=useRef(null);
  const [voiceState, setVoiceState] = useState("off");
  const [voiceError, setVoiceError] = useState("");
  const voiceActive = !["off", "error"].includes(voiceState);
  useEffect(() => () => voice.current?.cancel(), []);
  function startVoice() {
    if(openaiVoice.current?.stop({preservePending:true})?.retained)return notify("I kept the recognized words in your draft. Review them before starting local dictation.");
    if (busy) return notify("Wait for the current test to finish before recording.");
    if (!session) return notify("Connect the local helper before starting dictation.");
    let consent = false;
    try { consent = localStorage.getItem("atmem-local-dictation") === "yes"; } catch {}
    if (!consent) {
      consent = window.confirm("Use your microphone for local dictation? Audio is processed on this computer by the local helper and is not saved. Words appear in the message box; only pressing Send posts them to your selected architect.");
      if (!consent) return;
      try { localStorage.setItem("atmem-local-dictation", "yes"); } catch {}
    }
    setVoiceError("");voice.current?.cancel();
    let activeSession = session;
    fetch('/api/voice/prepare',{method:'POST',headers:{Authorization:`Bearer ${session.token}`}}).catch(()=>{});
    voice.current = new VoiceDictation({
      base: input, onState: setVoiceState, onError: setVoiceError, onDraft: setInput,
      transcribe: async (audio, signal) => {
        const request = () => fetch("/api/voice/transcribe", {
          method: "POST", headers: { "Content-Type": "audio/wav", Authorization: `Bearer ${activeSession.token}` },
          body: audio, signal,
        });
        let response = await request();
        if (response.status === 401 && !signal.aborted) {
          const fresh = await refreshSession();
          if (fresh) { activeSession = fresh; response = await request(); }
        }
        const result = await response.json();
        if (!response.ok) throw Error(result.detail || "Local dictation could not finish. Nothing has been sent.");
        return result.text;
      },
    });
    void voice.current.start();
  }
  function stopVoice() { voice.current?.cancel();openaiVoice.current?.interrupt(); }
  useEffect(()=>{if(buildView)stopVoice();},[buildView]);
  async function postMessage() {
    if (busy) return;
    if (voice.current?.running || voice.current?.finishing) {
      const draft = await voice.current.finish();
      if (draft !== null) void send(draft);
    } else void send();
  }
  const { screenToFlowPosition, fitView, zoomIn, zoomOut } = useReactFlow();
  const [attention, setAttention] = useState(null);
  const attentionRef = useRef(null);
  const fileRef = useRef(),fileImportAsCopy=useRef(false),requirementsInput=useRef();
  const attachmentInput=useRef();
  const [attachments,setAttachments]=useState([]),[attachmentError,setAttachmentError]=useState(''),[readingAttachments,setReadingAttachments]=useState(false);
  const attachmentReadLock=useRef(false);
  async function attachFiles(files){
    if(!files.length||attachmentReadLock.current)return;
    attachmentReadLock.current=true;const projectAtStart=projectRef.current.id;
    setReadingAttachments(true);setAttachmentError('');
    try {const next=await readAttachments([...files],attachments);if(projectRef.current.id===projectAtStart)setAttachments(previous=>[...previous,...next]);}
    catch(error){setAttachmentError(error.message);}
    finally{attachmentReadLock.current=false;setReadingAttachments(false);}
  }
  const chatScroll = useChatScroll(project.id,chatOpen);
  const latestArchitectureTurn=Array.isArray(project.extensions?.architectureActivity?.turns)?project.extensions.architectureActivity.turns.at(-1):null;
  const runToken = useRef(0);
  const commitGroup = useRef(false);
  const notify = useCallback((t) => setToast(t), []);
  // In Build the prototype card and run bar cover part of the board; fit around them.
  const testing = mode === "review" && reviewView === "test";
  // The notes card sits on the board's left; fit the drawing beside it, never under it.
  const notesShown = false; // notes live in the chat header, never over the board
  const padding = testing
    ? { top: "70px", right: "330px", bottom: "90px", left: "80px" }
    : notesShown
      ? { top: "70px", right: "40px", bottom: "70px", left: "430px" }
      : 0.25;
  const refit = useCallback(
    // Wait a frame or two so newly drawn blocks are measured before fitting them in.
    (nodes) => setTimeout(() => {
      if (!attentionRef.current) fitView({ padding, maxZoom: 1.1, duration: 200, ...(nodes ? { nodes } : {}) });
    }, 180),
    [fitView, testing, notesShown],
  );
  useEffect(() => {
    refit();
  }, [testing, notesShown, refit, pending]);

  useEffect(() => {
    if (!attention) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const zoom = setTimeout(() => {
      if (attention.nodes.length) fitView({ nodes: attention.nodes.map(id => ({ id })), padding: 0.35, maxZoom: 1.4, duration: reduced ? 0 : 550 });
    }, 180);
    const clear = setTimeout(() => {
      attentionRef.current = null;
      setAttention(null);
    }, 3200);
    return () => { clearTimeout(zoom); clearTimeout(clear); };
  }, [attention, fitView]);

  const refreshSession = useCallback(async () => {
    try {
      const next = await discoverLocalAgent();
      setSession(next);
      return next;
    } catch {
      setSession(null);
      return null;
    }
  }, []);
  useEffect(() => {
    refreshSession();
    const timer=setInterval(refreshSession,30000);
    window.addEventListener("focus",refreshSession);
    return ()=>{clearInterval(timer);window.removeEventListener("focus",refreshSession);};
  }, [refreshSession]);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 3500);
    return () => clearTimeout(timer);
  }, [toast]);
  useEffect(() => {
    try {
      const durable = withConversation(project, messages);
      toProjectFile(durable); // Do not persist credentials included in chat.
      localStorage.setItem(STORAGE, JSON.stringify(durable));
      setStorageError(false);
    } catch {
      setStorageError(true);
    }
  }, [project, messages]);
  useEffect(
    () => () => {
      runToken.current++;
      agentAbort.current?.abort();
    },
    [],
  );

  const commit = useCallback(
    (next, remember = true) => {
      if (busy) return;
      const current = projectRef.current;
      if (remember) {
        setHistory((h) => [...h.slice(-29), structuredClone(current)]);
        setFuture([]);
      }
      const updated = withDerived({ ...next, revision: current.revision + 1 });
      projectRef.current = updated;
      setProject(updated);
      setRunStates({});
      setRun(null);
      setProbe(null);
    },
    [busy],
  );

  // Brief, options, decisions and gate edits are not design changes: no revision bump, runs kept.
  const updateEngagement = useCallback((next) => {
    const updated = withDerived(next);
    projectRef.current = updated;
    setProject(updated);
  }, []);
  const syncEngineeringIntent=useCallback((owner,id,events)=>{const current=projectRef.current,next=synchronizeEngineeringIntent(current,id,events,owner);if(next!==current)updateEngagement(next);},[updateEngagement]);
  const changeArchitectureWork=useCallback((change,owner)=>{const current=projectRef.current,next=change.kind==='artifact'?applyArtifactWork(current,owner,change.verified):applyArchitectureChange(current,owner,change);if(next!==current){toProjectFile(next);updateEngagement(next);}},[updateEngagement]);
  const allIssues = checkProject(project).filter((i) => i.level !== "info");
  // Fixture checks only matter for designs that can be test-run; sketches are reviewed in Review.
  const runnable = project.nodes.some((n) => n.data.kind !== "note") && !project.nodes.some((n) => n.data.kind === "resource");
  const issues = runnable ? allIssues.filter((i) => i.level === "error") : [];
  const selectedNode = project.nodes.find((n) => n.id === selected);
  const currentPassed = run?.status === "passed" && run.revision === project.revision;
  const focusBlocks = useMemo(
    () =>
      focus ? new Set(project.nodes.filter((n) => layerOf(n).id === focus).map((n) => n.id)) : null,
    [focus, project.nodes],
  );
  const focusLabel = focus && project.nodes.map(layerOf).find((l) => l.id === focus)?.label;

  // Users navigate components and their details; topology stays internal.
  function goFlow(layer = null) {
    setLevel("flow");
    setFocus(layer);
    setProbe(null);
    const ids = layer
      ? projectRef.current.nodes.filter((n) => layerOf(n).id === layer).map((n) => ({ id: n.id }))
      : null;
    refit(ids);
  }
  function openBlock(id, edge = null) {
    setSelected(id);
    setProbe(edge);
    setLevel("block");
    const n = projectRef.current.nodes.find((x) => x.id === id);
    if (n && focus && layerOf(n).id !== focus) setFocus(layerOf(n).id);
  }
  function goUp() {
    if (level === "block") goFlow(focus);
    else if (focus) goFlow(null);
  }

  useEffect(() => {
    function keys(e) {
      const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName);
      if (e.key === "Escape") {
        if (modal || menu || palette || issuesOpen) {
          if (!(modal === "welcome" && !connection)) setModal(null);
          setMenu(false);
          setPalette(false);
          setIssuesOpen(false);
        } else if (agentAbort.current) agentAbort.current.abort();
        else if (!typing&&!buildView) goUp();
      }
      if(buildView)return;
      if (e.key === "/" && !typing) {
        e.preventDefault();
        setPalette(true);
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "a" && !typing && mode === "design") {
        e.preventDefault();
        setLevel("flow");
        setPicked(new Set(projectRef.current.nodes.map((n) => n.id)));
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z" && !typing && !modal) {
        e.preventDefault();
        if (e.shiftKey) redo(); else undo();
      }
      if ((e.key === "Delete" || e.key === "Backspace") && !typing && picked.size > 1) {
        e.preventDefault();
        removeNodes(picked);
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        document.querySelector(".runbar .run-button")?.click();
      }
    }
    window.addEventListener("keydown", keys);
    return () => window.removeEventListener("keydown", keys);
  });

  const onNodesChange = useCallback(
    (changes) => {
      // React Flow hides unmeasured nodes; keep sizes outside the design revision.
      const sizes = changes.filter((c) => c.type === "dimensions" && c.dimensions);
      if (sizes.length)
        setMeasured((m) => ({ ...m, ...Object.fromEntries(sizes.map((c) => [c.id, c.dimensions])) }));
      if (busy || level === "system") return;
      const real = changes.filter((c) => c.type !== "select" && c.type !== "dimensions");
      if (!real.length) return;
      const dragging = real.some((c) => c.type === "position" && c.dragging);
      const remember = !commitGroup.current;
      commitGroup.current = dragging;
      const current = projectRef.current;
      commit({ ...current, nodes: applyNodeChanges(real, current.nodes) }, remember);
    },
    [commit, busy, level],
  );
  const onEdgesChange = useCallback(
    (changes) => {
      if (busy || level === "system") return;
      const real = changes.filter((c) => c.type !== "select");
      if (real.length)
        commit({ ...projectRef.current, edges: applyEdgeChanges(real, projectRef.current.edges) });
    },
    [commit, busy, level],
  );

  // New blocks land in the middle of the visible board, nudged so they don't stack.
  function centre(count) {
    const box = document.getElementById("canvas")?.getBoundingClientRect();
    const at = box
      ? screenToFlowPosition({ x: box.left + box.width / 2, y: box.top + box.height / 2 })
      : { x: 90, y: 90 };
    return { x: at.x - 105 + (count % 4) * 24, y: at.y - 29 + (count % 4) * 24 };
  }
  function noteText(id, text) {
    const p = projectRef.current;
    commit({ ...p, nodes: p.nodes.map((n) => (n.id === id ? { ...n, data: { ...n.data, label: text.slice(0, 150), description: text.slice(0, 500) } } : n)) });
  }
  function addNote(position, attachTo = null) {
    const p = projectRef.current;
    const id = `note-${crypto.randomUUID().slice(0, 8)}`;
    freshNote.current = id;
    const note = { id, type: "resource", position, data: { label: "", kind: "note", provider: "tools", description: "", config: { region: "", classification: "Internal", timeout: 5000 }, origin: "proposed" } };
    commit({ ...p, nodes: [...p.nodes, note], edges: attachTo ? [...p.edges, { id: `${id}-${attachTo}`, source: id, target: attachTo, type: "smoothstep", label: "" }] : p.edges });
    if (level !== "flow") setLevel("flow");
  }
  function clearBoard() {
    const p = projectRef.current;
    if (!p.nodes.length) return;
    commit({ ...p, nodes: [], edges: [] });
    setPicked(new Set());
    setSelected(null);
    notify("Board cleared — Undo brings it back.");
  }
  function removeNodes(ids) {
    const p = projectRef.current;
    commit({ ...p, nodes: p.nodes.filter((n) => !ids.has(n.id)), edges: p.edges.filter((e) => !ids.has(e.source) && !ids.has(e.target)) });
    setPicked(new Set());
    setSelected(null);
  }
  // What the user changed by hand since the model last saw the board.
  // What the model has seen; starts as the board as it was when the page opened.
  const seen = useRef(null);
  if (!seen.current) seen.current = structuredClone(project);
  const paletteAt = useRef(null);
  const freshNote = useRef(null);
  function canvasChanges(now) {
    const was = seen.current;
    if (!was) return [];
    const before = new Map(was.nodes.map((n) => [n.id, n])),
      after = new Map(now.nodes.map((n) => [n.id, n]));
    const name = (n) => (n.data.kind === "note" ? `note “${n.data.label}”` : n.data.label);
    const out = [];
    for (const n of now.nodes) if (!before.has(n.id)) out.push(`added ${name(n)}`);
    for (const n of was.nodes) if (!after.has(n.id)) out.push(`removed ${name(n)}`);
    for (const n of now.nodes) if (before.has(n.id) && before.get(n.id).data.label !== n.data.label) out.push(`renamed “${before.get(n.id).data.label}” to “${n.data.label}”`);
    const wire = (e) => `${e.source}>${e.target}`;
    const had = new Set(was.edges.map(wire)),
      has = new Set(now.edges.map(wire));
    const label = (id) => (after.get(id) || before.get(id))?.data.label || id;
    for (const e of now.edges) if (!had.has(wire(e))) out.push(`drew an arrow ${label(e.source)} → ${label(e.target)}`);
    for (const e of was.edges) if (!has.has(wire(e))) out.push(`removed the arrow ${label(e.source)} → ${label(e.target)}`);
    return out.slice(0, 40);
  }
  function addComponent(item, position) {
    if (busy) return;
    const next = structuredClone(project);
    const id = crypto.randomUUID();
    next.nodes.push({
      id,
      type: "resource",
      position: position || centre(next.nodes.length),
      data: {
        ...item,
        config: { region: "To be selected", classification: "Internal", timeout: 5000 },
        origin: "proposed",
      },
    });
    commit(next);
    setSelected(id);
    setPalette(false);
    if (level !== "flow") goFlow(null);
    notify(`${item.label} added — wire its ports.`);
  }
  function updateNode(node) {
    commit({ ...project, nodes: project.nodes.map((n) => (n.id === node.id ? node : n)) });
  }
  function removeNode(id) {
    commit({
      ...project,
      nodes: project.nodes.filter((n) => n.id !== id),
      edges: project.edges.filter((e) => e.source !== id && e.target !== id),
    });
    setSelected(null);
    goFlow(focus);
  }
  function undo() {
    if (!history.length || busy || agentBusy) return;
    const previous = history.at(-1);
    setFuture((f) => [...f.slice(-29), structuredClone(projectRef.current)]);
    setHistory((h) => h.slice(0, -1));
    // Undo takes back the design, never what the user has told us since.
    commit(keepEngagement(previous, projectRef.current), false);
    setSelected(null);
    setPending(null);
    notify("Board change undone. Redo restores it.");
  }
  function redo() {
    if (!future.length || busy || agentBusy) return;
    const next = future.at(-1);
    setHistory((h) => [...h.slice(-29), structuredClone(projectRef.current)]);
    setFuture((f) => f.slice(0, -1));
    commit(keepEngagement(next, projectRef.current), false);
    setSelected(null);
    setPending(null);
    notify("Board change redone.");
  }
  function download(data, name, type = "application/json") {
    const url = URL.createObjectURL(
      new Blob(
        [data instanceof Uint8Array || typeof data === "string" ? data : JSON.stringify(data, null, 2)],
        { type },
      ),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function importProject(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      if (file.size > MAX_FILE_BYTES) throw Error("Project files must be 2 MB or smaller.");
      const content = await file.text();
      const raw = JSON.parse(content);
      if (raw.format || raw.version === 1) {
        const { project: opened, migrated, from } = parseProjectFile(content);
        loadDesign(fileImportAsCopy.current?copyProject(opened,crypto.randomUUID()):opened, { own: true });
        notify(fileImportAsCopy.current?"New project created from the saved design. The original is preserved.":migrated ? `Project opened and upgraded from ${from}.` : "Project opened.");
      } else {
        loadDesign(importUpstreamProject(raw));
        notify("OpenArchFlow design imported.");
      }
    } catch (error) {
      notify(error.message);
    }
    e.target.value = "";
  }
  // A project file brings its own records; templates and imports keep the current ones.
  function loadDesign(next, { own = false } = {}) {
    stopVoice();
    attentionRef.current = null;
    setAttention(null);
    if (busy) {
      notify("Stop the run before replacing the design.");
      return;
    }
    seen.current = structuredClone(next);
    // A project file brings its own engagement; templates and imports keep the current one.
    if (own) {
      // Project boundaries keep separate history; never blend records from different projects.
      setHistory([]);
      setFuture([]);
      projectRef.current = next;
      setProject(withDerived(next));
      setRunStates({});
      setRun(null);
      setProbe(null);
      setAttachments([]);setAttachmentError('');
    setMessages(conversationMessages(next, [welcome(next)]));
    } else commit(validateImport(keepEngagement(next, projectRef.current)));
    setSelected(null);
    setPending(null);
    setScenario("happy");
    setView("diagram");
    setMode("design");
    setDesignView("board");
    setModal(null);
    const canvasView=readCanvasView(next);
    setLevel(canvasView.level);setFocus(canvasView.focus);setSelected(canvasView.selected);setTopologyPositions(canvasView.positions);
    refit();
    if (next.importReport) notify(next.importReport.notice);
  }

  const coachedReports=useRef(new WeakMap());
  const emulationMentorKey=JSON.stringify([connection?.provider,connection?.model]);
  useEffect(()=>{
    const report=emulation.result;
    if(buildView||intakeRef.current.some(q=>q.projectId===project.id)||!emulation.coach||emulation.running||!report||!emulationCoachReady(session,connection)||busy||agentBusy||pending||coachedReports.current.get(report)?.has(emulationMentorKey))return;
    void discussEmulation(report,'coach');
  },[buildView,emulation.result,emulation.running,emulation.coach,session,connection,busy,agentBusy,pending]);

  async function discussEmulation(report,intent){
    if(busy||agentBusy||pending||report!==emulation.result)return;
    if(intent==='question'){setChatOpen(true);setInput(current=>current||'Help me understand these local check results: ');requestAnimationFrame(()=>messageInput.current?.focus());return;}
    coachedReports.current.set(report,new Set([...(coachedReports.current.get(report)||[]),emulationMentorKey]));
    setChatOpen(true);
    const guidance=emulationGuidance(projectRef.current,report);
    if(guidance&&!guidance.needsModel){
      const text=guidanceMessage(guidance);setMessages(m=>m.at(-1)?.role==='assistant'&&m.at(-1)?.text===text?m:[...m,{role:'assistant',text}]);
      return;
    }
    if(intent!=='coach')setMessages(m=>[...m,{role:'user',text:'Help me with the next test step.'}]);
    await send(emulationPrompt(projectRef.current,report,intent),'emulation',{mode:'design',view:'emulation'});
  }
  async function send(text = input, origin = "chat", destination = null, reviewTarget = null, intakeOptions = {}) {
    if ((!text.trim() && !(origin === "chat" && attachments.length)) || busy || readingAttachments) return;
    if(origin!=='chat'&&(agentBusy||agentAbort.current))return;
    if(text.length>8000){notify('Keep each message within 8,000 characters; your draft is unchanged.');return;}
    stopVoice();
    const message = text.trim() || "Please review the attached files and help me use them in this architecture.";
    const estimateOnly=intakeOptions.estimateOnly===true;
    const sentAttachments=intakeOptions.attachments||(origin === "chat"?attachments:[]);
    if(sentAttachments.length>4){notify('Keep up to four files in one update; your draft and files are unchanged.');return;}
    if(sentAttachments.some(a=>!a.data)){notify('Attach the missing original files again before sending, or remove their references to continue with text.');return;}
    const requestIds=intakeOptions.requestIds||(origin==='chat'?[crypto.randomUUID()]:[]);
    const requestProject=projectRef.current.id;
    if(origin==='chat'&&!intakeOptions.alreadyLogged&&(agentBusy||agentAbort.current||intakeRef.current.some(q=>q.projectId===requestProject))){
      const id=requestIds[0];updateIntake([...intakeRef.current,{id,projectId:requestProject,text:message,attachments:sentAttachments}]);
      setMessages(m=>[...m,{role:'user',text:message,attachments:sentAttachments,requestId:id,workState:'queued'}]);
      setInput('');setAttachments([]);chatScroll.followLatest();return;
    }
    if ((origin === "chat" || origin === "block-review")&&!intakeOptions.alreadyLogged) {
      setMessages((m) => [...m, { role: "user", text: reviewTarget ? `Review ${reviewTarget.label} with me.` : message, attachments:sentAttachments,...(requestIds.length?{requestId:requestIds[0],workState:'processing'}:{}) }]);
      setInput("");
    }
    if(origin==='chat'){setPending(null);if(!intakeOptions.alreadyLogged)setAttachments([]);}
    setChatOpen(true);
    if (!connection) {
      setRequestState(requestIds,'failed');
      setModal("welcome");
      return;
    }
    if (/^compare all four clouds/i.test(message)) {
      setMode("design");
      setDesignView("options");
    }
    if (!session) {
      setRequestState(requestIds,'failed');
      setMessages((m) => [
        ...m,
        { role: "assistant", text: "Looks like we've lost the connection, so that message didn't go out. Let's fix it.", fix: true },
      ]);
      return;
    }
    if(origin==='chat'&&!intakeOptions.alreadyLogged)setIntakePaused(false);
    const controller = new AbortController();
    agentAbort.current = controller;
    chatScroll.followLatest();
    setArchitectAction(origin==='block-review'?`Reviewing ${reviewTarget?.label||'the block'}…`:origin==='chat'?'Architect is working…':'Updating the design…');
    setAgentBusy(true);
    const activityId=session.architectureActivityEnabled?crypto.randomUUID():null;
    try {
      if(activityId){
        const next=recordArchitectureTurn(projectRef.current,requestProject,{id:activityId,provider:connection.provider,model:connection.model,effort:connection.effort,origin,requestIds:[...requestIds],startedAt:new Date().toISOString()});
        toProjectFile(next);
        updateEngagement(next);
      }
      // Keep the discovery record current from the user's words, whatever model replies.
      const was = projectRef.current;
      const heard = origin === "chat" ? understand(message, was) : { project: was };
      updateEngagement(heard.project);
      const signals = harnessSignals(was, heard.project);
      // The connected architect draws from the user's idea. No local preset blocks.
      const edits = canvasChanges(projectRef.current);
      seen.current = structuredClone(projectRef.current);
      const result = await requestArchitect({
        extra: [{type:"discovery",id:"active-view",text:`The user is working in ${destination ? (destination.mode === "design" ? destination.view : destination.mode) : mode === "design" ? designView : mode}. Use the shared diagram and conversation. Prioritise major system decisions over configuration details; ask only when a material user decision is needed. Otherwise add or refine the needed components and their connections. Keep topology reasoning internal; use plain component names and short explanations for the user.`}, ...(edits.length ? [{ type: "discovery", id: "canvas-changes", text: `Since your last reply the user ${edits.join("; ")}. Build on these changes.` }] : [])],
        session,
        connection,
        message,
        attachments:sentAttachments,
        project: projectRef.current,
        history: intakeOptions.history||messages,
        stage: destination?.mode || mode,
        origin,
        signal: controller.signal,
        activityId,
      });
      if(projectRef.current.id!==requestProject)return;
      if(activityId)updateEngagement(finishArchitectureTurn(projectRef.current,requestProject,activityId,'response_received',result.architectureActivity?.detailsAvailable!==false));
      if(intakeRef.current.some(q=>q.projectId===requestProject)){
        carryIntent.current={projectId:requestProject,text:carryIntent.current?.projectId===requestProject?carryIntent.current.text:message};
        setRequestState(requestIds,'superseded');
        setMessages(m=>[...m,{role:'assistant',text:'I’ve kept your updates. I’m combining them before changing the design.',...(activityId?{activityId}:{})}]);
        return;
      }
      carryIntent.current=null;
      setRequestState(requestIds,'complete');
      if (!estimateOnly && !["document","emulation","block-review"].includes(origin) && result.optionAssessment?.length) {
        const p = projectRef.current, a = p.assessment || defaultAssessment();
        const scores = structuredClone(a.scores), notes = { ...a.notes };
        for (const option of result.optionAssessment) {
          scores[option.provider] = option.scores;
          notes[option.provider] = `AtMem AI Architect proposal — confirm: ${option.rationale}`;
        }
        updateEngagement({ ...p, assessment: { ...a, scores, notes } });
        signals.push("cloud comparison updated");
      }
      if (!estimateOnly && !["document","emulation","block-review"].includes(origin) && result.usageUpdates?.length) {
        let next = projectRef.current;
        for (const update of result.usageUpdates) if (message.includes(update.sourceText)) next = setUsage(next, update.key, update.value);
        updateEngagement(next);
      }
      if (origin === "document" && result.requirementUpdates?.length) {
        updateEngagement(proposeCommentRevisions(projectRef.current,was,result.requirementUpdates));
        signals.push("suggested wording ready to review in Requirements");
      } else if (!estimateOnly && origin!=="emulation" && result.requirementUpdates?.length) {
        const p = projectRef.current;
        const updates = new Map(result.requirementUpdates.filter(u => message.includes(u.sourceText)).map(u => [u.id,u]));
        const applicable = new Map([...updates].filter(([id]) => was.needs?.find(r=>r.id===id)?.statement === p.needs?.find(r=>r.id===id)?.statement));
        updateEngagement({ ...p, needs: (p.needs || []).map(r => applicable.has(r.id) ? { ...r, statement: applicable.get(r.id).statement, source: "user", basis:`User statement: ${applicable.get(r.id).sourceText}`, ...(applicable.get(r.id).rationale?{rationale:applicable.get(r.id).rationale}:{}) } : r),
          extensions: {...p.extensions,requirementComments:(p.extensions?.requirementComments || []).map(c=> applicable.has(c.requirementId) && applicable.get(c.requirementId).sourceText === c.text ? {...c,status:'reviewed',revisedStatement:applicable.get(c.requirementId).statement} : c)} });
        signals.push("requirements refined from your answer");
      }
      if (!estimateOnly && !["document","emulation","block-review"].includes(origin) && result.decisionUpdates?.length) updateEngagement(applyDecisionUpdates(projectRef.current,result.decisionUpdates,message));
      if (!["document","emulation","block-review"].includes(origin) && result.priceQuotes?.length) updateEngagement(applyPriceQuotes(projectRef.current, result.priceQuotes));
      if(['chat','workflow','block-review'].includes(origin)){
        const p=projectRef.current,q=result.followUp;
        updateEngagement({...p,lastAsked:q?{id:'architect-question',topic:q.topic||'',question:q.question,why:q.why,beginner:q.example||''}:null,extensions:{...p.extensions,activeConsultation:{hasQuestion:!!q}}});
      }
      if(origin==='block-review'&&reviewTarget&&result.componentReview){
        try {updateEngagement(applyComponentReview(projectRef.current,reviewTarget,result.componentReview));signals.push('block review and linked questions recorded');}
        catch(error){notify(error.message);}
      }
      setMessages((m) => [...m, { role: "assistant", ...(activityId?{activityId}:{}), text: origin==="emulation"?groundEmulationMessage(emulation.result,result.message,projectRef.current):result.message, live: true, signals, contextUsed: result.contextUsed }]);
      openaiVoice.current?.speak(origin==="emulation"?groundEmulationMessage(emulation.result,result.message,projectRef.current):result.message);
      if (!estimateOnly && result.proposal && !["document","block-review"].includes(origin)) {
        const proposal = { ...result.proposal, next: validateImport(result.proposal.next), ...(origin==="emulation"?{emulationCorrection:true}:{}) };
        if(origin==="emulation")guardEmulationCorrection(was,proposal.next);
        // "Draw as we talk": the design evolves with the conversation; each step is undoable.
        if (drawLive && origin !== "preview") applyProposal(proposal, { live: true });
        else setPending(proposal);
      }
      if (!estimateOnly && !["document","preview","emulation","block-review"].includes(origin) && result.requirementDrafts?.length) updateEngagement(applyRequirementDrafts(projectRef.current,result.requirementDrafts));
      return result.message;
    } catch (error) {
      if(projectRef.current.id!==requestProject)return;
      if(activityId)updateEngagement(finishArchitectureTurn(projectRef.current,requestProject,activityId,error.name==='AbortError'?'cancelled':'failed'));
      setRequestState(requestIds,'failed');setIntakePaused(true);
      setMessages((m) => [
        ...m,
        error.name === "AbortError"
          ? { role: "assistant", ...(activityId?{activityId}:{}), text: "Stopped. Nothing on the board changed." }
          : { role: "assistant", ...(activityId?{activityId}:{}), text: `Hmm, that didn't work: ${error.message}`, fix: /connect|sign|model|running|service|failed|limit/i.test(error.message) },
      ]);
    } finally {
      if (agentAbort.current === controller) {
        setAgentBusy(false);
        agentAbort.current = null;
      }
    }
  }
  async function reviewComponent(id){
    const current=projectRef.current,item=componentReviews(current).find(r=>r.id===id);if(!item)return;
    setChatOpen(true);
    return send(`Review this block against its latest requirements: ${item.label} (id: ${id}). Check responsibility, inputs/outputs, ownership, identity, state, failures and dependencies. Prioritise consequential system decisions over ports or packaging. Explain what is sound; ask only material unresolved questions. Preserve all scope and existing systems. Do not claim runtime validation. Current concerns: ${item.issues.map(i=>i.text).join('; ')||'None recorded; inspect for missing decisions.'}. Return componentReview with componentId ${id}, summary and questions. Return followUp only if a user decision is needed; do not return a graph change.`,"block-review",null,item);
  }
  // Applying a proposal is a design decision: it is recorded, and Undo restores the previous design.
  function applyProposal(proposal = pending, { live = false, quiet = false } = {}) {
    const current = projectRef.current;
    if (proposal.baseRevision !== current.revision) {
      notify("The design changed since this proposal. Ask again.");
      setPending(null);
      return;
    }
    if(proposal.emulationCorrection){guardEmulationCorrection(current,proposal.next);emulation.scheduleRetest();}
    // A newly drawn graph needs room for arrow labels. Preserve user-arranged
    // positions on refinements and any diagram that retains existing node IDs.
    if (proposal.next.nodes.length && !proposal.next.nodes.some(n => current.nodes.some(existing => existing.id === n.id))) {
      proposal = { ...proposal, next: autoLayout(proposal.next) };
    }
    const decision = {
      ...newDecision(current),
      subject: `design.${slugSubject(proposal.title)}`,
      title: proposal.title,
      status: "Accepted",
      context: proposal.body || "",
      decision: `${live ? "Drawn while talking" : "Applied"} as design revision ${current.revision + 1}.`,
    };
    const change = proposalDiff(current, proposal.next);
    const emphasis = diagramAttention(current, proposal.next);
    attentionRef.current = emphasis;
    setAttention(emphasis);
    // Remember the concept we drew so we can keep evolving it until the user takes over.
    commit({ ...keepEngagement(proposal.next, current), decisions: [...(current.decisions || []), decision], conceptSig: quiet ? conceptSignature(proposal.next) : null });
    seen.current = structuredClone(proposal.next);
    const summary = [
      ...change.added.map((l) => `+ ${l}`),
      ...change.changed.map((l) => `~ ${l}`),
      ...change.removed.map((l) => `− ${l}`),
    ].join("\n");
    if (!quiet) setMessages((m) => [
      ...m,
      {
        role: "assistant",
        text: `${live ? "Drew it" : "Applied"}: ${proposal.title}${summary ? `\n${summary.split("\n").slice(0, 3).join("\n")}${summary.split("\n").length > 3 ? `\n+${summary.split("\n").length - 3} more` : ""}` : ""}`,
        signals: [`${live ? "drew" : "applied"} ${proposal.next.nodes.length} blocks`, `logged ${decision.id.toUpperCase()}`, "undo ↶"],
      },
    ]);
    setPending(null);
    setSelected(null);
    setScenario("happy");
    if (mode !== "design" || designView !== "board") {
      setMode("design");
      setDesignView("board");
    }
    setLevel(previous=>previous==='block'?'flow':previous);
    setFocus(null);
    refit();
  }

  function exportPulumi() {
    const files = pulumiScaffold(project, environment);
    download(
      zipSync(Object.fromEntries(Object.entries(files).map(([name, text]) => [name, strToU8(text)]))),
      `atmem-ai-architect-${environment}-pulumi.zip`,
      "application/zip",
    );
    notify("Pulumi scaffold exported. Resource implementations are not generated.");
  }
  function cancelRun() {
    runToken.current++;
    setBusy(false);
    setRun((r) => (r ? { ...r, status: "cancelled" } : r));
    setRunStates((s) =>
      Object.fromEntries(Object.entries(s).map(([id, state]) => [id, state === "running" ? "cancelled" : state])),
    );
  }
  async function runFlow() {
    if (busy) return;
    if (!runnable || issues.length) return;
    const revision = project.revision,
      p = structuredClone({ ...project, nodes: project.nodes.filter((n) => n.data.kind !== "note"), edges: project.edges.filter((e) => !project.nodes.some((n) => n.data.kind === "note" && (n.id === e.source || n.id === e.target))) }),
      token = ++runToken.current;
    setBusy(true);
    setRunStates({});
    const steps = [],
      outputs = {},
      states = {};
    setRun({ status: "running", revision, scenario, steps: [] });
    let failed = false;
    try {
      for (const n of orderProject(p)) {
        if (token !== runToken.current) return;
        const parents = p.edges.filter((e) => e.target === n.id);
        // Several inputs are merged, in wire order.
        const input = parents.length ? Object.assign({}, ...parents.map((e) => outputs[e.source])) : null;
        if (parents.some((e) => states[e.source] === "failed" || states[e.source] === "skipped")) {
          states[n.id] = "skipped";
          steps.push({ id: n.id, label: n.data.label, status: "skipped", input: null, output: null, error: "Not executed because an upstream step failed.", duration: 0 });
          setRunStates({ ...states });
          continue;
        }
        states[n.id] = "running";
        setRunStates({ ...states });
        const started = performance.now();
        await new Promise((resolve) => setTimeout(resolve, 380));
        if (token !== runToken.current) return;
        try {
          const output = executeBlock(n, input, scenario);
          outputs[n.id] = output;
          states[n.id] = "passed";
          steps.push({ id: n.id, label: n.data.label, status: "passed", input, output, duration: Math.round(performance.now() - started) });
        } catch (error) {
          failed = true;
          states[n.id] = "failed";
          steps.push({ id: n.id, label: n.data.label, status: "failed", input, output: null, error: error.message, duration: Math.round(performance.now() - started) });
        }
        setRunStates({ ...states });
        setRun({ status: "running", revision, scenario, steps: [...steps] });
      }
      setRun({ status: failed ? "failed" : "passed", revision, scenario, steps: [...steps] });
    } finally {
      if (token === runToken.current) setBusy(false);
    }
  }

  // Canvas content per level.
  // A pending proposal is drawn on the board straight away, as a preview, until applied or dismissed.
  const shown = pending?.next && mode === "design" ? pending.next : project;
  const previewing = shown !== project;
  const blockReviews = useMemo(()=>componentReviews(shown),[shown]);
  const reviewBlock = id => {setMode('design');setDesignView('board');setFocus(null);openBlock(id);};
  const system = useMemo(() => systemView(shown, runStates), [shown, runStates]);
  const wireClass = (source) =>
    `wire ${runStates[source] === "failed" ? "wire-failed" : runStates[source] === "passed" ? "wire-passed" : ""}`;
  const canvasNodes =
    level === "system"
      ? system.nodes.map((n) => ({ ...n, position:topologyPositions[n.id]||n.position, data:{...n.data,onExplore:()=>n.data.blocks.length===1?reviewBlock(n.data.blocks[0]):goFlow(n.data.layer),onReview:()=>reviewBlock(blockReviews.find(r=>n.data.blocks.includes(r.id)&&r.issues.length)?.id||n.data.blocks[0]),reviewSummary:{reviewed:blockReviews.filter(r=>n.data.blocks.includes(r.id)&&r.status==='reviewed').length,issues:blockReviews.filter(r=>n.data.blocks.includes(r.id)).flatMap(r=>r.issues)}}, measured: measured[n.id], className: previewing ? "preview" : "" }))
      : shown.nodes.map((n) => ({
          ...n,
          type: n.data.kind === "note" ? "note" : n.type,
          measured: measured[n.id],
          className: `${previewing ? "preview" : ""} ${attention?.nodes.includes(n.id) ? "diagram-attention" : ""}`,
          selected: n.id === selected || picked.has(n.id),
          data: { ...n.data, blockReview:blockReviews.find(r=>r.id===n.id), onReview:()=>reviewBlock(n.id), onText: noteText, fresh: n.id === freshNote.current, runState: runStates[n.id], dim: (focusBlocks && !focusBlocks.has(n.id)) || (testing && !n.data.poc && n.data.kind !== "resource" && project.nodes.some((x) => x.data.poc)) },
        }));
  const canvasEdges =
    level === "system"
      ? system.edges.map((e) => ({ ...e, className: wireClass(e.data.sources[0]), markerEnd: { type: "arrowclosed", width: 14, height: 14 } }))
      : shown.edges.map((e) => ({
          ...e,
          className: `${previewing ? "preview" : ""} ${attention?.edges.includes(e.id) ? "diagram-attention" : ""} ${wireClass(e.source)} ${focusBlocks && !(focusBlocks.has(e.source) || focusBlocks.has(e.target)) ? "dim" : ""}`,
          animated: busy && runStates[e.source] === "passed",
          markerEnd: { type: "arrowclosed", width: 14, height: 14 },
        }));
  const slug = project.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "atflow";
  const exportDocument = () => {
    download(deploymentDocument(project, run), `${slug}-deployment-document.md`, "text/markdown");
    notify("Deployment document generated from the current project.");
  };
  const exportFiles = (files, suffix) => {
    download(zipSync(Object.fromEntries(Object.entries(files).map(([name, content]) => [name, typeof content === "string" ? strToU8(content) : content]))), `${slug}-r${project.revision}-${suffix}.zip`, "application/zip");
  };
  const downloadBundle = bundle => {
    download(zipSync(Object.fromEntries(Object.entries(bundle.files).map(([name,content])=>[name,typeof content === "string"?strToU8(content):content]))),bundle.filename,"application/zip");
    if(bundle.project?.id===projectRef.current.id)updateEngagement(acknowledgeStage(projectRef.current,'delivery'));
    notify("ZIP downloaded.");setStarOffer(value=>value+1);
  };
  const exportPack = async () => {
    try {
      notify("Preparing documents and diagram exports…");
      downloadBundle(await outputBundle(project,run,environment));
    } catch(e) { notify(e.message); }
  };
  const exportTerraform = async (validation = null) => {
    try {
      toProjectFile(project); // Apply the same credential refusal as every project export.
      const files=terraformSketch(project,environment);
      const receipt=await verifiedReceipt(files,validation);
      exportFiles({...files,...(receipt?{'validation-receipt.json':JSON.stringify(receipt,null,2)}:{})}, "terraform");
      notify("Terraform sketch exported with resource coverage and unfinished work.");
    } catch (e) { notify(e.message); }
  };
  // One short real request proves the sign-in, model ID and local service all work.
  async function verifyConnection(choice) {
    let live = session;
    if (!live) {
      try {
        live = await discoverLocalAgent();
        setSession(live);
      } catch {
        throw Error("AtMem AI Architect's local service isn't running. Start it with npm run local, then try again.");
      }
    }
    const result = await requestArchitect({
      session: live,
      connection: choice,
      message: "Connection check from AtMem AI Architect. Reply with one short sentence; no proposal.",
      project: projectRef.current,
      history: [],
      stage: "discover",
      signal: AbortSignal.timeout(90000),
    });
    if (!result?.message) throw Error("The model didn't reply. Check the model ID and sign-in.");
  }
  // Sketching is the model's job; the skill's starter sketch is described to it as a starting point.
  function sketchIt() {
    send("Please draft a first sketch of the architecture from what I've told you, as a proposal I can review.");
  }
  function skipQuestion() {
    const p = projectRef.current;
    const skipped = { ...p, asked: [...(p.asked || []), ask?.id].filter(Boolean) };
    const next = nextQuestion({ ...skipped, lastAsked: null });
    updateEngagement({ ...skipped, lastAsked: next });
    setMessages((m) => [...m, { role: "assistant", text: next ? `No problem, we'll come back to it.\n\n${next.question}\n${next.beginner}` : "That's everything I need for now." }]);
  }
  // Autosave to the helper (your account on this computer), a moment after each change.
  const binned = useRef(new Set());
  useEffect(() => {
    if (!session || binned.current.has(project.id) || (!project.nodes.length && !project.brief?.application?.trim() && messages.length < 2)) return;
    const t = setTimeout(async () => {
      try {
        const saved=await projectStore(session, "save", { id: project.id, file: toProjectFile(withConversation(project, messages)) });
        if(saved.memory)setMemorySync({projectId:project.id,...saved.memory});
      } catch (error) { setMemorySync(current=>({...((current?.projectId===project.id)?current:{}),projectId:project.id,status:'sync_failed'}));notify(`Project conversation could not be saved: ${error.message}`); }
    }, 800);
    return () => clearTimeout(t);
  }, [project, messages, session?.token]);
  async function saveEngineeringProject(owner,expected){
    const current=projectRef.current;
    if(current.id!==owner)throw Error('The project changed while opening engineering work. Return to that project before submitting its draft.');
    if(expected&&expected!==current)throw Error('The design changed before saving the handoff. Review Delivery again.');
    const conversation=messagesRef.current;
    const result=await projectStore(session,'save',{id:owner,file:toProjectFile(withConversation(current,conversation))});
    if(expected&&(projectRef.current!==expected||messagesRef.current!==conversation))throw Error('The design changed while saving the handoff. Review Delivery again.');
    return result;
  }
  async function refreshProjects() {
    if (!session) return;
    try {
      setSaved(await projectStore(session, "list"));
    } catch (e) {
      notify(e.message);
    }
  }
  function switchTo(next) {
    chooseWorkspace('canvas');setBuildRequest(null);
    next = withDerived(next);
    const leaving = projectRef.current;
    if (session && !binned.current.has(leaving.id) && (leaving.nodes.length || leaving.brief?.application?.trim() || messages.length > 1))
      projectStore(session, "save", { id: leaving.id, file: toProjectFile(withConversation(leaving, messages)) }).catch(() => {});
    setHistory([]);
    setFuture([]);
    projectRef.current = next;
    seen.current = structuredClone(next);
    setProject(next);
    setRun(null);
    setRunStates({});
    setPending(null);
    setSelected(null);
    setPicked(new Set());
    const canvasView=readCanvasView(next);
    setLevel(canvasView.level);setFocus(canvasView.focus);setSelected(canvasView.selected);setTopologyPositions(canvasView.positions);
    setMode("design");
    setDesignView("board");
    setPeek(null);
    setAttachments([]);setAttachmentError('');
    setMessages(conversationMessages(next, [welcome(next)]));
    setInput("");
    setProbe(null);
    setSnapshot(null);
    setCtx(null);
    refit();
  }
  async function openSaved(id) {
    try {
      const { project: opened } = fromProjectFile(await projectStore(session, "get", { id }));
      switchTo(opened);
      setModal(null);
    } catch (e) {
      notify(e.message);
    }
  }
  const linkedProject = useRef(null);
  useEffect(() => {
    const id = projectIdFromUrl(window.location.href);
    if (!session?.token || !id || linkedProject.current === id) return;
    let active = true;
    (async () => {
      try {
        const { project: opened } = fromProjectFile(await projectStore(session, "get", { id }));
        if (!active) return;
        const leaving = projectRef.current;
        if (leaving.id !== id && !binned.current.has(leaving.id) && (leaving.nodes.length || leaving.brief?.application?.trim() || messages.length > 1)) {
          await projectStore(session, "save", { id: leaving.id, file: toProjectFile(withConversation(leaving, messages)) });
        }
        if (!active) return;
        linkedProject.current = id;
        switchTo(opened);
        setModal(null);
      } catch (error) { if (active) notify(error.message); }
    })();
    return () => { active = false; };
  }, [session?.token]);
  function newProject() {
    setModal("start-over");
  }
  async function binProject(id) {
    try {
      binned.current.add(id);
      await projectStore(session, "trash", { id });
      if (id === projectRef.current.id) switchTo(validateImport(emptyProject()));
      await refreshProjects();
      notify("Moved to the bin. Restore it from Projects any time.");
    } catch (e) {
      binned.current.delete(id);
      notify(e.message);
    }
  }
  async function restoreProject(id) {
    try {
      await projectStore(session, "restore", { id });
      binned.current.delete(id);
      await refreshProjects();
    } catch (e) {
      notify(e.message);
    }
  }
  async function purgeProject(id) {
    try {
      await projectStore(session, "purge", { id });
      await refreshProjects();
    } catch (e) {
      notify(e.message);
    }
  }
  const guidance = useMemo(()=>journey(project),[project]);
  const activeSection = designSection(mode,designView);
  const nextAction = journeyAction(guidance,activeSection.id);
  function followJourney(next=guidance){
    if(busy||agentBusy)return;
    setChatOpen(true);
    consultationAttempts.current.add(`${projectRef.current.id}:${projectRef.current.revision}:${next.mode}:${next.view}`);
    const section=DESIGN_SECTIONS.find(item=>item.id===journeySectionId(next.id));
    setMode(section?.mode||next.mode);setDesignView(section?.view||next.view);if(section?.mode==='review')setReviewView('findings');
    send(next.prompt,'workflow',next);
  }
  function visitJourney(id,event){
    const section=DESIGN_SECTIONS.find(item=>item.id===journeySectionId(id));
    if(!section)return;
    event?.currentTarget.closest("details")?.removeAttribute("open");
    setMode(section.mode);setDesignView(section.view);
    if(section.mode==='review')setReviewView('findings');
  }
  async function chooseCloud(provider){
    if(busy||agentBusy||pending)return;
    const ok=await send(`Use ${OPTION_NAMES[provider]} for this project.`,"chat",{mode:"design",view:"options"});
    if(ok){setMode('design');setDesignView('options');setChatOpen(true);}
  }
  function continueJourney(){
    if(!guidance.checkpoint||busy||agentBusy)return;
    const next=advanceJourney(projectRef.current,guidance.checkpoint);
    updateEngagement(next);const upcoming=journey(next);
    if(upcoming.id==='delivery')visitJourney('delivery');else followJourney(upcoming);
  }
  const findings = useMemo(() => review(project), [project]);
  const costs = useMemo(() => estimate(project), [project]);
  useEffect(() => {
    if (buildView || !drawLive || !session || !connection || busy || agentBusy || input.trim() || mode !== "design" || designView !== "board" || modal) return;
    const edits = canvasChanges(project);
    if (!edits.length || project.nodes.some(n => n.data.kind === "note" && !n.data.label.trim())) return;
    const timer = setTimeout(() => send("The user changed the shared diagram: " + edits.join("; ") + ". Work with these edits, preserve their comments and blocks, refine only what follows from their intent, and ask one useful next question if needed.", "canvas"), 1200);
    return () => clearTimeout(timer);
  }, [buildView,project.nodes,project.edges,drawLive,session,connection,busy,agentBusy,input,mode,designView,modal]);
  const topics = progress(project);
  const blockerCount = findings.filter((f) => f.severity === "blocker" && f.status === "open").length;
  const ask = project.extensions?.activeConsultation ? (project.extensions.activeConsultation.hasQuestion ? project.lastAsked : null) : project.lastAsked?.question ? project.lastAsked : nextQuestion(project);
  function saveProjectFile() {
    try {
      download(JSON.stringify(toProjectFile(withConversation(project, messages)), null, 2), `${slug}.atmem-ai-architect.json`);
      notify("Project file saved. Open it later from ⋯ → Open project file.");
      return true;
    } catch (error) {
      notify(error.message);
      return false;
    }
  }
  const exportDecisions = () =>
    download(`# Decisions · ${project.name}\n\n${adrMarkdown(project.decisions)}`, `${slug}-decisions.md`, "text/markdown");
  function showDesign(cloud) {
    send(`Propose this design on ${OPTION_NAMES[cloud]}, keeping its structure, so I can compare.`);
  }
  function recommend(option) {
    const d = recommendationDecision(project, option, OPTION_NAMES);
    updateEngagement({ ...project, decisions: [...(project.decisions || []), d] });
    setDesignView("decisions");
    notify(`${d.id.toUpperCase()} drafted. Add an owner and the consequences.`);
  }
  const scenarioReady = ([, , needs]) => !needs || project.nodes.some((n) => n.data.kind === needs);
  const onBoard = testing || (mode === "design" && designView === "board");
  const diff = pending?.next ? proposalDiff(project, pending.next) : null;

  const specificationChecks=(
          <ReviewView expanded
            project={project}
            findings={findings}
            onChange={updateEngagement}
            onOpen={(id) => {
              setMode("design");
              setDesignView("board");
              openBlock(id);
            }}
            onAddRequirement={(category) => {
              setMode("design");setDesignView("requirements");setChatOpen(true);
              send(`Help us establish the ${category} requirement for this architecture. Explain why it matters and ask for the target we actually need; do not insert a default SLA.`,"workflow",{mode:"design",view:"requirements"});
            }}
          />
  );
  return (
    <div style={{"--chat-panel-width":`${chatWidth}px`}} className={`app ${chatOpen&&!buildView ? "" : "chat-closed"} ${buildView?"build-workspace":""}`}>
      <header className="bar">
        <button aria-label="About AtMem AI Architect" className="brand" onClick={() => setModal("about")} title="About AtMem AI Architect">
          <Mark />

        </button>
        <nav className="crumbs" aria-label="Level"><span className="workspace-label">PROJECT</span>
          <button className="projects-btn" aria-label="Projects" title="Your projects" onClick={() => (refreshProjects(), setModal("projects"))}>
            <FolderOpen size={22} /> Projects
          </button>
          <label className="project-rename"><input
            className="project-name"
            title={project.name}
            aria-label="Project name"
            value={project.name}
            onChange={(e) => commit({ ...project, name: e.target.value })}
          /><PencilRuler size={14} aria-hidden="true"/></label>
        </nav>
        <div className="bar-actions">
          {storageError && <span className="warn-text">Not saved</span>}
          <button
            className="icon"
            title={theme === "dark" ? "Light mode" : "Dark mode"}
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            onClick={() => {
              const next = theme === "dark" ? "light" : "dark";
              document.documentElement.dataset.theme = next;
              try {
                localStorage.setItem(THEME, next);
              } catch {}
              setTheme(next);
            }}
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <button className="icon" title="More" aria-label="More" onClick={() => setMenu((m) => !m)}>
            <MoreHorizontal size={16} />
          </button>

        </div>
        {menu && (
          <div className="menu" role="menu" onClick={() => setMenu(false)}>
            <button role="menuitem" onClick={() => (refreshProjects(), setModal("projects"))} disabled={busy}><FolderOpen size={16}/>Projects</button>
            <button role="menuitem" onClick={newProject} disabled={busy}><Plus size={16}/>New project</button>
            <hr/><button role="menuitem" onClick={() => setPalette(true)} disabled={busy}><Plus size={16}/>Add a block</button>
            <button role="menuitem" onClick={() => setModal("templates")} disabled={busy}><LayoutTemplate size={16}/>Templates</button>
            <hr/><button role="menuitem" onClick={() => setModal("import")} disabled={busy}><GitBranch size={16}/>Import diagram</button>
            <button role="menuitem" onClick={() => setModal("project-file")} disabled={busy}><FolderOpen size={16}/>Open project file</button>
            <hr/><button role="menuitem" onClick={() => setModal("memory")} disabled={!session}><BrainActivity size={18} active={false}/>AtMem memory</button>
            <button role="menuitem" onClick={() => setModal("start-over")} disabled={busy || agentBusy}><RotateCcw size={16}/>Start over</button>
            <hr />
            <button role="menuitem" onClick={() => setModal("connections")}><Waypoints size={16}/>AI providers</button>
            <button role="menuitem" onClick={() => setModal("licenses")}><ShieldCheck size={16}/>Licences</button>
            <a role="menuitem" href={STAR_URL} target="_blank" rel="noopener noreferrer">Star on GitHub ↗</a>
          </div>
        )}
      </header>

      <section className="journey-wizard unified-journey" aria-label="Architecture journey">
        <nav className="stage-tabs" role="tablist" aria-label="Project stages">{DESIGN_SECTIONS.map((section,i)=><button key={section.id} role="tab" aria-label={section.label} aria-selected={activeSection.id===section.id} className={completedStages(project)[section.id]?'stage-complete':''} onClick={()=>visitJourney(section.id)} title={completedStages(project)[section.id]?'Working draft acknowledged':'Not yet complete'}><span>{completedStages(project)[section.id]?'✓':i+1}</span>{section.label}</button>)}</nav>
        {nextAction&&<div className="journey-current"><button className="btn primary" disabled={busy||agentBusy||!!pending} onClick={()=>nextAction.kind==='navigate'?visitJourney(nextAction.section):nextAction.kind==='continue'?continueJourney():followJourney()}>{nextAction.label}</button></div>}
      </section>
      <main
        id="canvas"
        className={`canvas level-${level}`}
        onDrop={(e) => {
          e.preventDefault();
          if(buildView)return;
          const item = ALL_CATALOG.find((c) => c.id === e.dataTransfer.getData("application/atforma-block"));
          if (item) addComponent(item, screenToFlowPosition({ x: e.clientX, y: e.clientY }));
        }}
        onDragOver={(e) => {
          e.preventDefault();
          e.dataTransfer.dropEffect = "move";
        }}
      >
        <div className={`board-surface ${treeOpen&&level!=="block"?"has-component-sidebar":""}`} hidden={!onBoard}>
          {level!=="block"&&<aside className="board-components component-navigator" data-expanded={treeOpen} aria-label="Board components"><button className="btn" aria-label="Toggle components and layers" aria-expanded={treeOpen} onClick={()=>setTreeOpen(!treeOpen)}><LayoutGrid size={16}/> Components &amp; layers</button>
{treeOpen&&<nav className="board-component-tree" aria-label="Component tree"><strong>{project.name}</strong><div className="tree-views"><button disabled={!blockReviews.length} onClick={()=>{reviewBlock((blockReviews.find(r=>r.status!=='reviewed')||blockReviews[0]).id);}}><CheckCheck size={16}/> Review blocks · {blockReviews.filter(r=>r.status==='reviewed').length}/{blockReviews.length}</button></div>{[...new Map(project.nodes.filter(n=>n.data.kind!=='note').map(n=>[layerOf(n).id,layerOf(n)])).values()].map(layer=><details open key={layer.id}><summary>{layer.label}</summary>{project.nodes.filter(n=>n.data.kind!=='note'&&layerOf(n).id===layer.id).map(n=><button key={n.id} aria-current={selected===n.id?'true':undefined} onClick={()=>{setMode('design');setDesignView('board');setFocus(null);setLevel('flow');setSelected(n.id);setTimeout(()=>fitView({nodes:[{id:n.id}],padding:1,maxZoom:1.2,duration:350}),100);}}><Database size={14}/><span>{n.data.label}<small>{n.data.service||n.data.provider}</small><small className={`tree-review-state ${blockReviews.find(r=>r.id===n.id)?.status}`}>{blockReviews.find(r=>r.id===n.id)?.statusLabel}</small></span></button>)}</details>)}</nav>}
          {treeOpen&&<button className="btn" disabled={busy} onClick={()=>setPalette(true)}><Plus size={16}/> Add component</button>}</aside>}
          {!hasDesign&&!palette&&!dismissedStarts.includes(project.id)&&<section className="board-start" aria-label="Start your project"><button type="button" className="icon board-start-close" aria-label="Dismiss welcome card" title="Dismiss welcome card" onClick={dismissStart}><X size={16}/></button><h2>What would you like to create?</h2><div className="row"><button className="btn primary" onClick={()=>{dismissStart();setChatOpen(true);document.querySelector('.composer textarea, .chat textarea')?.focus();}}>Start chatting</button><button className="btn" onClick={()=>{setChatOpen(true);requirementsInput.current.click();}}>Upload requirements or diagram</button><button className="btn" onClick={()=>setModal("project-file")}>Open project</button></div><InlineNote label="Supported starting files">Word, PDF, text, Markdown, draw.io, images and Architect project JSON.</InlineNote></section>}
        <ReactFlow
          nodes={canvasNodes}
          edges={canvasEdges}
          nodeTypes={nodeTypes}
          colorMode={theme}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={(c) => {
            if (!busy && level === "flow")
              commit({ ...project, edges: addEdge({ ...c, type: "smoothstep", label: "data" }, project.edges) });
          }}
          isValidConnection={(c) =>
            c.source !== c.target && !project.edges.some((e) => e.source === c.source && e.target === c.target)
          }
          onNodeClick={(_, n) => {
            if (level === "system") return;
            setSelected(n.id);
            setProbe(null);
          }}
          onNodeDoubleClick={(_, n) => (level === "system" ? n.data.blocks.length===1?reviewBlock(n.data.blocks[0]):goFlow(n.data.layer) : openBlock(n.id))}
          onEdgeClick={(_, e) => (level === "system" ? goFlow(null) : openBlock(e.source, e))}
          onPaneContextMenu={(e) => {
            e.preventDefault();
            if (previewing) return;
            setCtx({ x: e.clientX, y: e.clientY, at: screenToFlowPosition({ x: e.clientX, y: e.clientY }) });
          }}
          onNodeContextMenu={(e, n) => {
            e.preventDefault();
            if (previewing) return;
            setCtx({ x: e.clientX, y: e.clientY, at: screenToFlowPosition({ x: e.clientX, y: e.clientY }), node: level === "system" ? null : n });
          }}
          onPaneClick={() => {
            setCtx(null);
            setPicked(new Set());
            setSelected(null);
            setPalette(false);
          }}
          nodesDraggable={!busy && !previewing && level === "flow"}
          nodesConnectable={!busy && !previewing && level === "flow"}
          elementsSelectable={!busy}
          deleteKeyCode={busy || level !== "flow" ? null : ["Backspace", "Delete"]}
          fitView
          fitViewOptions={{ padding: 0.25, maxZoom: 1.2 }}
          minZoom={0.25}
          maxZoom={1.8}
          zoomOnDoubleClick={false}
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={20} size={1} />
        </ReactFlow>

        <div className="toolbar" aria-label="Tools">
          <button
            className="icon"
            title="Auto-arrange"
            aria-label="Auto-arrange"
            disabled={busy || previewing || level==='block' || !project.nodes.length}
            onClick={() => {
              if(level==='system')setTopologyPositions(arrangeOverview(system,measured));
              else commit(autoLayout(projectRef.current));
              refit();
            }}
          >
            <LayoutGrid size={17} />
          </button>
          <button className="icon" title="Clear board" aria-label="Clear board" disabled={!project.nodes.length || busy} onClick={clearBoard}>
            <Eraser size={17} />
          </button>
          <button className="icon" title="Undo board change" aria-label="Undo" disabled={!history.length || busy || agentBusy} onClick={undo}>
            <Undo2 size={17} />
          </button>
          <button className="icon" title="Redo board change" aria-label="Redo" disabled={!future.length || busy || agentBusy} onClick={redo}><Redo2 size={17} /></button>
        </div>
        {level !== "block" && (
          <div className="zoom">
            <button className="icon" aria-label="Zoom out" onClick={() => zoomOut()}><ZoomOut size={15} /></button>
            <button className="icon" aria-label="Fit" title="Fit" onClick={() => refit()}><Maximize2 size={14} /></button>
            <button className="icon" aria-label="Zoom in" onClick={() => zoomIn()}><ZoomIn size={15} /></button>
          </div>
        )}
        {palette && <Palette onAdd={(item) => addComponent(item, paletteAt.current || undefined)} onClose={() => ((paletteAt.current = null), setPalette(false))} disabled={busy} />}

        {level === "system" && project.nodes.length > 0 && (
          <p className="hint">Double-click to open</p>
        )}
        {level === "flow" && selectedNode && (
          <p className="hint">Double-click for detail · Esc back</p>
        )}
        {ctx && (
          <div className="ctx-menu" role="menu" style={{ left: Math.min(ctx.x,window.innerWidth-210), top: Math.min(ctx.y,window.innerHeight-200) }} onMouseLeave={() => setCtx(null)}>
            {ctx.node ? (
              <>
                <button role="menuitem" onClick={() => (addNote({ x: ctx.at.x + 40, y: ctx.at.y - 120 }, ctx.node.id), setCtx(null))}>
                  <StickyNote size={16}/> Add comment
                </button>
                <div className="ctx-divider" role="separator"/>
                <button role="menuitem" className="danger" onClick={() => (removeNodes(new Set(picked.size > 1 ? picked : [ctx.node.id])), setCtx(null))}>
                  <Trash2 size={16}/>{picked.size > 1 ? `Delete ${picked.size} items` : "Delete"}
                </button>
              </>
            ) : (
              <>
                <button role="menuitem" onClick={() => ((paletteAt.current = ctx.at), setPalette(true), setCtx(null))}>
                  <Plus size={16}/> Add block here
                </button>
                <button role="menuitem" onClick={() => (addNote(ctx.at), setCtx(null))}>
                  <StickyNote size={16}/> Add comment here
                </button>
                <button role="menuitem" onClick={() => (setLevel("flow"), setPicked(new Set(project.nodes.map((n) => n.id))), setCtx(null))}>
                  <Scan size={16}/> Select all
                </button>
                <div className="ctx-divider" role="separator"/>
                <button role="menuitem" className="danger" disabled={!project.nodes.length} onClick={() => (clearBoard(), setCtx(null))}>
                  <Eraser size={16}/> Clear board
                </button>
              </>
            )}
          </div>
        )}
        {picked.size > 1 && (
          <div className="preview-bar" role="status">
            <span>{picked.size} selected</span>
            <button className="btn" onClick={() => removeNodes(picked)}>
              Delete
            </button>
            <button className="btn ghost" onClick={() => setPicked(new Set())}>
              Cancel
            </button>
          </div>
        )}
        {previewing && (
          <div className="preview-bar" role="status">
            <span>
              Preview · <strong>{pending.title}</strong>
            </span>
            <button className="btn primary" disabled={busy} onClick={() => applyProposal()}>
              Apply
            </button>
            <button className="btn ghost" onClick={() => setPending(null)}>
              Dismiss
            </button>
          </div>
        )}
        {!shown.nodes.length && (
          <div className="empty-canvas">
            <p className="muted">Describe your idea in the chat — it takes shape here.</p>
          </div>
        )}

        {level === "block" && selectedNode && (
          <BlockDetail
            project={project}
            node={selectedNode}
            run={run}
            probe={probe}
            busy={busy||agentBusy||!!pending}
            reviewItems={componentReviews(project)}
            onReviewConfirm={()=>{updateEngagement(markComponentReviewed(project,selectedNode.id));notify(`${selectedNode.data.label}: design reviewed.`);}}
            onReviewDiscuss={issue=>{if(issue?.kind!=='finding')return reviewComponent(selectedNode.id);setChatOpen(true);return send(`Help address this design issue for ${selectedNode.data.label}: ${issue.text} Suggested next step: ${issue.action||'Propose a concrete correction.'} Explain what is missing and why it matters here, then propose the design changes needed to resolve it. This is engineering work, not a question the user must solve. Ask only for a consequential business choice that cannot be inferred from the saved design. Preserve all requirements, existing systems and provider choices. Keep any change reviewable, and do not claim monitoring or other runtime behavior is already implemented.`,'workflow');}}
            onRequirementSave={async(id,text)=>{
              updateEngagement(editBlockRequirement(projectRef.current,selectedNode.id,id,text));
              if(connection&&session)await reviewComponent(selectedNode.id);
              else notify('Requirement saved. Local checks updated; connect Architect for its review.');
            }}
            onReviewQuestion={question=>updateEngagement({...project,openQuestions:[...(project.openQuestions||[]),newQuestion({question,links:[selectedNode.id]})]})}
            onReviewResolve={(id,answer)=>updateEngagement({...project,openQuestions:project.openQuestions.map(q=>q.id===id?{...q,status:'answered',answer}:q)})}
            onChange={updateNode}
            onWorkModelChange={changeArchitectureWork}
            onRemove={() => removeNode(selectedNode.id)}
            onOpen={(id) => openBlock(id)}
            onSpec={()=>{visitJourney('scope');setTimeout(()=>document.getElementById('component-spec-'+selectedNode.id)?.scrollIntoView({block:'start'}),0);}}
            onBack={goUp}
          />
        )}

        {testing && view === "panel" && level !== "block" && (
          <FrontPanel project={project} run={run} onSelect={openBlock} />
        )}

        {testing && !runnable && (
          <div className="runbar note">
            <span>
              {project.nodes.length
                ? "This design is a sketch, so it can't be test-run yet. Test runs need blocks with sample-data behaviour — the Predictive maintenance and Analytics templates have them."
                : "Nothing to test yet. Describe what you want to build in Discover first."}
            </span>
          </div>
        )}
        {testing && runnable && issues.length > 0 && (
          <div className="runbar note">
            <span>Fix before testing:</span>
            <div className="steps">
              {issues.map((issue, i) => (
                <button key={i} className="step failed" onClick={() => issue.nodeId && openBlock(issue.nodeId)}>
                  {issue.text}
                </button>
              ))}
            </div>
          </div>
        )}
        {testing && runnable && !issues.length && (
          <div className="runbar">
            {busy ? (
              <button className="btn" onClick={cancelRun}>
                <X size={14} /> Stop
              </button>
            ) : (
              <button className="btn primary run-button" onClick={runFlow} title="Runs each block in order with sample data on this computer. No AI model, no cloud, no cost.">
                <Play size={13} /> Test with sample data
              </button>
            )}
            <select aria-label="Test scenario" disabled={busy} value={scenario} onChange={(e) => setScenario(e.target.value)}>
              {SCENARIOS.filter(scenarioReady).map(([id, label]) => (
                <option key={id} value={id}>
                  {label}
                </option>
              ))}
            </select>
            <div className="seg">
              <button className={view === "diagram" ? "on" : ""} onClick={() => setView("diagram")}>Diagram</button>
              <button className={view === "panel" ? "on" : ""} onClick={() => setView("panel")}>Panel</button>
            </div>
            {run && (
              <span className={`run-summary ${run.status}`}>
                {STATUS_GLYPH[run.status]} {run.status[0].toUpperCase() + run.status.slice(1)} · {run.steps.filter((s) => s.status === "passed").length}/{project.nodes.length}
              </span>
            )}
            <div className="steps">
              {run?.steps.map((s) => (
                <button
                  key={s.id}
                  className={`step ${s.status} ${selected === s.id ? "on" : ""}`}
                  title={s.error || `${s.duration} ms`}
                  onClick={() => openBlock(s.id)}
                >
                  {s.label}
                </button>
              ))}
              {!run && <span className="muted">Pick a scenario, then test. Failure scenarios show where problems are caught.</span>}
            </div>
          </div>
        )}

        {testing && runnable && level !== "block" && <TestCard project={project} run={run} onOpen={(id) => openBlock(id)} />}

        </div>
        <div className="review-workspace" hidden={mode!=="review"&&mode!=="estimate"}>
        <header className="review-intro"><h2>Review</h2></header>
        <div className="review-design-status"><ShieldCheck size={18}/><span>{findings.filter(f=>f.status==='open').length} design items</span><button className="icon" aria-label="Open design checks in specification" title="Specification" onClick={()=>visitJourney('scope')}><Code2 size={16}/></button></div>
        <section className="review-costs" aria-label="Project costs">
        {["review","estimate"].includes(mode) && <EstimateView project={project} result={costs} onChange={updateEngagement} busy={busy||agentBusy||!!pending} onEstimate={refreshEstimate} onChooseRegion={()=>{visitJourney('cloud');requestAnimationFrame(()=>{const input=document.querySelector('.location-region-form input');input?.focus();input?.scrollIntoView({block:'center',behavior:'instant'});});}} pricing={pricingState} onNext={()=>{const section=document.querySelector('.review-generation');const target=section?.querySelector('button')||section;if(target){target.setAttribute('tabindex','-1');target.focus({preventScroll:true});target.scrollIntoView({block:'center'});}}} />}
        </section>
        {mode==='review'&&session?.engineeringEnabled&&<section className="review-generation" aria-label="Generation and verification"><EngineeringPanel key={project.id} project={project} onBusyChange={setGenerationPending} onWorkModelChange={changeArchitectureWork} onIntentContext={syncEngineeringIntent} projectId={project.id} session={session} connection={connection} contextBusy={busy||agentBusy||!!pending} saveProject={()=>saveEngineeringProject(project.id)} buildRequest={buildRequest} onBuildRequestHandled={id=>setBuildRequest(current=>current?.id===id?null:current)} onConnections={()=>setModal('connections')}/></section>}
        {mode==='review'&&!session?.engineeringEnabled&&<p>Generation and local checks require the engineering service. Your design is retained; Delivery can package the design and remaining tasks.</p>}
        {mode==='review'&&<ProjectChecks receipt={checkReceipt} project={project} environment={environment} session={session} onReceipt={setCheckReceipt} onBusy={setChecking}/>}
        {mode==='review'&&<footer className="review-finish"><div><strong>3. Package and download</strong><p>Explore all files and download one project ZIP in Delivery.</p></div><button className="btn primary" onClick={()=>{const next=acknowledgeStage(projectRef.current,'review');updateEngagement(costs.complete?{...next,extensions:{...next.extensions,journey:{...next.extensions.journey,estimate:journey(next).keys.estimate}}}:next);visitJourney('delivery');}}>Complete →</button></footer>}
        </div>




        {onBoard&&emulationOpen&&<div className="emulation-dock"><EmulationPanel project={project} session={session} emulation={emulation} onDiscuss={discussEmulation} onOpenComponent={id=>{reviewBlock(id);setEmulationOpen(false);}} discussionBusy={busy||agentBusy||!!pending} onClose={()=>setEmulationOpen(false)} onBuild={session?.engineeringEnabled?()=>{setEmulationOpen(false);buildCurrentDesign('test');}:undefined}/></div>}

        {mode === "design" && designView === "outputs" && <OutputsView onNavigate={async target=>{const [stage,selector]={requirements:['scope','.requirements-document'],location:['cloud','section[aria-label="Country and region"]'],cost:['review','.review-costs'],implementation:['review','.review-generation'],checks:['review','.project-checks']}[target];visitJourney(stage);await new Promise((resolve,reject)=>{const started=performance.now();function focus(){const element=document.querySelector(selector);if(element&&element.getClientRects().length){element.setAttribute('tabindex','-1');element.focus({preventScroll:true});element.scrollIntoView({block:'start',behavior:'instant'});resolve();}else if(performance.now()-started<5000)requestAnimationFrame(focus);else reject(Error('Section is unavailable. Use the stage tabs to continue.'));}requestAnimationFrame(focus);});}} checkReceipt={checkReceipt} onDownloaded={()=>{updateEngagement(acknowledgeStage(projectRef.current,'delivery'));setStarOffer(value=>value+1);}} onReview={()=>visitJourney('review')} onSave={expected=>saveEngineeringProject(project.id,expected)} project={project} run={run} environment={environment} session={session} emulation={emulation} onDiscuss={discussEmulation} discussionBusy={busy||agentBusy||!!pending} onDownload={downloadBundle} onBuild={session?.engineeringEnabled?()=>visitJourney('review'):undefined} onBack={()=>setDesignView("board")} />}
        {mode === "design" && designView === "terraform" && <TerraformView project={project} environment={environment} session={session} emulation={emulation} onDiscuss={discussEmulation} discussionBusy={busy||agentBusy||!!pending} onDelivery={()=>visitJourney("delivery")} onBuild={session?.engineeringEnabled?()=>visitJourney('review'):undefined} onBack={()=>setDesignView("board")} />}
        <div className="choices-workspace" hidden={!(mode==="design"&&["options","decisions","location"].includes(designView))}>
        {mode === "design" && ["options","decisions"].includes(designView) && (
          <OptionsView project={project} busy={busy||agentBusy||!!pending} onChoose={chooseCloud} onContinue={()=>{updateEngagement(acknowledgeStage(projectRef.current,'cloud'));visitJourney('review');}} onPreview={(provider)=>{setDesignView("board");setLevel("flow");setChatOpen(true);send(`Preview a concrete ${OPTION_NAMES[provider]} implementation of our working scope, using actual named services in data.service and explicit connections. Keep existing systems and comments. Use the known country/residency constraints, or leave region undecided and ask the country question. This is an alternative preview, not a cloud choice or deployment. Return a graph proposal and explain key integration assumptions.`,"preview",{mode:"design",view:"board"});}} onDiscuss={(question) => { setChatOpen(true); send(question, "workflow"); }} />
        )}
        {mode === "design" && ["options","decisions","location"].includes(designView) && <LocationChoices project={project} onChange={commit} onDiscuss={()=>{setChatOpen(true);send('Review the accepted cloud, data country and cloud region. Ask one material unresolved location question. Preserve selected regions and residency.','workflow');}}/>}
        </div>
        {mode === "design" && designView === "requirements" && (
          <RequirementsView checks={specificationChecks} onContinue={()=>{updateEngagement(acknowledgeStage(projectRef.current,'scope'));visitJourney('cloud');}} onUpload={()=>{setChatOpen(true);requirementsInput.current.click();}} onOpenProject={()=>setModal("project-file")} project={project} onChange={updateEngagement} reviewing={agentBusy} onReview={(comments)=>{setChatOpen(true);send("Propose revisions for these user comments on the requirements document. The document will remain unchanged until the user applies each suggestion. Explain the proposed change; never say you have already changed the document. Return requirementUpdates for the existing IDs where the feedback is clear, quoting the user's comment exactly in sourceText. Preserve other requirements and the diagram. Ask one question if a comment is ambiguous.\n" + comments.map(c=>`Requirement ${c.requirementId}${c.selectedText ? ` (selected text: ${c.selectedText.slice(0,300)})` : ""} — comment: ${c.text}`).join("\n"), "document");}} onDiscuss={(question) => { setChatOpen(true); send(question, "workflow"); }} />
        )}
      </main>

      {!chatOpen&&!buildView && <button className="icon chat-reopen" title="Show chat" aria-label="Show chat" onClick={()=>setChatOpen(true)}><PanelRightOpen size={18}/></button>}
      {chatOpen&&!buildView && (
        <aside className="chat" aria-label="Chat"><ChatResizeHandle width={chatWidth} onChange={resizeChat}/>
          <div className="chat-head">
            <div className="chat-heading-row"><strong className="chat-title" aria-label="AI Architect">
              <Mark size={24} />
            </strong><button className="icon" title="Clear chat view" aria-label="Clear chat view" disabled={busy||agentBusy||intake.length>0||messages.length<=chatView.start} onClick={()=>changeChatView({start:messages.length,turnIds:(project.extensions?.architectureActivity?.turns||[]).map(turn=>turn.id)})}><Trash2 size={16}/></button>{(chatView.start>0||chatView.turnIds.length>0)&&<button className="icon" title="Restore chat history" aria-label="Restore chat history" onClick={()=>changeChatView({start:0,turnIds:[]})}><Undo2 size={16}/></button>}<button className="icon chat-width-toggle" onClick={()=>resizeChat(chatWidth>360?360:Math.max(320,Math.min(720,window.innerWidth-360)))} aria-label={chatWidth>360?"Narrow chat":"Widen chat"} title={chatWidth>360?"Narrow chat":"Widen chat"}>{chatWidth>360?<ChevronsRightLeft size={17}/>:<ChevronsLeftRight size={17}/>}</button><button className="icon" title="Hide chat" aria-label="Hide chat" onClick={()=>setChatOpen(false)}><PanelRightClose size={16}/></button></div>
            <label className="live-toggle" title="On: changes are drawn as we talk, and you can undo any of them. Off: they wait as previews for you to apply.">
              <input
                type="checkbox"
                checked={drawLive}
                onChange={(e) => {
                  setDrawLive(e.target.checked);
                  try {
                    localStorage.setItem("atforma-draw-live", e.target.checked ? "on" : "off");
                  } catch {}
                }}
              />
              Draw as we talk
            </label>
            <button className="model" onClick={() => setModal("connections")} title="AI providers">
              <span className={`led ${connection && session ? "on" : ""}`} />
              {connection ? `${connection.model}${connection.effort ? ` · ${EFFORT_LABEL[connection.effort] || connection.effort}` : ""}` : "Connect a model"}
            </button>
          </div>
          <div className="skills" aria-label="Active skills">
            <button className="known-bar" disabled={!session} aria-label="AtMem memory" title="Open AtMem memory, confirmed decisions and sync activity" onClick={()=>setModal("memory")}><BrainActivity size={18} active={false}/>{memoryLabel}<ChevronRight size={14}/></button>
            <button
              className={`known-bar ${peek === "known" ? "on" : ""}`}
              aria-label="Design context" aria-expanded={peek === "known"} title="Review what is known, assumed or still open"
              onClick={() => setPeek((p) => (p === "known" ? null : "known"))}
            >
              <CheckCheck size={15}/> Design context <ChevronRight size={14}/>
            </button>
            {WORKFLOWS.filter((w) => w.id === project.workflow).map((w) => (
              <button key={w.id} className={`skill ${peek === "skill" ? "on" : ""}`} onClick={() => setPeek((p) => (p === "skill" ? null : "skill"))}>
                Skill: {w.name}
              </button>
            ))}
            {guidance.availableModes.includes("review") && (
              <button className="skill" title="Review rules check the design on every change" onClick={() => setMode("review")}>
                Review {findings.filter((f) => f.status === "open").length}
              </button>
            )}
          </div>
          {peek === "skill" &&
            WORKFLOWS.filter((w) => w.id === project.workflow).map((w) => (
              <div key={w.id} className="peek">
                <strong>{w.name}</strong> <span className="muted">knows</span>
                <div className="knows">
                  {w.knows.map((k) => (
                    <span key={k}>{k}</span>
                  ))}
                </div>
              </div>
            ))}
          {peek === "known" && (
            <ul className="peek known-list" aria-label="Design context summary"><li className="context-caption">Context from our conversation · not workflow steps</li>
              {topics.map((t) => (
                <li key={t.id} className={t.state} title={project.brief?.[t.id] || t.question}>
                  <span>{t.state === "known" ? "✓" : t.state === "assumed" ? "~" : "·"}</span>
                  {t.label}
                  {t.state !== "open" && <em>{String(project.brief?.[t.id] || "").split("\n").filter((l) => !/^Not sure yet/.test(l)).pop() || "assumed"}</em>}
                </li>
              ))}
            </ul>
          )}
          <div className="messages" ref={chatScroll.viewport}>
            <div className="message-list" ref={chatScroll.content}>
            {architectureChatEntries(project,messages).filter(entry=>entry.kind==='message'?entry.index>=chatView.start:entry.kind==='activity'?!chatView.turnIds.includes(entry.turn.id):entry.kind==='legacy-activity'?entry.entries.some(item=>!chatView.turnIds.includes(item.turn.id)):true).map(entry=>{
              if(entry.kind==='activity-error')return <p key="activity-error" role="alert">{entry.error}</p>;
              if(entry.kind==='legacy-activity')return <EarlierArchitectureActivity key={entry.id} entries={entry.entries} projectId={project.id} session={session}/>;
              if(entry.kind==='activity')return <ArchitectureTurn key={project.id+':'+entry.turn.id} turn={entry.turn} number={entry.number} projectId={project.id} session={session} active={agentBusy&&entry.turn.clientStatus==='submitted'&&entry.turn.id===latestArchitectureTurn?.id} working={agentBusy&&entry.turn.clientStatus==='submitted'} onStop={()=>agentAbort.current?.abort()}/>;
              const m=entry.message,i=entry.index,turn=project.extensions?.architectureActivity?.turns?.find(t=>t.id===m.activityId),messageTime=m.createdAt||(m.role==='assistant'?turn?.completedAt:null)||turn?.startedAt;
              return (
              <div key={i} className={`msg ${m.role}`}>
                <header className="message-meta"><span>{m.role==='user'?'You':'Architect'}</span><time dateTime={messageTime||undefined} title={messageTime?new Date(messageTime).toLocaleString():'No timestamp recorded'}>{messageTime?new Date(messageTime).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}):'—'}</time></header><ChatMessage text={m.text} concise={m.role==='assistant'}/>
                {(m.workState==='queued'||m.workState==='processing'&&intake.some(q=>q.id===m.requestId))&&<small className="message-work-state">Queued for the next update <button className="link" onClick={()=>{updateIntake(intakeRef.current.filter(q=>q.id!==m.requestId));setRequestState([m.requestId],'cancelled');}}>Remove from queue</button><button className="link" onClick={()=>{if(input||attachments.length){notify('Your current draft is preserved. Send or clear it before editing a queued update.');return;}const queued=intakeRef.current.find(q=>q.id===m.requestId);if(!queued)return;setInput(queued.text);setAttachments(queued.attachments);updateIntake(intakeRef.current.filter(q=>q.id!==m.requestId));setRequestState([m.requestId],'cancelled');}}>Edit update</button>{m.attachments?.some(a=>!a.data)&&<button className="link" onClick={()=>{updateIntake(intakeRef.current.map(q=>q.id===m.requestId?{...q,attachments:[]}:q));setIntakePaused(false);}}>Continue with text only</button>}</small>}
                {!!m.attachments?.length&&<div className="sent-attachments">{m.attachments.map(a=><figure key={a.id}>{a.data&&a.mime.startsWith('image/')&&<img src={`data:${a.mime};base64,${a.data}`} alt={a.name}/>}<figcaption><Paperclip size={12}/>{a.name}{a.originalNotSaved && <small>Original file not saved; attach it again to review its contents.</small>}</figcaption></figure>)}</div>}
                {m.fix && (
                  <button className="btn fix" onClick={() => setModal("connections")}>
                    Fix connection
                  </button>
                )}
                {m.signals?.length > 0 && (
                  <div className="signals" aria-label="What the harness did">
                    {m.signals.map((sig) => (
                      <span key={sig}>{sig}</span>
                    ))}
                  </div>
                )}
                {m.contextUsed && <ContextUsed value={m.contextUsed} />}
              </div>
            );})}
            {pending && diff && (
              <div className="proposal">
                <strong>{pending.title}</strong>
                <ul>
                  {diff.added.map((l) => <li key={`a${l}`} className="add">+ {l}</li>)}
                  {diff.changed.map((l) => <li key={`c${l}`} className="chg">~ {l}</li>)}
                  {diff.removed.map((l) => <li key={`r${l}`} className="del">− {l}</li>)}
                  {(diff.wiresAdded > 0 || diff.wiresRemoved > 0) && (
                    <li className="muted">
                      wires +{diff.wiresAdded} −{diff.wiresRemoved}
                    </li>
                  )}
                </ul>
                <small className="muted">Based on r{pending.baseRevision}</small>
                <div className="row">
                  <button className="btn primary" disabled={busy} onClick={() => applyProposal()}>Apply to canvas</button>
                  <button className="btn ghost" onClick={() => setPending(null)}>Dismiss</button>
                </div>
              </div>
            )}
            {agentBusy && !(session?.architectureActivityEnabled&&latestArchitectureTurn?.clientStatus==='submitted') && (
              <div className="msg assistant working">
                <BrainActivity size={24} /> Architecting…
                <button className="link" onClick={() => agentAbort.current?.abort()}>Cancel</button>
              </div>
            )}
            </div>
          </div>
          {chatScroll.away&&<button className="chat-jump-latest" aria-label="Jump to latest message" onClick={chatScroll.followLatest}>↓</button>}
          {!!intake.filter(q=>q.projectId===project.id).length&&<div className="intake-status" role="status">{intake.filter(q=>q.projectId===project.id).length} update(s) {intakePaused?'saved · paused':'queued · combining next'}{intakeIssue&&<span> {intakeIssue}</span>}{intakePaused&&<button className="link" onClick={()=>setIntakePaused(false)}>Resume</button>}</div>}
          <div className="prompts">
            {mode === "design" && project.workflow && !project.nodes.length && !pending && (
              <button className="primary-chip" disabled={busy || agentBusy} onClick={sketchIt}>Sketch it →</button>
            )}
            {PROMPTS[mode].filter(() => project.nodes.length > 0 && !["idea","scope"].includes(guidance.id)).map((s) => (
              <button key={s} disabled={busy || agentBusy} onClick={() => send(s)}>
                {s}
              </button>
            ))}
          </div>
          {(agentBusy||generationPending||['starting','running'].includes(engineeringStatus?.state)||pricingState.busy||checking)&&<div className="chat-working-status" role="status" aria-live="polite"><BrainActivity size={26}/><span>{agentBusy?architectAction:generationPending?'Starting project generation…':['starting','running'].includes(engineeringStatus?.state)?'Generating project files…':checking?'Running checks…':'Calculating costs…'}</span></div>}
          {readingAttachments&&<p className="attachment-status" role="status"><BrainActivity/> Reading files…</p>}
          {attachmentError&&<p className="attachment-status" role="alert">{attachmentError}</p>}
          {!!attachments.length&&<div className="attachment-tray" aria-label="Attachments ready to send">{attachments.map(a=><div className="attachment-chip" key={a.id}>{a.data&&a.mime.startsWith('image/')?<img src={`data:${a.mime};base64,${a.data}`} alt=""/>:<Paperclip size={16}/>}<span>{a.name}<small>{!a.data?'Original missing · attach again':a.mime.startsWith('image/')?'Image':a.mime==='application/pdf'||a.mime.includes('wordprocessingml')?'Text will be extracted; embedded images omitted':'Document text'}</small></span><button className="icon" aria-label={`Remove ${a.name}`} onClick={()=>setAttachments(list=>list.filter(item=>item.id!==a.id))}><X size={14}/></button></div>)}<p>Sent to your selected architect with this message. Original files are not stored in project files.</p></div>}
          <form
            className="composer"
            onSubmit={(e) => {
              e.preventDefault();
              void postMessage();
            }}
          >
            <textarea
              onPaste={e=>{const files=[...e.clipboardData.files];if(files.length){e.preventDefault();void attachFiles(files);}}}
              ref={messageInput}
              aria-label="Your message"
              placeholder={brief(project) ? "Reply in your own words…" : "Describe what you want to build…"}
              rows={2}
              value={input}
              onChange={(e) => { stopVoice(); setInput(e.target.value); }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void postMessage();
                }
              }}
            />
            <div className="composer-actions">
            <button type="button" className="icon attach-button" aria-label="Attach images or documents" title="Attach images or documents" disabled={readingAttachments} onClick={()=>attachmentInput.current.click()}><Paperclip size={18}/></button>
            <input id="chat-attachment-input" type="file" ref={attachmentInput} accept={ATTACHMENT_ACCEPT} multiple hidden onChange={e=>{void attachFiles(e.target.files);e.target.value='';}}/>
            <button
              type="button"
              className={`mic ${voiceActive ? "on" : ""}`}
              aria-label={voiceActive ? "Stop dictation" : "Start dictation"}
              aria-pressed={voiceActive}
              title={voiceActive ? "Stop dictation and finish the transcript" : "Dictate locally with Whisper"}
              disabled={voiceState === "transcribing"}
              onClick={voiceActive ? () => { void voice.current?.finish(); } : startVoice}
            >
              {voiceActive ? <Square size={13} /> : <Mic size={15} />}
            </button>
            <button type="submit" className="send" aria-label="Send message" disabled={(!input.trim() && !voiceActive && !attachments.length) || busy || readingAttachments || voiceState === "transcribing"}>
              <ArrowUp size={15} />
            </button>
            </div>
          </form>
          {session&&<OpenAIVoicePanel key={project.id} session={session} connection={connection} transportRef={openaiVoice} onConnections={()=>setModal('connections')} onStart={()=>{voice.current?.cancel();setVoiceError('');}} onTranscript={(text,automatic)=>{
            if(automatic&&!input.trim()&&!attachments.length){setInput(text);void send(text);}
            else setInput(current=>current+(current.trim()?' ':'')+text);
          }}/>}
          <div className="voice-status" role="status" aria-live="polite">
            {!voiceError&&["starting","transcribing"].includes(voiceState)&&<BrainActivity size={22}/>}
            {voiceError || ({ starting: "Opening microphone…", listening: "Dictating locally — review your words, then press Send.", transcribing: "Finishing your transcript…" }[voiceState] || "")}
          </div>
        </aside>
      )}

      <input type="file" id="requirements-file-input" ref={requirementsInput} accept={ATTACHMENT_ACCEPT} multiple hidden onChange={async e=>{const files=[...e.target.files];e.target.value='';if(!files.length||readingAttachments)return;const uploadOwner=projectRef.current.id;setReadingAttachments(true);setAttachmentError('');try{const added=await readAttachments(files,attachments);if(projectRef.current.id!==uploadOwner)return;const all=[...attachments,...added];setAttachments(all);setChatOpen(true);setInput('Read these requirements and diagrams. Summarise what you understand, propose requirements and a connected design, and ask one focused question about anything important that is unclear. Preserve existing systems and distinguish source facts from assumptions.');if(connection&&session){setReadingAttachments(false);void send('Read these requirements and diagrams. Summarise what you understand, propose requirements and a connected design, and ask one focused question about anything important that is unclear. Preserve existing systems and distinguish source facts from assumptions.','chat',null,null,{attachments:all});}else{setModal('connections');}}catch(error){setAttachmentError(error.message);}finally{setReadingAttachments(false);}}}/>
      <input id="project-file-input" type="file" ref={fileRef} accept="application/json,.json" hidden onChange={importProject} />
      {toast && (
        <div className="toast" role="status">
          {toast === "Preparing documents and diagram exports…"&&<BrainActivity/>}{toast}
        </div>
      )}
      <StarPrompt offer={starOffer}/>
      {modal && (
        <div className="backdrop" onMouseDown={(e) => e.target === e.currentTarget && !(modal === "welcome" && !connection) && setModal(null)}>
          <section className={`modal ${modal==="memory"?"memory-modal":""}`} role="dialog" aria-modal="true" aria-label={modal}>
            {!(modal === "welcome" && !connection) && <button className="icon modal-close" onClick={() => setModal(null)} aria-label="Close dialog">
              <X size={16} />
            </button>}
            {modal === "project-file" ? (<><h2>Open project</h2><button className="btn primary" onClick={()=>{fileImportAsCopy.current=false;fileRef.current.click();}}>Open project</button></>) : modal === "memory" ? (
              <MemoryPanel key={project.id} session={session} project={project} onError={notify} onStatus={status=>setMemorySync({projectId:project.id,...status})} />
            ) : modal === "templates" ? (
              <TemplateDialog onLoad={loadDesign} />
            ) : modal === "import" ? (
              <ImportDialog onLoad={loadDesign} onNotify={notify} />
            ) : modal === "pulumi" ? (
              <PulumiDialog
                snapshot={snapshot}
                onSnapshot={setSnapshot}
                onLoad={loadDesign}
                onExport={exportPulumi}
                onNotify={notify}
                environment={environment}
              />
            ) : modal === "projects" ? (
              <div><div className="row"><button className="btn" onClick={()=>setModal("project-file")}>Open project</button><button className="btn" onClick={saveProjectFile}>Save project</button></div><ProjectsDialog
                list={saved}
                folder={saved.folder}
                currentId={project.id}
                onOpen={openSaved}
                onNew={newProject}
                onBin={binProject}
                onRestore={restoreProject}
                onPurge={purgeProject}
              /></div>
            ) : modal === "start-over" ? (
              <>
                <h2>Start over?</h2>
                <p>Start a new idea with an empty board and chat. Requirements, decisions and estimates start fresh too. Your model connection stays.</p>
                <div className="reset-actions">
                  <button className="btn primary" title="Download your project, then start a new one" aria-label="Save project and start over" onClick={() => {
                    if (!saveProjectFile()) return;
                    switchTo(validateImport(emptyProject()));
                    setModal(null);
                  }}><Package size={18}/> Save & start new</button>
                  <button
                    className="btn" title="Start a new project without downloading this one" aria-label="Start over without download"
                    onClick={() => {
                      switchTo(validateImport(emptyProject()));
                      setModal(null);
                    }}
                  >
                    <Plus size={18}/> Start without saving
                  </button>
                  <button className="btn ghost" onClick={() => setModal(null)}>
                    <ArrowLeft size={18}/> Keep working
                  </button>
                </div>
                <p className="modal-fine">Save a project file to reopen this engagement later. Undo and redo apply within the current project.</p>
              </>
            ) : modal === "connections" || modal === "welcome" ? (
              <Connections
                session={session}
                connection={connection}
                onRetry={refreshSession}
                welcome={!connection}
                onCheck={verifyConnection}
                onSave={(choice) => {
                  setConnection(choice);
                  saveConnection(choice);
                  setModal(null);
                }}
              />
            ) : modal === "licenses" ? (
              <>
                <h2>AtMem</h2><a href="/licenses/atmem-APACHE-2.0.txt" target="_blank" rel="noreferrer">Apache 2.0</a>
              </>
            ) : (
              <>
                <h2>AtMem AI Architect</h2>
                <p className="muted">v{appVersion}</p><InlineNote label="Keyboard shortcuts">/ Add block · Esc Board · ⌘↵ Run</InlineNote>
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")).render(
  <ReactFlowProvider>
    <App />
  </ReactFlowProvider>,
);
