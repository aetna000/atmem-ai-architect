import {applyDrawingLayout,updateDrawingLayout} from './drawing-layout.mjs';
import {ArchitectureStatus} from './ArchitectureStatus.jsx';
import {ProjectOverview} from './ProjectOverview.jsx';
import {HandoffReview,PageExplorer} from './HandoffReview.jsx';
import {DrawioCanvas} from './DrawioCanvas.jsx';
import {DrawioShapePalette} from './DrawioShapePalette.jsx';
import {DiagramPages,projectPages} from './DiagramPages.jsx';
import {DiagramMermaid} from './DiagramMermaid.jsx';
import {boardGraph,graphMermaid,drawioFile,drawioShapes} from './drawio-model.mjs';
import {EngineeringModelView} from './EngineeringModelView.jsx';
import {ArchitectureDiagramWorkspace,DiagramPicker} from './ArchitectureDiagramWorkspace.jsx';
import {validateDiagramModel,diagramFromSelection,emptyDiagramModel} from './architecture-diagrams.mjs';
import {updateRequirementsDocument} from './requirements-document.mjs';
import {DesignComments} from './DesignComments.jsx';
import {applyCommentProposal,commentBasis,commentPrompt,commentTarget,parseCommentProposal} from './design-comments.mjs';
import {architectureConsistency} from './architecture-consistency.mjs';
import {SystemModelWorkspace} from './SystemModelView.jsx';
import {validateSystemModel} from './system-model.mjs';
import {BLOCK_SYMBOLS} from './block-symbols.mjs';
import {copyBoardItems,pasteBoardItems} from './board-clipboard.mjs';
import {appliedQualityBasis} from './canvas-quality.mjs';
import {canvasProposal,canvasBasis,canvasProposalRecords} from './codex-canvas.mjs';
import {engineeringCall,verifiedEngineeringDownload} from './engineering-client.mjs';
import {BlockSpecProperties,BlockBuildSpec,BlockHierarchy,NestedBlocks} from './BlockBuildSpec.jsx';
import {removeBlocks,interfaceFields} from './block-spec.mjs';
import {nestedCanvas,preferredNestedScope} from './nested-canvas.mjs';
import {validateCapturedDiagrams} from './captured-diagrams.mjs';
import {HOSTED,connectHostedWorkspace,hostedInitial,hostedCall,hostedRevision,noteHostedChange} from './hosted-workspace.mjs';
import {readyExample,isReadyExample} from './ready-example.mjs';
import {ReadyExampleDownload} from './ReadyExample.jsx';
import {StarPrompt,STAR_URL} from './StarPrompt.jsx';
import {prefillAcceptedSettings} from './engineering-defaults.mjs';
import {LocationChoices} from './LocationChoices.jsx';
import {InlineNote} from './HelpNote.jsx';
import {ProjectChecks} from './ProjectChecks.jsx';
import {useEngineeringStatus} from './useEngineeringStatus.mjs';
import {ChatResizeHandle} from './ChatResizeHandle.jsx';
import {copyProject} from './project-copy.mjs';
import {initializeProjectIdentity} from './project-identity.mjs';
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
import {componentReviews,markComponentReviewed,applyComponentReview,editBlockRequirement} from './component-review.mjs';
import {ComponentReview} from './ComponentReview.jsx';
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
import {TerraformApplyDock,useTerraformApplyEmulation} from './TerraformApplyPanel.jsx';
import {applyNodeStates} from './terraform-apply-emulation.mjs';
import {identityToken} from './identifiers.mjs';
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
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
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
  Boxes,
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
  Volume2,
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
  Loader2,
  Minus,
  Save,
  Download,
  ExternalLink,
  Mail,
  Github,
} from "lucide-react";
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
import { fromProjectFile, parseProjectFile, toProjectFile } from "./project-file.mjs";
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
import { discoverLocalAgent, projects as projectStore, requestArchitect, requestDiagramSet } from "./local-agent.mjs";
import { EFFORT_LABEL } from "./WorkbenchDialogs.jsx";
import { pulumiScaffold } from "./pulumi.mjs";
import { zipSync, strToU8 } from "fflate";

// Each browser starts fresh; earlier projects are opened deliberately (⋯ → Open project file).
const STORAGE = "atforma-workspace-v3";
// A new project starts empty: the user describes what they want first.
import './onboarding.css';
import './chat-composer.css';
const emptyProject = () => initializeProjectIdentity({version: 1, revision: 1, name: "New project", provider: "tools", requirements: "", nodes: [], edges: []});
const MANUAL_BLOCK = {id:'manual-block',kind:'resource',provider:'tools',label:'New block',description:''};
const ALL_CATALOG = [MANUAL_BLOCK, ...CATALOG, ...UPSTREAM_CATALOG];
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
  creating: <Loader2 size={13} className="spin" />,
  applied: <Check size={13} />,
  verified: <ShieldCheck size={13} />,
  destroying: <Loader2 size={13} className="spin" />,
  gone: <Minus size={13} />,
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
  if(HOSTED)return hostedInitial().connection;
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
function shouldSaveLocalProject(project, messages) {
  return project.revision>1 || project.nodes.length>0 || !!project.brief?.application?.trim() || messages.length>1 || !!project.extensions?.designSources?.length || !!project.extensions?.pendingArchitecture;
}

function readSaved() {
  if(HOSTED)return withDerived(fromProjectFile(hostedInitial().file).project);
  try {
    const raw = localStorage.getItem(STORAGE);
    const p = validateImport(raw ? JSON.parse(raw) : emptyProject());
    return withDerived(initializeProjectIdentity(p));
  } catch {
    return validateImport(emptyProject());
  }
}

function Palette({ onAdd, onClose, disabled, inline=false }) {
  const [query, setQuery] = useState(""),
    [provider, setProvider] = useState("all"),
    [scope, setScope] = useState("all");
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
    <div className={inline?"studio-block-palette":"palette"} role={inline?"region":"dialog"} aria-label="Add block">
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
        {!inline&&<button type="button" className="icon" aria-label="Close component picker" title="Close component picker" onClick={onClose}><X size={16}/></button>}
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
            aria-label={item === MANUAL_BLOCK ? "Blank block" : undefined}
            draggable={!disabled}
            disabled={disabled}
            onDragStart={(e) => e.dataTransfer.setData("application/atforma-block", item.id)}
            onClick={() => onAdd(item)}
          >
            {React.createElement(KIND_ICON[item.kind] || Cloud, { size: 15 })}
            <span>{item === MANUAL_BLOCK ? "Blank block" : item.label}</span>
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

function BlockDetail({ project, node, run, probe, busy, reviewItems, onReviewConfirm, onReviewDiscuss, onReviewQuestion, onReviewResolve, onRequirementSave, onWorkModelChange, onChange, onRemove, onOpen, onBack,onSpec,onDraft,onInterface,onSaveInterface,onPrepareSources,onSystemDiagrams,renderComments,session }) {
  const hasSpecKit = node.data.kind !== "note";
  const [tab, setTab] = useState(hasSpecKit ? "spec-kit" : "overview");
  const activeTab = hasSpecKit ? tab : "overview";
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
        <button className="back" onClick={onBack} aria-label="Back one level">
          <ArrowLeft size={15} /><kbd>Esc</kbd>
        </button>
        {hasSpecKit && <div className="block-detail-tabs" role="tablist" aria-label="Block detail views"
          onKeyDown={event => {
            if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
            event.preventDefault();
            const next = event.key === "Home" ? "overview" : event.key === "End" ? "spec-kit" : activeTab === "overview" ? "spec-kit" : "overview";
            setTab(next);
            event.currentTarget.querySelector(`#block-tab-${next}`)?.focus();
          }}>
          {[["overview", "Overview"], ["spec-kit", "Block Spec Kit"]].map(([id, label]) =>
            <button key={id} type="button" id={`block-tab-${id}`} role="tab" aria-selected={activeTab === id}
              aria-controls={`block-panel-${id}`} tabIndex={activeTab === id ? 0 : -1} onClick={() => setTab(id)}>{label}</button>)}
        </div>}
        {onSystemDiagrams&&<button type="button" className="btn" onClick={onSystemDiagrams}>System diagrams</button>}
      </div>
      {hasSpecKit && <BlockHierarchy nodes={project.nodes} node={node} busy={busy} onOpen={onOpen}
        onReparent={parentBlockId => set({parentBlockId})}/>}
      <div className="block-detail-overview" role={hasSpecKit ? "tabpanel" : undefined} id="block-panel-overview"
        aria-labelledby={hasSpecKit ? "block-tab-overview" : undefined} hidden={activeTab !== "overview"}>
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
            maxLength={hasSpecKit ? 150 : 16000}
            onChange={(e) => set({ label: e.target.value })}
          />
        </div>
        {hasSpecKit && <div className="fields manual-block-fields">
          <label>Block symbol
            <select aria-label="Block symbol" value={node.data.symbol || ''} disabled={busy} onChange={e=>set({symbol:e.target.value || undefined})}>
              <option value="">Automatic</option>
              {Object.entries(BLOCK_SYMBOLS).map(([id, name]) => <option key={id} value={id}>{name}</option>)}
            </select>
          </label>
          <label className="field-wide">Description
            <textarea aria-label="Description" value={node.data.description || ''} maxLength={16000} disabled={busy} onChange={e=>set({description:e.target.value})}/>
          </label>
        </div>}
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
          <p className="muted">{"Not run yet."}</p>
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
      </div>
      {hasSpecKit && <div className="block-build-spec" role="tabpanel" id="block-panel-spec-kit"
        aria-labelledby="block-tab-spec-kit" hidden={activeTab !== "spec-kit"}>
        <BlockBuildSpec project={project} node={node} busy={busy} onOpen={onOpen} onDraft={onDraft} renderComments={renderComments}
          onInterface={onInterface} onSaveInterface={onSaveInterface} onSaveSpec={buildSpec=>{
            toProjectFile({...project,nodes:project.nodes.map(block=>block.id===node.id?{...block,data:{...block.data,buildSpec}}:block)});
            set({buildSpec});
          }} onPrepareSources={onPrepareSources} session={session}/>
      </div>}
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
  introduction: true,
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


function readChatView(id){try{const value=JSON.parse(localStorage.getItem('atmem-chat-view:'+id)||'null');return value&&Number.isSafeInteger(value.start)&&value.start>=0&&Array.isArray(value.turnIds)?value:{start:0,turnIds:[]};}catch{return {start:0,turnIds:[]};}}
const pricingSignature=p=>JSON.stringify([p.id,p.estimate?.projectSize||'small',p.estimate?.usage,p.facts,p.decisions?.filter(d=>d.status==='Accepted'&&['cloud.region','data.country'].includes(d.subject)),[...storageNodes(p),...lambdaNodes(p),...googleNodes(p)].map(n=>[n.id,n.data.provider,n.data.service,n.data.config])]);
function App() {
  const [starOffer,setStarOffer]=useState(0);
  const [introOpen,setIntroOpen]=useState(false),[voiceOpenRequest,setVoiceOpenRequest]=useState(0);
  const [project, setProject] = useState(()=>!HOSTED&&new URL(location.href).searchParams.get('example')==='1'&&!projectIdFromUrl(location.href)?readyExample():readSaved());
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
        return localStorage.getItem("atforma-draw-live") === "on";
      } catch {
        return false;
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
    [modal, setModal] = useState(null),
    [menu, setMenu] = useState(false),
    [palette, setPalette] = useState(false),
    [issuesOpen, setIssuesOpen] = useState(false),
    [chatOpen, setChatOpen] = useState(()=>!window.matchMedia('(max-width:900px)').matches),
    [theme, setTheme] = useState(savedTheme),
    [environment, setEnvironment] = useState("staging"),
    [storageError, setStorageError] = useState(false),
    [view, setView] = useState("diagram"),
    [probe, setProbe] = useState(null),
    [snapshot, setSnapshot] = useState(null),
    [measured] = useState({});
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
  const sessionRef=useRef(session),sessionProbe=useRef(null);
  sessionRef.current=session;
  const [buildRequest,setBuildRequest]=useState(()=>project.extensions?.pendingArchitecture||null);
  useEffect(()=>setBuildRequest(project.extensions?.pendingArchitecture||null),[project.id]);
  const [memorySync,setMemorySync]=useState(null);
  const currentMemory=memorySync?.projectId===project.id?memorySync:null;
  const memoryLabel=!session?'AtMem memory':currentMemory?.enabled===false?'AtMem off':currentMemory?.status==='unavailable'?'AtMem unavailable':currentMemory?.pending>0||currentMemory?.status==='sync_failed'?'AtMem sync pending':currentMemory?.status==='ready'?'AtMem on':'AtMem memory';
  const buildView=false;
  const hasDesign=hasArchitectureDesign(project);
  const modelLinkIssues=useMemo(()=>mode==='review'?architectureConsistency(project).issues.filter(issue=>issue.modelElementId||issue.caseId):[],[project,mode]);

  const [libraryCollapsed,setLibraryCollapsed]=useState(()=>window.matchMedia('(max-width:700px)').matches);
  const [openDiagramPicker,setOpenDiagramPicker]=useState(false);
  const [openSpecOnEntry,setOpenSpecOnEntry]=useState(false);
  const [openMermaidOnEntry,setOpenMermaidOnEntry]=useState(false);
  const [entryPage,setEntryPage]=useState(null);
  const [studioTab,setStudioTab]=useState('Shapes');
  const [extraBoardTools,setExtraBoardTools]=useState(false);
  const [librarySlot,setLibrarySlot]=useState(null),[pageError,setPageError]=useState('');
  function showBlockLibrary(){
    if(drawingStudio){setStudioTab('Blocks');setPalette(false);}
    else setPalette(true);
  }
  function selectStudioBlock(id){
    setMode('design');setDesignView('board');setLevel('flow');setNestedScope('*');setFocus(null);
    setPicked(new Set());setSelected(id);setBoardRecord(id);
    setTimeout(()=>fitView({nodes:[{id}],maxZoom:1.1,padding:.18}),100);
  }
  function openDrawingPage(key){
    if(key==='board'){setMode('design');setDesignView('board');setLevel('flow');return;}
    openSystemDiagrams();
    if(key.startsWith('system/'))setDesignView('system-model-legacy');
    if(key.startsWith('engineering/'))setDesignView('engineering-page');
    setEntryPage(key.substring(key.indexOf('/')+1));
  }
  function openSystemDiagrams(){setStudioTab('Pages');setOpenSpecOnEntry(false);setEntryPage(null);setOpenDiagramPicker(false);setOpenMermaidOnEntry(false);setMode('design');setDesignView('system-diagrams');setChatOpen(false);}
  function createArchitectureDiagram(){
    openSystemDiagrams();
    setOpenDiagramPicker(true);
    setStudioTab('Pages');
    setPageError('');
  }
  function createStudioPage(kind,name,starting,scope){
    try{
      const saved=project.extensions?.architectureDiagrams;
      const result=diagramFromSelection(saved||emptyDiagramModel(),kind,name,starting,scope);
      saveArchitectureDiagrams(result.model,saved);setPageError('');setStudioTab('Shapes');
      openDrawingPage('view/'+result.view.id);
    }catch(error){setPageError(error.message);}
  }
  function insertMermaidDiagram(){openSystemDiagrams();setOpenMermaidOnEntry(true);}
  const [boardProgress,setBoardProgress]=useState(false);
  const [sourceBatch,setSourceBatch]=useState(null);
  const sourceDocuments=project.extensions?.designSources||[];
  const currentSourceBatch=sourceBatch?.owner===project.id?sourceBatch:null;
  useEffect(()=>setBoardProgress(false),[project.id]);
  function showSourceBoard(){
    setMode('design');
    setDesignView('board');
    setLevel('flow');
  }
  const nativeDesignEnabled=!!session?.engineeringEnabled&&!HOSTED;
  const [nestedScope,setNestedScope]=useState(()=>preferredNestedScope(project));
  useEffect(()=>setNestedScope(preferredNestedScope(project)),[project.id]);
  function startArchitecture(sources=projectRef.current.extensions?.designSources,live=sessionRef.current) {
    if (!live?.engineeringEnabled||HOSTED) return;
    if (!sources?.length) { requirementsInput.current.click(); return; }
    if (sources===projectRef.current.extensions?.designSources&&['running','starting'].includes(engineeringStatus?.state)){
      showSourceBoard();return;
    }
    const current=projectRef.current;
    const request={id:crypto.randomUUID(),projectId:current.id,intent:'design',createdAt:new Date().toISOString()};
    const sourceTitle=/^(New project|Untitled.*)$/i.test(current.name||'')?sources[0].name.replace(/\.[^.]+$/,''):current.name;
    const next={...current,name:sourceTitle,extensions:{...current.extensions,designSources:sources,diagramCatalogueRequired:true,pendingArchitecture:request,...(/^(New project|Untitled.*)$/i.test(current.name||'')?{sourceProvisionalTitle:sourceTitle}:{})}};
    toProjectFile(next);
    updateEngagement(next);
    setBuildRequest(request);
    showSourceBoard();
    if(connection?.provider!=='codex'||!connection.model||connection.model==='default'||!connection.effort)showConnections();
  }
  async function readArchitectureDraft(artifact, sessionId) {
    const current=projectRef.current;
    const basis=canvasBasis(current);
    const saved=await saveEngineeringProject(current.id,current);
    const report=await engineeringCall(session,'delivery',{projectId:current.id});
    if(report.relation!=='matches_saved_design'||report.savedFileSha256!==saved.sha256
      ||report.artifact?.id!==artifact.id||report.session?.id!==sessionId)throw Error('This Codex package belongs to another design revision.');
    const blob=await verifiedEngineeringDownload(session,{projectId:current.id,sessionId,artifactId:artifact.id},artifact);
    const bytes=new Uint8Array(await blob.arrayBuffer());
    if(canvasBasis(projectRef.current)!==basis)throw Error('The current design changed during canvas review.');
    try{
      const proposal=canvasProposal(projectRef.current,bytes,artifact.id,report.context?.sha256,report.sourceFigureEvidence);
      toProjectFile({...proposal.next,...canvasProposalRecords(current,proposal)});
      proposal.quality.capturedDiagrams=await validateCapturedDiagrams(proposal.designDocuments);
      proposal.quality.gates.authoredDiagramSyntax=true;
      return proposal;
    }
    catch(error){error.canvasDraftInvalid=!error.validationUnavailable&&!error.hostStorageBound;throw error;}
  }
  async function previewArchitectureDraft(artifact, sessionId) {
    const proposal=await readArchitectureDraft(artifact,sessionId);
    setSelected(null);setLevel('flow');setFocus(null);setMode('design');setDesignView('board');
    setStudioTab(proposal.architectureDiagrams?'Pages':'Layers');
    if(drawLive)applyProposal(proposal,{live:true});
    else setPending(proposal);
    refit();
  }
  async function receiveDesignSources(files, owner, live=sessionRef.current) {
    const batch={owner,names:files.map(file=>file.name)};
    showSourceBoard();
    setSourceBatch(batch);
    try{
      const received=await readAttachments(files);
      await saveEngineeringProject(owner);
      if(projectRef.current.id!==owner)return;
      const response=await fetch('/api/design-sources',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${live.token}`},
        body:JSON.stringify({projectId:owner,attachments:received.map(({name,mime,data})=>({name,mime,data}))})});
      const result=await response.json();
      if(!response.ok)throw Error(typeof result.detail==='string'?result.detail:'The source document could not be read.');
      if(projectRef.current.id!==owner)return;
      const prior=projectRef.current.extensions?.designSources||[];
      startArchitecture([...new Map([...prior,...result.sources].map(source=>[source.sha256,source])).values()],live);
      setSourceBatch(null);
    }catch(error){
      if(projectRef.current.id===owner)setSourceBatch({...batch,error:error.message});
      throw error;
    }
  }

  useEffect(()=>{saveCanvasView(project,{level,focus,selected,positions:topologyPositions});},[project.id,level,focus,selected,topologyPositions]);
  const emulation=useEmulation(project,environment,session);
  // Terraform apply emulation: one run shared by the Board dock and the Terraform view.
  const applyKey=useMemo(()=>JSON.stringify({projectId:project.id,files:terraformSketch(project,environment)}),[project,environment]);
  const applyEmulation=useTerraformApplyEmulation(project,environment,session,applyKey);
  const applyDiagram=useMemo(()=>applyEmulation.running||applyEmulation.report?applyNodeStates(project.nodes.map(n=>n.id),identityToken,applyEmulation.events,applyEmulation.report,applyEmulation.running):{states:{},counts:{}},[project.nodes,applyEmulation.running,applyEmulation.report,applyEmulation.events]);
  const [applyDockOpen,setApplyDockOpen]=useState(false);
  const emulationWorking=emulation.running||(agentBusy&&!!emulation.result);
  const [pricingState,setPricingState]=useState({busy:false,errors:[]});
  const [generationPending,setGenerationPending]=useState(false);
  const [engineeringError,setEngineeringError]=useState(null);
  const [engineeringActivity,setEngineeringActivity]=useState(null);
  const receiveEngineeringActivity=useCallback(value=>setEngineeringActivity({owner:project.id,...value}),[project.id]);
  const [checking,setChecking]=useState(false),[checkReceipt,setCheckReceipt]=useState(null);
  const [serverSavedId,setServerSavedId]=useState(null);
  const canObserveEngineering=serverSavedId===project.id||!!project.extensions?.architectureWork||sourceDocuments.length>0;
  const engineeringStatus=useEngineeringStatus(session,project.id,canObserveEngineering,serverSavedId);
  const reviewSaving=useRef(null);
  useEffect(()=>{
    if(mode!=='review'||!session?.engineeringEnabled||canObserveEngineering||!project.nodes.length||reviewSaving.current===project.id)return;
    reviewSaving.current=project.id;
    saveEngineeringProject(project.id).catch(error=>{reviewSaving.current=null;notify(error.message);});
  },[mode,session?.engineeringEnabled,canObserveEngineering,project.id]);
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
  const [emulationOpen,setEmulationOpen]=useState(false);
  const consultationAttempts = useRef(new Set());
  const agentAbort = useRef(null);
  const messageInput = useRef(null);
  const hasIntroduction=messages[0]?.role==='assistant'&&(messages[0].introduction===true||messages[0].text==='What would you like to build?'||messages[0].text.startsWith('Good to see you again'));
  const idleChat=hasIntroduction&&!introOpen&&architectureChatEntries(project,messages).length===1;
  useEffect(()=>{
    const resize=()=>{const field=messageInput.current;if(field){field.style.height='32px';field.style.height=Math.min(120,Math.max(32,field.scrollHeight))+'px';}};
    resize();window.addEventListener('resize',resize);return()=>window.removeEventListener('resize',resize);
  },[input,chatWidth,chatOpen]);
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
  const boardApi=useRef(null);
  const [boardRecord,setBoardRecord]=useState(null),[boardPane,setBoardPane]=useState('Properties');
  useEffect(()=>setBoardPane('Properties'),[boardRecord]);
  const screenToFlowPosition=useCallback(point=>boardApi.current?.position({clientX:point.x,clientY:point.y})||point,[]);
  const fitView=useCallback(options=>boardApi.current?.fit(options),[]);
  const zoomIn=()=>boardApi.current?.zoom(.15);
  const zoomOut=()=>boardApi.current?.zoom(-.15);
  const [attention, setAttention] = useState(null);
  const attentionRef = useRef(null);
  const fileRef = useRef(),fileImportAsCopy=useRef(false),requirementsInput=useRef();
  const menuTrigger=useRef(null),projectMenu=useRef(null);
  const [savingProject,setSavingProject]=useState(false);
  const [runningComment,setRunningComment]=useState(null);
  const commentQueue=useRef({working:false,activeId:null,items:[]});

  useEffect(()=>{
    if(!menu)return;
    const panel=projectMenu.current;
    panel.querySelector('[role="menuitem"]:not(:disabled)')?.focus();
    function dismiss(event){
      if(!panel.contains(event.target)&&!menuTrigger.current?.contains(event.target))setMenu(false);
    }
    document.addEventListener('pointerdown',dismiss);
    return ()=>document.removeEventListener('pointerdown',dismiss);
  },[menu]);
  function navigateProjectMenu(event){
    const items=[...projectMenu.current.querySelectorAll('[role="menuitem"]:not(:disabled)')];
    const index=items.indexOf(document.activeElement);
    switch(event.key){
      case 'Escape':
        event.preventDefault();
        event.stopPropagation();
        setMenu(false);
        menuTrigger.current?.focus();
        return;
      case 'Tab':
        setMenu(false);
        return;
      case 'Home': items[0]?.focus(); break;
      case 'End': items.at(-1)?.focus(); break;
      case 'ArrowDown': items[(index+1)%items.length]?.focus(); break;
      case 'ArrowUp': items[(index+items.length-1)%items.length]?.focus(); break;
      default: return;
    }
    event.preventDefault();
    event.stopPropagation();
  }
  const attachmentInput=useRef();
  const [attachments,setAttachments]=useState([]),[attachmentError,setAttachmentError]=useState(''),[readingAttachments,setReadingAttachments]=useState(false);
  const attachmentReadLock=useRef(false);
  async function attachFiles(files){
    const selectedFiles=[...files];
    if(!selectedFiles.length||attachmentReadLock.current)return;
    attachmentReadLock.current=true;const projectAtStart=projectRef.current.id;
    setReadingAttachments(true);setAttachmentError('');
    try {
      const live=sessionRef.current||await refreshSession();
      if(live?.engineeringEnabled&&!HOSTED){
        await receiveDesignSources(selectedFiles,projectAtStart,live);return;
      }
      const next=await readAttachments(selectedFiles,attachments);
      if(projectRef.current.id===projectAtStart)setAttachments(previous=>[...previous,...next]);
    }
    catch(error){setAttachmentError(error.message);}
    finally{attachmentReadLock.current=false;setReadingAttachments(false);}
  }
  const chatScroll = useChatScroll(project.id,chatOpen);
  const latestArchitectureTurn=Array.isArray(project.extensions?.architectureActivity?.turns)?project.extensions.architectureActivity.turns.at(-1):null;
  const runToken = useRef(0);
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
    (nodes, minZoom=1) => setTimeout(() => {
      if (!attentionRef.current) fitView({ padding, minZoom, maxZoom: 1.1, duration: 200, ...(nodes ? { nodes } : {}) });
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

  function showConnections(){if(HOSTED){void hostedCall('account').catch(error=>notify(error.message));return;}setModal('connections');}
  const refreshSession = useCallback(async () => {
    if(sessionProbe.current)return sessionProbe.current;
    const lookup=discoverLocalAgent().then(next=>{
      sessionRef.current=next;
      setSession(next);
      if(HOSTED&&next.defaultConnection)setConnection(current=>current?.model===next.defaultConnection.model&&current?.effort===next.defaultConnection.effort?current:next.defaultConnection);
      return next;
    }).catch(()=>{
      sessionRef.current=null;
      setSession(null);
      return null;
    }).finally(()=>{sessionProbe.current=null;});
    sessionProbe.current=lookup;
    return lookup;
  }, []);
  useEffect(()=>{if(HOSTED&&session?.token)void hostedCall('ready').catch(()=>{});},[session?.token]);
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
    const parent = projectRef.current.nodes.find(node => node.id === selected)?.data.parentBlockId;
    if (level === "block" && parent) openBlock(parent);
    else if (level === "block") goFlow(focus);
    else if(nestedScope&&nestedScope!=='*')exploreSubsystem(projectRef.current.nodes.find(node=>node.id===nestedScope)?.data.parentBlockId||null);
    else if (focus) goFlow(null);
  }

  useEffect(() => {
    function keys(e) {
      const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName) || document.activeElement?.isContentEditable;
      if(document.querySelector('.architecture-dialog[open]'))return;
      if (['system-diagrams','system-model-legacy','engineering-page'].includes(designView)&&e.key==='Escape'&&!modal&&!menu&&!typing){setDesignView(designView==='system-model-legacy'?'system-diagrams':'board');return;}
      if (e.key === "Escape") {
        if (modal || menu || palette || issuesOpen) {
          if (!(modal === "welcome" && !connection)) setModal(null);
          setMenu(false);
          setPalette(false);
          setIssuesOpen(false);
        } else if (agentAbort.current) agentAbort.current.abort();
        else if (!typing&&!buildView) goUp();
      }
      if(['system-diagrams','system-model-legacy','engineering-page'].includes(designView)){
        if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'&&!typing){
          e.preventDefault();
          if(e.shiftKey)redo();else undo();
        }
        return;
      }
      if(buildView)return;
      if (onBoard && level !== "block" && !typing && !modal && !palette && !window.getSelection()?.toString() && (e.ctrlKey || e.metaKey)) {
        if (e.key.toLowerCase() === "c" && (selected || picked.size)) {
          e.preventDefault();
          copySelection();
        }
        if (e.key.toLowerCase() === "v" && boardClipboard?.projectId === project.id) {
          e.preventDefault();
          pasteSelection();
        }
      }
      if (e.key === "/" && !typing) {
        e.preventDefault();
        showBlockLibrary();
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "a" && !typing && mode === "design") {
        e.preventDefault();
        setLevel("flow");
        setPicked(new Set((nested.projected?nested.nodes:projectRef.current.nodes).map((n) => n.id)));
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z" && !typing && !modal) {
        e.preventDefault();
        if (e.shiftKey) redo(); else undo();
      }
      if ((e.key === "Delete" || e.key === "Backspace") && !typing && !nested.projected && picked.size > 1) {
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

  // New blocks land in the middle of the visible board, nudged so they don't stack.
  function centre(count) {
    const box = document.querySelector('.board-surface .drawio-canvas')?.getBoundingClientRect();
    const at = box
      ? screenToFlowPosition({ x: box.left + box.width / 2, y: box.top + box.height / 2 })
      : { x: 90, y: 90 };
    return { x: at.x - 105 + (count % 4) * 24, y: at.y - 29 + (count % 4) * 24 };
  }
  function noteText(id, text) {
    const p = projectRef.current;
    commit({ ...p, nodes: p.nodes.map((n) => (n.id === id ? { ...n, data: { ...n.data, label: text.slice(0, 150), description: text.slice(0, 500) } } : n)) });
  }
  function addDrawingTool(tool,position){
    if(busy||previewing||agentBusy||pending)return;
    if(tool.startsWith('element:')){
      const item=ALL_CATALOG.find(row=>'element:'+row.id===tool);
      if(item)addComponent(item,position);
      return;
    }
    if(!Object.hasOwn(drawioShapes,tool))return;
    const current=projectRef.current;
    const id='shape-'+crypto.randomUUID();
    const node={id,type:'resource',position:position||centre(current.nodes.length),data:{
      kind:'note',provider:'tools',drawingShape:tool,label:drawioShapes[tool],description:'',
      config:{region:'',classification:'Internal',timeout:5000},origin:'proposed',
    }};
    commit({...current,nodes:[...current.nodes,node]});
    if(nested.projected)setNestedScope('*');
    setLevel('flow');setFocus(null);setSelected(id);setPicked(new Set());setBoardRecord(id);
  }
  function addNote(position, attachTo = null) {
    const p = projectRef.current;
    const id = `note-${crypto.randomUUID().slice(0, 8)}`;
    const note = { id, type: "resource", position, data: { label: "", kind: "note", provider: "tools", description: "", config: { region: "", classification: "Internal", timeout: 5000 }, origin: "proposed" } };
    commit({ ...p, nodes: [...p.nodes, note], edges: attachTo ? [...p.edges, { id: `${id}-${attachTo}`, source: id, target: attachTo, type: "smoothstep", label: "" }] : p.edges });
    setBoardRecord(id);
    setModal('edit-board-note');
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
    commit({ ...p, nodes: removeBlocks(p.nodes, ids), edges: p.edges.filter((e) => !ids.has(e.source) && !ids.has(e.target)) });
    setPicked(new Set());
    setSelected(null);
  }
  // What the user changed by hand since the model last saw the board.
  // What the model has seen; starts as the board as it was when the page opened.
  const seen = useRef(null);
  if (!seen.current) seen.current = structuredClone(project);
  const paletteAt = useRef(null);
  const [boardClipboard, setBoardClipboard] = useState(null);
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
    if (busy || agentBusy || pending) return;
    const current = projectRef.current;
    const id = crypto.randomUUID();
    const parentBlockId = nested.scope || undefined;
    const next = {
      ...current,
      nodes: [...current.nodes, {id, type:"resource", position:position || centre(current.nodes.length),
        data:{...item, parentBlockId,
          config:{region:"To be selected", classification:"Internal", timeout:5000}, origin:"proposed"}}],
    };
    try { toProjectFile(next); } catch (error) { notify(error.message); return; }
    commit(next);
    setPicked(new Set());
    setSelected(id);
    setPalette(false);
    paletteAt.current = null;
    if (item === MANUAL_BLOCK) openBlock(id);
    else if (level !== "flow") goFlow(null);
    notify(`${item.label} added.`);
  }

  function copySelection(ids = picked.size > 1 ? picked : selected ? [selected] : picked) {
    try {
      const contents = copyBoardItems(projectRef.current, ids);
      if (!contents) return;
      setBoardClipboard(contents);
      notify(`Copied ${contents.nodes.length} ${contents.nodes.length === 1 ? 'item' : 'items'}.`);
    } catch (error) { notify(error.message); }
  }

  function pasteSelection(position) {
    if (!boardClipboard || busy || agentBusy || pending) return;
    const current = projectRef.current;
    try {
      const {nodes, edges} = pasteBoardItems(current, boardClipboard, position || centre(current.nodes.length), nested.scope || undefined);
      const next = {...current, nodes:[...current.nodes,...nodes], edges:[...current.edges,...edges]};
      validateImport(next);
      toProjectFile(next);
      commit(next);
      if (level !== "flow") goFlow(null);
      setPicked(new Set(nodes.map(node => node.id)));
      setSelected(nodes.length === 1 ? nodes[0].id : null);
      notify(`Pasted ${nodes.length} ${nodes.length === 1 ? 'item' : 'items'}.`);
    } catch (error) { notify(error.message); }
  }

  function saveBlockInterface(edge) {
    const current = projectRef.current;
    const edges = current.edges.some(item => item.id === edge.id)
      ? current.edges.map(item => item.id === edge.id ? edge : item)
      : [...current.edges, edge];
    const next = {...current, edges};
    validateImport(next);
    toProjectFile(next);
    commit(next);
  }

  function updateNode(node) {
    commit({ ...project, nodes: project.nodes.map((n) => (n.id === node.id ? node : n)) });
  }
  function removeNode(id) {
    commit({
      ...project,
      nodes: removeBlocks(project.nodes, new Set([id])),
      edges: project.edges.filter((e) => e.source !== id && e.target !== id),
    });
    setSelected(null);
    goFlow(focus);
  }
  function restoreDesign(snapshot) {
    const restored=keepEngagement(snapshot,projectRef.current);
    const extensions={...restored.extensions};
    if(snapshot.extensions?.architectureDiagrams)extensions.architectureDiagrams=snapshot.extensions.architectureDiagrams;
    else delete extensions.architectureDiagrams;
    if(snapshot.extensions?.drawingLayouts)extensions.drawingLayouts=snapshot.extensions.drawingLayouts;
    else delete extensions.drawingLayouts;
    if(snapshot.extensions?.systemModel)extensions.systemModel=snapshot.extensions.systemModel;
    else delete extensions.systemModel;
    commit({...restored,extensions},false);
  }
  function saveArchitectureDiagrams(model,expected){
    validateDiagramModel(model);
    const current=projectRef.current;
    if(busy||agentBusy||pending||current.id!==project.id||current.extensions?.architectureDiagrams!==expected){
      throw Error('The project changed. Try again from the current diagram.');
    }
    const next={...current,extensions:{...current.extensions,architectureDiagrams:model}};
    toProjectFile(next);
    commit(next);
  }
  async function draftArchitectureDiagrams({specification,useProject,files,resume},signal,onProgress){
    const current=projectRef.current;
    const projectContext=JSON.stringify({
      name:current.name,
      ...(useProject?{requirements:current.requirements,needs:current.needs,decisions:current.decisions,
        sources:current.extensions?.designSources?.map(({name,text,mode})=>({name,text,mode})),
        components:current.nodes.filter(node=>node.data.kind!=='note').map(({id,data})=>({id,
          label:data.label,service:data.service,description:data.description,origin:data.origin,buildSpec:data.buildSpec})),
        connections:current.edges.map(({id,source,target,label,interfaceSpec})=>({id,source,target,label,interfaceSpec})),
      }:{}),existingDiagramModel:current.extensions?.architectureDiagrams,
    });
    if(!specification.trim()&&!files.length&&!useProject)throw Error('Add a solution specification.');
    if(projectContext.length>1200000)throw Error('Project context exceeds 1,200,000 characters. Generate from a focused specification.');
    const model=await requestDiagramSet({session:sessionRef.current,connection,specification,projectContext,files,resume,signal,onProgress});
    return validateDiagramModel(model,{complete:true});
  }
  function saveDiagramModel(model) {
    validateSystemModel(model);
    const current=projectRef.current;
    const next={...current,extensions:{...current.extensions,systemModel:model}};
    toProjectFile(next);
    commit(next);
  }
  function undo() {
    if (!history.length || busy || agentBusy) return;
    const previous = history.at(-1);
    setFuture((f) => [...f.slice(-29), structuredClone(projectRef.current)]);
    setHistory((h) => h.slice(0, -1));
    // Undo takes back the design, never what the user has told us since.
    restoreDesign(previous);
    setSelected(null);
    setPending(null);
    notify("Board change undone. Redo restores it.");
  }
  function redo() {
    if (!future.length || busy || agentBusy) return;
    const next = future.at(-1);
    setHistory((h) => [...h.slice(-29), structuredClone(projectRef.current)]);
    setFuture((f) => f.slice(0, -1));
    restoreDesign(next);
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
      const content = await file.text();
      const raw = JSON.parse(content);
      if (raw.format || raw.version === 1) {
        const { project: opened, migrated, from } = parseProjectFile(content);
        if(HOSTED){
          await saveEngineeringProject(projectRef.current.id);
          const imported=await hostedCall('import-project',{file:toProjectFile(opened)});
          loadDesign(fromProjectFile(imported.file).project,{own:true});
        }else loadDesign(fileImportAsCopy.current?copyProject(opened,crypto.randomUUID()):opened, { own: true });
        if(fileImportAsCopy.current)notify("New project created from the saved design. The original is preserved.");
        else if(migrated)notify(`Project opened and upgraded from ${from}.`);
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
    if(next.extensions?.architectureDiagrams?.views.length&&!next.nodes.some(node=>node.data.kind!=='note')){
      openSystemDiagrams();
    }else{
      setMode('design');
      setDesignView('board');
    }
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
        const questions = p.openQuestions || [];
        const linked = q?.componentId && origin !== 'block-review' && p.nodes.some(node=>node.id===q.componentId)
          && !questions.some(row=>row.question.trim()===q.question.trim()&&row.links.includes(q.componentId));
        updateEngagement({...p,openQuestions:linked?[...questions,newQuestion({question:q.question,links:[q.componentId]})]:questions,lastAsked:q?{id:'architect-question',topic:q.topic||'',question:q.question,why:q.why,beginner:q.example||''}:null,extensions:{...p.extensions,activeConsultation:{hasQuestion:!!q}}});
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
    if (proposal.baseRevision !== current.revision || proposal.sourceBasis && proposal.sourceBasis!==canvasBasis(current)) {
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
    const next={...keepEngagement(proposal.next,current),decisions:[...(current.decisions||[]),decision],
      conceptSig:quiet?conceptSignature(proposal.next):null};
    if(proposal.sourceRequirements){
      Object.assign(next,canvasProposalRecords(current,proposal));
      const applied=withDerived({...next,revision:current.revision+1});
      next.extensions.architectureDraftQuality={...proposal.quality,appliedBasis:appliedQualityBasis(applied)};
    }
    commit(next);
    if(proposal.sourceRequirements)setNestedScope(preferredNestedScope(next));
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
        text: `Architecture updated to revision ${current.revision+1}.${summary?'\n\n'+summary:''}`,
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
    if(proposal.sourceRequirements&&!live)setDesignView('overview');
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
  // Live Terraform apply emulation states take precedence on the blocks they touch.
  const liveStates = useMemo(() => ({ ...runStates, ...applyDiagram.states }), [runStates, applyDiagram]);
  const system = useMemo(() => systemView(shown, liveStates), [shown, liveStates]);
  const nested = useMemo(()=>nestedCanvas(shown,nestedScope),[shown,nestedScope]);
  const nestedPositions = useMemo(()=>nested.projected?arrangeOverview(nested,measured,nested.nodes.length<=5?'TB':'LR'):{},[nested,measured]);
  const nodesReady=shown.nodes.length>0;
  const nestedViewKey=nested.nodes.map(node=>node.id).join('|');
  useEffect(()=>{
    if(!nested.projected||!nodesReady||mode!=='design'||designView!=='board'||level!=='flow')return;
    const timer=setTimeout(()=>fitView({padding:0.1,minZoom:1,maxZoom:1.1,duration:150}),350);
    return()=>clearTimeout(timer);
  },[nested.projected,nested.scope,nestedViewKey,nestedPositions,nodesReady,mode,designView,level,studioTab,chatWidth,fitView]);
  function exploreSubsystem(id){setNestedScope(id);setSelected(null);setPicked(new Set());setLevel('flow');refit();}
  const wireClass = (source) =>
    `wire ${liveStates[source] === "failed" ? "wire-failed" : ["passed","verified"].includes(liveStates[source]) ? "wire-passed" : ["creating","applied"].includes(liveStates[source]) ? "wire-live" : ""}`;
  const canvasNodes =
    level === "system"
      ? system.nodes.map((n) => ({ ...n, position:topologyPositions[n.id]||n.position, data:{...n.data,onExplore:()=>n.data.blocks.length===1?reviewBlock(n.data.blocks[0]):goFlow(n.data.layer),onReview:()=>reviewBlock(blockReviews.find(r=>n.data.blocks.includes(r.id)&&r.issues.length)?.id||n.data.blocks[0]),reviewSummary:{reviewed:blockReviews.filter(r=>n.data.blocks.includes(r.id)&&r.status==='reviewed').length,issues:blockReviews.filter(r=>n.data.blocks.includes(r.id)).flatMap(r=>r.issues)}}, measured: measured[n.id], className: previewing ? "preview" : "" }))
      : nested.nodes.map((n) => ({
          ...n,
          position:nestedPositions[n.id]||n.position,
          type: n.data.kind === "note" ? "note" : n.type,
          measured: measured[n.id],
          className: `${previewing ? "preview" : ""} ${attention?.nodes.includes(n.id) ? "diagram-attention" : ""}`,
          selected: n.id === selected || picked.has(n.id),
          data: { ...n.data, childCount:n.id===nested.scope?0:shown.nodes.filter(child=>child.data.parentBlockId===n.id).length,onExploreChildren:()=>exploreSubsystem(n.id),blockReview:blockReviews.find(r=>r.id===n.id), onReview:()=>reviewBlock(n.id), onText: noteText, runState: liveStates[n.id], runCount: applyDiagram.counts[n.id], dim: (focusBlocks && !focusBlocks.has(n.id)) || (testing && !n.data.poc && n.data.kind !== "resource" && project.nodes.some((x) => x.data.poc)) },
        }));
  const canvasEdges =
    level === "system"
      ? system.edges.map((e) => ({ ...e, className: wireClass(e.data.sources[0]), markerEnd: { type: "arrowclosed", width: 14, height: 14 } }))
      : nested.edges.map((e) => ({
          ...e,
          className: `${previewing ? "preview" : ""} ${attention?.edges.includes(e.id) ? "diagram-attention" : ""} ${wireClass(e.source)} ${focusBlocks && !(focusBlocks.has(e.source) || focusBlocks.has(e.target)) ? "dim" : ""}`,
          animated: (busy && liveStates[e.source] === "passed") || (applyEmulation.running && ["creating","applied","verified"].includes(liveStates[e.source])),
          markerEnd: { type: "arrowclosed", width: 14, height: 14 },
        }));
  const boardLayoutKey=level==='system'?'board/system':nested.projected?'board/overview/'+(nested.scope||'root'):'board/full';
  const legacyBoardLayout=nested.projected||!shown.nodes.some(n=>n.data.parentBlockId)?project.extensions?.drawingLayouts?.pages?.board:null;
  const nativeBoard=applyDrawingLayout(boardGraph(canvasNodes,canvasEdges),project.extensions?.drawingLayouts?.pages?.[boardLayoutKey]??legacyBoardLayout);
  const boardEditable=!busy&&!previewing&&!nested.projected&&level==='flow';
  const boardItem=nativeBoard.vertices.find(row=>row.id===boardRecord)||nativeBoard.wires.find(row=>row.id===boardRecord);
  const recordNode=project.nodes.find(node=>node.id===boardRecord);
  function saveBlockProperty(recordNode,buildSpec){
    const current=projectRef.current;
    if(!recordNode||current.nodes.find(node=>node.id===recordNode.id)?.data.buildSpec!==recordNode.data.buildSpec)throw Error('The selected block changed. Reopen its properties.');
    const next={...current,nodes:current.nodes.map(node=>node.id===recordNode.id?{...node,data:{...node.data,buildSpec}}:node)};
    toProjectFile(next);commit(next);
  }
  function renderBlockProperties(id){
    const node=project.nodes.find(row=>row.id===id);
    if(!node||node.data.kind==='note')return null;
    return <BlockSpecProperties key={node.id} node={node} busy={boardToolLocked} compact
      onSave={buildSpec=>saveBlockProperty(node,buildSpec)} renderComments={renderDesignComments}/>;
  }
  function styleBoardBlock(field,color){
    const current=projectRef.current;
    if(boardToolLocked||!/^#[0-9a-f]{6}$/i.test(color))return;
    commit({...current,nodes:current.nodes.map(node=>node.id===boardRecord?{...node,data:{...node.data,[field]:color}}:node)});
  }
  function connectBoard(source,target){
    if(!boardEditable)return;
    const current=projectRef.current;
    if(source===target||current.edges.some(row=>row.source===source&&row.target===target))return;
    const id='wire-'+crypto.randomUUID();
    commit({...current,edges:[...current.edges,{id,source,target,type:'smoothstep',label:'data'}]});
    setBoardRecord(id);
  }
  function saveDrawingLayout(page,changes){
    const current=projectRef.current;let layouts=current.extensions?.drawingLayouts;
    const legacy=page.startsWith('board/overview/')||page==='board/full'&&!current.nodes.some(n=>n.data.parentBlockId);
    if(legacy&&layouts?.pages?.board&&!layouts.pages[page])layouts={...layouts,pages:{...layouts.pages,[page]:layouts.pages.board}};
    let next=updateDrawingLayout(layouts,page,changes);
    if(changes===null&&legacy&&layouts?.pages?.board)next={...next,pages:{...next.pages,[page]:{}}};
    commit({...current,extensions:{...current.extensions,drawingLayouts:next}});
  }

  function moveBoard(positions){
    const current=projectRef.current;
    const changes=new Map(positions.map(({id,x,y})=>[id,{x,y}]));
    commit({...current,nodes:current.nodes.map(row=>changes.has(row.id)?{...row,position:changes.get(row.id)}:row)});
  }
  function removeBoard(ids){
    const current=projectRef.current,selectedIds=new Set(ids);
    const removedNodes=new Set(current.nodes.filter(row=>selectedIds.has(row.id)).map(row=>row.id));
    commit({...current,nodes:removeBlocks(current.nodes,removedNodes),edges:current.edges.filter(row=>
      !selectedIds.has(row.id)&&!removedNodes.has(row.source)&&!removedNodes.has(row.target))});
    setBoardRecord(null);
    setSelected(null);
  }
  function openBoardRecord(id){
    const node=canvasNodes.find(row=>row.id===id),edge=canvasEdges.find(row=>row.id===id);
    if(edge){if(level==='system')goFlow(null);else openBlock(edge.source,edge);return;}
    if(!node)return;
    if(level==='system'){node.data.onExplore();return;}
    if(node.data.kind==='note'){setModal('edit-board-note');return;}
    if(nested.projected&&node.data.childCount&&nested.scope!==id)exploreSubsystem(id);
    else openBlock(id);
  }
  const slug = project.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "atflow";
  const exportDocument = () => {
    download(deploymentDocument(project, run), `${slug}-deployment-document.md`, "text/markdown");
    notify("Deployment document generated from the current project.");
  };
  const exportFiles = (files, suffix) => {
    download(zipSync(Object.fromEntries(Object.entries(files).map(([name, content]) => [name, typeof content === "string" ? strToU8(content) : content]))), `${slug}-r${project.revision}-${suffix}.zip`, "application/zip");
  };
  const downloadBundle = async bundle => {
    bundle=await(bundle.prepare?.()||bundle);
    if(bundle.project!==projectRef.current)throw Error('Design changed while preparing files. Download again.');
    download(zipSync(Object.fromEntries(Object.entries(bundle.files).map(([name,content])=>[name,typeof content === "string"?strToU8(content):content]))),bundle.filename,"application/zip");
    if(bundle.project?.id===projectRef.current.id)updateEngagement(acknowledgeStage(projectRef.current,'delivery'));
    notify("ZIP downloaded.");setStarOffer(value=>value+1);
  };
  const exportPack = async () => {
    try {
      notify("Preparing documents and diagram exports…");
      await downloadBundle(await outputBundle(project,run,environment,null,{session:sessionRef.current,prepareSources:prepareSourceEvidence}));
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
  useEffect(()=>{if(HOSTED)void noteHostedChange(project.id).catch(()=>{});},[project,messages]);
  // Autosave through the selected local or hosted session service.
  const binned = useRef(new Set());
  useEffect(() => {
    if (!session || binned.current.has(project.id) || (!HOSTED && !shouldSaveLocalProject(project,messages))) return;
    const bridgeVersion=HOSTED?hostedRevision(project.id):undefined;
    const t = setTimeout(async () => {
      try {
        const saved=await projectStore(session, "save", { id: project.id, file: toProjectFile(withConversation(project, messages)),...(HOSTED?{bridgeVersion}:{}) });
        if(saved.memory)setMemorySync({projectId:project.id,...saved.memory});
      } catch (error) { setMemorySync(current=>({...((current?.projectId===project.id)?current:{}),projectId:project.id,status:'sync_failed'}));notify(`Project conversation could not be saved: ${error.message}`); }
    }, 800);
    return () => clearTimeout(t);
  }, [project, messages, session?.token]);
  async function prepareSourceEvidence(expected){
    const basis=canvasBasis(expected);
    const live=sessionRef.current||await refreshSession();
    if(!live?.token)return live;
    const unchanged=()=>{if(canvasBasis(projectRef.current)!==basis)throw Error('The design changed while preparing source images. Retry the handoff.');};
    unchanged();
    // Figure authorization needs the owned saved project, not a frozen chat journal.
    // Source/manifest/pixel pins independently bind the exported snapshot.
    await saveEngineeringProject(expected.id);
    unchanged();
    return live;
  }
  async function saveEngineeringProject(owner,expected){
    const current=projectRef.current;
    if(current.id!==owner)throw Error('The project changed while opening engineering work. Return to that project before submitting its draft.');
    if(expected&&expected!==current)throw Error('The design changed before saving the handoff. Review Delivery again.');
    const conversation=messagesRef.current;
    const result=await projectStore(sessionRef.current,'save',{id:owner,file:toProjectFile(withConversation(current,conversation))});
    setServerSavedId(owner);
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
    next=initializeProjectIdentity(next);
    setIntroOpen(false);setVoiceOpenRequest(0);
    const address=new URL(window.location.href);if(address.searchParams.get('project')!==next.id){address.searchParams.delete('project');address.searchParams.delete('example');window.history.replaceState(null,'',address);}
    setBuildRequest(null);
    next = withDerived(next);
    const leaving = projectRef.current;
    if (session && !binned.current.has(leaving.id) && shouldSaveLocalProject(leaving,messages))
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
    setDesignView(next.nodes.length?"overview":"board");
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
      if(HOSTED)await saveEngineeringProject(projectRef.current.id);
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
        if (leaving.id !== id && !binned.current.has(leaving.id) && shouldSaveLocalProject(leaving,messages)) {
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
  async function newProject() {
    if(HOSTED){
      if(agentBusy||busy||intake.length)return;
      try{await saveEngineeringProject(projectRef.current.id);const {file}=await hostedCall('new-project');switchTo(fromProjectFile(file).project);setModal(null);}catch(error){notify(error.message);}
      return;
    }
    if(!busy&&!agentBusy&&!intake.length)setModal("start-over");
  }
  function createOwnProject(){
    if(HOSTED){void newProject();return;}
    switchTo(validateImport(emptyProject()));setModal(connection?null:'connections');
    requestAnimationFrame(()=>document.querySelector('input[aria-label="Project name"]')?.focus());
  }
  async function openReadyExample(){
    if(busy||agentBusy||intake.length)return;
    const example=readyExample();example.id=crypto.randomUUID();
    if(HOSTED){try{await saveEngineeringProject(projectRef.current.id);const {file}=await hostedCall('import-project',{file:toProjectFile(example)});switchTo(fromProjectFile(file).project);setModal(null);}catch(error){notify(error.message);}return;}
    switchTo(example);setModal(null);
  }
  async function binProject(id) {
    try {
      binned.current.add(id);
      await projectStore(session, "trash", { id });
      if(id===projectRef.current.id){if(HOSTED){const {file}=await hostedCall('new-project');switchTo(fromProjectFile(file).project);}else switchTo(validateImport(emptyProject()));}
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
    if(section.id!=='scope'&&document.querySelector('[data-unsaved-requirements="true"]')&&!window.confirm('Leave Requirements and discard unsaved document edits?'))return;
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
  function updateComments(owner,transform){
    const current=projectRef.current;
    if(current.id!==owner)return;
    const next={...current,extensions:{...current.extensions,designComments:transform(current.extensions?.designComments||[])}};
    toProjectFile(next);
    updateEngagement(next);
  }
  function saveDesignComment(target,value,ask,quote){
    const current=projectRef.current;
    const text=value.trim();
    if(!text||text.length>1800)throw Error('Enter a comment up to 1,800 characters.');
    if(!commentTarget(current,target))throw Error('This part of the design is unavailable.');
    if((current.extensions?.designComments?.length||0)>=300)throw Error('This project already has 300 design comments.');
    const comment={id:crypto.randomUUID(),target,text,status:'queued',...(quote?{quote:quote.slice(0,1500)}:{})};
    updateComments(current.id,rows=>[...rows,comment]);
    if(ask)void runDesignComments([comment.id]);
  }
  function replyToDesignComment(id,value){
    const text=value.trim();
    if(!text||text.length>1800)throw Error('Enter a reply up to 1,800 characters.');
    const current=projectRef.current;
    if(!current.extensions?.designComments?.some(row=>row.id===id))throw Error('This comment is no longer available.');
    const reply={id:crypto.randomUUID(),text,createdAt:new Date().toISOString()};
    updateComments(current.id,rows=>rows.map(row=>row.id===id?{...row,replies:[...(Array.isArray(row.replies)?row.replies:[]),reply]}:row));
  }
  async function runDesignComments(ids){
    if(!ids.length)return;
    const owner=projectRef.current.id;
    const live=sessionRef.current||await refreshSession();
    if(projectRef.current.id!==owner)return;
    if(!live||!connection){notify('Connect an AI provider to review saved comments.');showConnections();return;}
    const queue=commentQueue.current;
    for(const id of ids)if(queue.activeId!==id&&!queue.items.some(item=>item.id===id))queue.items.push({owner,id});
    if(queue.working)return;
    queue.working=true;
    try{
      while(queue.items.length){
        const job=queue.items.shift();
        const current=projectRef.current;
        if(current.id!==job.owner)continue;
        const row=current.extensions?.designComments?.find(comment=>comment.id===job.id);
        if(!row||row.status==='applied')continue;
        queue.activeId=row.id;
        setRunningComment(row.id);
        const update=values=>updateComments(job.owner,comments=>comments.map(comment=>comment.id===row.id?{...comment,...values}:comment));
        try{
          const binding=commentTarget(current,row.target);
          if(!binding)throw Error('This part of the design is unavailable.');
          const basis=commentBasis(binding);
          update({status:'queued',proposal:null,error:null});
          await saveEngineeringProject(job.owner);
          const response=await requestArchitect({session:sessionRef.current,connection,message:commentPrompt(current,row,binding),
            project:current,history:[],origin:'document',stage:'design',signal:AbortSignal.timeout(120000)});
          const proposal=parseCommentProposal(response.message,binding);
          const ready=Object.keys(proposal.changes).length>0;
          if(ready)toProjectFile(applyCommentProposal(current,{...row,basis},proposal));
          update({status:ready?'ready':'answered',proposal,basis,error:null});
        }catch(failure){
          update({status:'failed',error:failure.name==='TimeoutError'?'AI review timed out.':failure.message,proposal:null});
        }
        finally{queue.activeId=null;setRunningComment(null);}
      }
    }finally{queue.working=false;}
  }
  function applyDesignComment(id){
    const current=projectRef.current;
    if(busy||agentBusy||pending)throw Error('Finish the current design change before applying this edit.');
    const comment=current.extensions?.designComments?.find(row=>row.id===id);
    if(comment?.status!=='ready')throw Error('This AI edit is unavailable.');
    const next=applyCommentProposal(current,comment);
    const extensions={...next.extensions,designComments:next.extensions.designComments.map(row=>row.id===id?{...row,status:'applied'}:row)};
    validateImport(next);
    toProjectFile({...next,extensions});
    commit({...next,extensions});
  }
  function renderDesignComments(target,label){
    return <DesignComments key={JSON.stringify(target)} project={project} target={target} label={label} onSave={saveDesignComment}
      onRun={id=>void runDesignComments([id])} onApply={applyDesignComment} onReply={replyToDesignComment} running={runningComment}/>;
  }
  async function saveCurrentProject() {
    if(savingProject)return;
    setSavingProject(true);
    try {
      const current=projectRef.current;
      if(sessionRef.current){
        const receipt=await saveEngineeringProject(current.id);
        if(receipt.saved!==true&&!/^[a-f0-9]{64}$/.test(receipt.sha256||''))throw Error('Project save could not be confirmed.');
        notify('Project saved.');
        if(projectRef.current.id===current.id)void runDesignComments((current.extensions?.designComments||[]).filter(row=>row.status==='queued').map(row=>row.id));
      }else{
        const draft=withConversation(current,messagesRef.current);
        toProjectFile(draft);
        localStorage.setItem(STORAGE,JSON.stringify(draft));
        setStorageError(false);
        notify('Project saved in this browser.');
      }
    }catch(error){notify(error.message);}
    finally{setSavingProject(false);}
  }
  function saveProjectFile(filename = `${slug}.atmem-ai-architect.json`) {
    try {
      download(JSON.stringify(toProjectFile(withConversation(projectRef.current, messagesRef.current)), null, 2), filename);
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
  const drawingBoard=onBoard&&!testing&&level!=='block';
  useEffect(()=>{
    if(!drawingBoard)return;
    const mobile=window.matchMedia('(max-width:900px)');
    const onNarrow=event=>{if(event.matches)setChatOpen(false);};
    mobile.addEventListener('change',onNarrow);
    return ()=>mobile.removeEventListener('change',onNarrow);
  },[drawingBoard]);
  const drawingStudio=drawingBoard||(mode==='design'&&['system-diagrams','system-model-legacy','engineering-page'].includes(designView));
  const boardPages=projectPages(project.extensions?.architectureDiagrams?.views,project.extensions?.systemModel?.diagrams,project.extensions?.engineeringModel?.diagrams);
  const boardToolLocked=busy||previewing||agentBusy||Boolean(pending);
  const boardProgressVisible=mode==='design'&&onBoard&&boardProgress;
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
    <div style={{"--chat-panel-width":`${chatWidth}px`}} className={`app ${idleChat?"idle-chat":""} ${chatOpen&&!buildView ? "" : "chat-closed"} ${buildView?"build-workspace":""}`}>
      <header className="bar">
        <button aria-label="About AtMem AI Architect" className="brand" onClick={() => setModal("about")} title="About AtMem AI Architect">
          <Mark />

        </button>
        <nav className="crumbs" aria-label="Level"><span className="workspace-label">PROJECT</span>
          <button className="projects-btn" aria-label="Projects" title="Your projects" onClick={() => (refreshProjects(), setModal("projects"))}>
            <FolderOpen size={22} /><span>Projects</span>
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
          {!chatOpen&&<button className="icon" title="Show chat" aria-label="Show chat" onClick={()=>setChatOpen(true)}><PanelRightOpen size={18}/></button>}
          {HOSTED&&<><button className="btn" onClick={newProject} disabled={busy||agentBusy}><Plus size={16}/>New project</button><button className="btn" onClick={()=>hostedCall('account')}>Account</button></>}
          {isReadyExample(project)&&<><ReadyExampleDownload compact/>{!HOSTED&&<button className="btn" onClick={newProject} disabled={busy||agentBusy}>Create new project</button>}</>}
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
          <button ref={menuTrigger} className="icon" title="More" aria-label="More" aria-haspopup="menu" aria-expanded={menu} aria-controls={menu?"project-menu":undefined} onClick={() => setMenu((m) => !m)}>
            <MoreHorizontal size={16} />
          </button>

        </div>
        {menu && (
          <div ref={projectMenu} id="project-menu" className="menu project-menu" role="menu"
            aria-label="Project actions" onKeyDown={navigateProjectMenu}
            onClick={event=>{if(event.target.closest('[role="menuitem"]'))setMenu(false);}}>
            <div className="project-menu-group" role="group" aria-label="Project files">
              <button role="menuitem" tabIndex={-1} onClick={() => (refreshProjects(), setModal("projects"))} disabled={busy}><FolderOpen/>Projects</button>
              <button role="menuitem" tabIndex={-1} onClick={newProject} disabled={busy||agentBusy}><Plus/>New project</button>
              <button role="menuitem" tabIndex={-1} onClick={()=>{fileImportAsCopy.current=false;fileRef.current.click();}} disabled={busy}><FolderOpen/>Open project file</button>
              <button role="menuitem" tabIndex={-1} onClick={saveCurrentProject} disabled={savingProject}><Save/>Save</button>
              <button role="menuitem" tabIndex={-1} onClick={()=>setModal("save-as")}><Download/>Save as…</button>
            </div>
            <div className="project-menu-group" role="group" aria-label="Design">
              <button role="menuitem" tabIndex={-1} onClick={showBlockLibrary} disabled={busy}><Plus/>Add a block</button>
              <button role="menuitem" tabIndex={-1} onClick={() => setModal("import")} disabled={busy}><GitBranch/>Import diagram</button>
              <button role="menuitem" tabIndex={-1} onClick={() => setModal("templates")} disabled={busy}><LayoutTemplate/>Templates</button>
              <button role="menuitem" tabIndex={-1} onClick={openReadyExample} disabled={busy||agentBusy}><LayoutGrid/>Open runnable AI example</button>
            </div>
            <div className="project-menu-group" role="group" aria-label="Workspace settings">
              {!HOSTED&&<button role="menuitem" tabIndex={-1} onClick={() => showConnections()}><Waypoints/>AI providers</button>}
              <button role="menuitem" tabIndex={-1} onClick={() => setModal("memory")} disabled={!session}><BrainActivity size={16} active={false}/>AtMem memory</button>
              <button role="menuitem" tabIndex={-1} onClick={() => setModal("licenses")}><ShieldCheck/>Licences</button>
              <button role="menuitem" tabIndex={-1} onClick={() => setModal("start-over")} disabled={busy || agentBusy}><RotateCcw/>Start over</button>
            </div>
            <div className="project-menu-footer" role="group" aria-label="Links">
              <a role="menuitem" tabIndex={-1} href="https://atmem.ai" target="_blank" rel="noopener noreferrer"><ExternalLink/>Website</a>
              <a role="menuitem" tabIndex={-1} href="mailto:hello@atmem.ai"><Mail/>Contact</a>
              <a role="menuitem" tabIndex={-1} href={STAR_URL} target="_blank" rel="noopener noreferrer"><Github/>GitHub</a>
            </div>
          </div>
        )}
      </header>

      <section className="journey-wizard unified-journey" aria-label="Architecture journey">
        <nav className="stage-tabs" role="tablist" aria-label="Project stages">{DESIGN_SECTIONS.map((section,i)=><button key={section.id} role="tab" aria-label={section.label} aria-selected={activeSection.id===section.id} className={completedStages(project)[section.id]?'stage-complete':''} onClick={()=>visitJourney(section.id)} title={completedStages(project)[section.id]?'Working draft recorded; see Review for verification':'Not yet acknowledged'}><span>{i+1}</span>{section.label}</button>)}</nav>
        {nextAction&&<div className="journey-current"><button className="btn primary" disabled={busy||agentBusy||!!pending} onClick={()=>nextAction.kind==='navigate'?visitJourney(nextAction.section):nextAction.kind==='continue'?continueJourney():followJourney()}>{nextAction.label} <span aria-hidden="true">→</span></button></div>}
      </section>
      <main
        id="canvas"
        className={`canvas level-${level} ${drawingStudio?'drawing-studio'+(libraryCollapsed?' library-collapsed':''):''}`}
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
        {drawingStudio&&<button className="studio-library-toggle" aria-label="Toggle drawing tools" aria-expanded={!libraryCollapsed} onClick={()=>setLibraryCollapsed(v=>!v)}><PencilRuler size={16}/> Tools</button>}
        {drawingStudio&&<aside hidden={libraryCollapsed} className="studio-library"  aria-label="Board library">
          <div className="studio-tools" role="group" aria-label="Workspace library">
            {['Shapes','Blocks','Layers','Pages'].map(tab=><button key={tab} type="button" aria-pressed={studioTab===tab} onClick={()=>setStudioTab(tab)}>{tab}</button>)}
            <button type="button" aria-label="Hide drawing tools" onClick={()=>setLibraryCollapsed(true)}>‹</button>
          </div>
          <div className="studio-tool-content" hidden={studioTab!=='Shapes'}>
            <div ref={setLibrarySlot}/>
            {drawingBoard&&<DrawioShapePalette onAdd={addDrawingTool} disabled={boardToolLocked}/>}
            {designView==='system-diagrams'&&!project.extensions?.architectureDiagrams?.views.length&&<button className="btn" onClick={createArchitectureDiagram}>Create a page</button>}
            {['system-model-legacy','engineering-page'].includes(designView)&&<DrawioShapePalette onAdd={tool=>{openDrawingPage('board');addDrawingTool(tool);}} disabled={boardToolLocked} boardTarget/>}
          </div>
          {studioTab==='Blocks'&&<div className="studio-tool-content"><Palette inline disabled={boardToolLocked} onAdd={item=>{openDrawingPage('board');addComponent(item,paletteAt.current||undefined);}}/></div>}
          {studioTab==='Layers'&&<div className="studio-tool-content studio-layers" aria-label="Component tree">
            <h3>Components &amp; layers</h3><button className="btn" disabled={!blockReviews.length} onClick={()=>reviewBlock((blockReviews.find(r=>r.status!=='reviewed')||blockReviews[0]).id)}>Review blocks · {blockReviews.filter(r=>r.status==='reviewed').length}/{blockReviews.length}</button>
            <NestedBlocks nodes={project.nodes} selected={boardRecord} onOpen={selectStudioBlock}/>
            {!blockReviews.length&&<p>No project blocks yet.</p>}
            <button className="btn" onClick={showBlockLibrary}><Plus size={14}/> Add component</button>
          </div>}
          {studioTab==='Pages'&&<div className="studio-tool-content"><PageExplorer project={project} onOpen={openDrawingPage} onCreate={()=>{setOpenDiagramPicker(true);openSystemDiagrams();setOpenDiagramPicker(true);}} onGenerate={()=>{openSystemDiagrams();setOpenSpecOnEntry(true);}}/><div hidden><DiagramPicker inline model={project.extensions?.architectureDiagrams||emptyDiagramModel()}
            onClose={()=>setStudioTab('Shapes')} onCreate={createStudioPage} error={pageError}/></div></div>}
          {level!=='block'&&(sourceDocuments.length>0||currentSourceBatch)&&<aside className="board-source-dock" aria-label="Uploaded specifications">
            <details open={currentSourceBatch?true:undefined}>
              <summary>{sourceDocuments.length} {sourceDocuments.length===1?'specification':'specifications'} loaded</summary>
              <ul aria-label="Loaded files">{sourceDocuments.map(source=><li key={source.sha256}>{source.name}</li>)}</ul>
              {currentSourceBatch&&<>
                <p role={currentSourceBatch.error?'alert':'status'}>{currentSourceBatch.error||'Reading files…'}</p>
                <ul aria-label="Selected files">{currentSourceBatch.names.map((name,index)=><li key={index}>{name}</li>)}</ul>
              </>}
              <div className="board-source-actions">
                <button className="link" disabled={readingAttachments||!!pending} onClick={()=>requirementsInput.current.click()}>Add files</button>
                {nativeDesignEnabled&&<button className="link" aria-expanded={boardProgress} onClick={()=>setBoardProgress(!boardProgress)}>{boardProgress?'Hide progress':'Architecture progress'}</button>}
                {(buildRequest?.intent==='design'||['running','starting'].includes(engineeringStatus?.state))&&<span role="status">Designing…</span>}
              </div>
            </details>
          </aside>}
        </aside>}
        <div className={`board-surface ${drawingBoard?"drawing-board":""} ${extraBoardTools?'show-extra-tools':''}`} hidden={!onBoard}>
          <div className="board-overlays">
          <div className="board-top-controls">
          <div className="board-top-actions">
            {level!=='block'&&<div className="nested-view-control">
          {nested.projected&&<label className="nested-scope-control">Scope
            <select aria-label="Architecture level" value={nested.scope||''} onChange={event=>exploreSubsystem(event.target.value||null)}>
              <option value="">Top level</option><option value="*">All blocks</option>
              {shown.nodes.filter(node=>shown.nodes.some(child=>child.data.parentBlockId===node.id)).map(node=><option key={node.id} value={node.id}>{node.data.label}</option>)}
            </select>
          </label>}
          {!nested.projected&&shown.nodes.some(node=>node.data.parentBlockId)&&<button className="btn" onClick={()=>exploreSubsystem(null)}>Top level</button>}
        </div>}
            {nativeDesignEnabled&&hasDesign&&studioTab==='Layers'&&<div className="native-canvas-action"><button className="btn" disabled={busy||agentBusy||!!pending} onClick={()=>startArchitecture()}>Update architecture</button><button className="link" disabled={readingAttachments||agentBusy||!!pending} onClick={()=>requirementsInput.current.click()}>Add specification</button></div>}
          </div>
        </div>
        <div className="board-controls">
        <div className="toolbar" aria-label="Tools">
          {level !== "block" && <>
            <button className="btn" type="button" disabled={busy||agentBusy||!!pending} onClick={()=>{paletteAt.current=null;showBlockLibrary();}}><Plus size={16}/> Add block</button>
            {(selected || picked.size>0) && <button className="btn" type="button" onClick={()=>copySelection()}>Copy</button>}
            {boardClipboard?.projectId === project.id && <button className="btn" type="button" disabled={busy||agentBusy||!!pending} onClick={()=>pasteSelection()}>Paste</button>}
          </>}
          {level!=='block'&&<><button className="btn" onClick={()=>setDesignView('overview')}>Overview</button><button className="btn board-secondary" type="button" onClick={openSystemDiagrams}>System diagrams</button></>}
          {level!=='block'&&<span className="board-secondary">{renderDesignComments({kind:'project'})}</span>}
          <button
            className="icon board-secondary"
            title="Auto-arrange"
            aria-label="Auto-arrange"
            disabled={busy || previewing || nested.projected || level==='block' || !project.nodes.length}
            onClick={() => {
              if(level==='system')setTopologyPositions(arrangeOverview(system,measured));
              else commit(autoLayout(projectRef.current));
              refit();
            }}
          >
            <LayoutGrid size={17} />
          </button>
          <button className="btn reset-board board-secondary" title="Reset board and context" aria-label="Reset board and context" disabled={busy||agentBusy||intake.length>0} onClick={newProject}>
            <Trash2 size={17} /> Reset board
          </button>
          <button className="icon" title="Undo board change" aria-label="Undo" disabled={!history.length || busy || agentBusy} onClick={undo}>
            <Undo2 size={17} />
          </button>
          <button className="icon" title="Redo board change" aria-label="Redo" disabled={!future.length || busy || agentBusy} onClick={redo}><Redo2 size={17} /></button>
          <button className="btn board-more-tools" aria-expanded={extraBoardTools} onClick={()=>setExtraBoardTools(value=>!value)}>{extraBoardTools?'Fewer actions':'More actions'}</button>
          {onBoard&&level!=='block'&&!emulationOpen&&!applyDockOpen&&hasDesign&&<button type="button" className={`apply-launcher board-secondary ${applyEmulation.running?'working':''}`} onClick={()=>setApplyDockOpen(true)} aria-label="Open Terraform apply emulation"><Play size={16}/> {applyEmulation.running?'Emulating…':'Emulate apply'}</button>}
        </div>
        {level !== "block" && (
          <div className="zoom">
            <button className="btn board-secondary" onClick={()=>download(drawioFile([{id:project.id,name:project.name,...nativeBoard}]),'board.drawio','application/xml')}>Export diagram</button>
            <button className="btn" disabled={busy||agentBusy||!!pending} onClick={insertMermaidDiagram}>Insert Mermaid</button>
            <button className="icon" aria-label="Zoom out" onClick={() => zoomOut()}><ZoomOut size={15} /></button>
            <button className="icon" aria-label="Fit" title="Fit" onClick={() => refit(undefined,.1)}><Maximize2 size={14} /></button>
            <button className="icon" aria-label="Zoom in" onClick={() => zoomIn()}><ZoomIn size={15} /></button>
          </div>
        )}
        </div>
          </div>
          <div className="board-paper">
          <ArchitectureStatus activity={engineeringActivity?.owner===project.id?engineeringActivity:null} error={engineeringError?.owner===project.id?engineeringError.message:null} connected={connection?.provider==='codex'&&!!connection?.effort} job={engineeringStatus} pending={buildRequest} sources={sourceDocuments} hasDesign={hasDesign} onReview={()=>setBoardProgress(true)} onConnect={showConnections} onRetry={()=>startArchitecture()}/>
          {!shown.nodes.length&&!hasDesign&&!palette&&!dismissedStarts.includes(project.id)&&!['running','starting'].includes(engineeringStatus?.state)&&!buildRequest&&!['interrupted','failed','cancelled'].includes(engineeringStatus?.last_status)&&<section className="board-start" aria-label="Start your project"><button type="button" className="icon board-start-close" aria-label="Dismiss welcome card" title="Dismiss welcome card" onClick={dismissStart}><X size={16}/></button><h2>What would you like to create?</h2><div className="row"><button className="btn" onClick={openReadyExample}>Explore runnable AI example</button><button className="btn" onClick={()=>{dismissStart();setChatOpen(true);document.querySelector('.composer textarea, .chat textarea')?.focus();}}>Start chatting</button><button className="btn primary" onClick={()=>requirementsInput.current.click()}>Upload specification</button><button className="btn" onClick={openSystemDiagrams}>Browse diagrams</button><button className="btn" onClick={()=>setModal("project-file")}>Open project</button></div><InlineNote label="Supported starting files">Word, PDF, text, Markdown, diagrams, images and Architect project JSON.</InlineNote></section>}

        <DrawioCanvas layoutKey={boardLayoutKey} scopeLabel={nested.projected?`Overview · ${canvasNodes.length} of ${project.nodes.length} elements. Open a component for details.`:`All ${canvasNodes.length} elements`} onDropShape={drawingBoard&&!boardToolLocked?addDrawingTool:null} graphRef={boardApi} scene={nativeBoard} label="Architecture board"
          selected={picked.size?[...picked]:boardRecord||selected} onSelect={(id,event)=>{
            setBoardRecord(id||null);
            if(!id){setCtx(null);setPicked(new Set());setSelected(null);setPalette(false);return;}
            const node=canvasNodes.find(row=>row.id===id);
            if(!node||level==='system')return;
            if(event?.shiftKey||event?.metaKey||event?.ctrlKey)setPicked(current=>{
              const next=new Set(current.size?current:selected?[selected]:[]);
              if(next.has(id))next.delete(id);else next.add(id);
              return next;
            });
            else setPicked(new Set());
            setSelected(id);setProbe(null);
          }}
          onDoubleClick={openBoardRecord}
          onLayout={!busy&&!previewing?changes=>saveDrawingLayout(boardLayoutKey,changes):null} onMove={boardEditable?moveBoard:null}
          onConnect={boardEditable?connectBoard:null}
          onRemove={boardEditable?removeBoard:null}
          onContext={(e,id)=>{
            if(previewing)return;
            setCtx({x:e.clientX,y:e.clientY,at:screenToFlowPosition(e),
              node:level==='system'?null:canvasNodes.find(row=>row.id===id)});
          }}
        />
        {level!=='block'&&boardItem&&<aside className="drawio-board-source" aria-label="Selected diagram record">
          <header><strong>{boardItem.name}</strong><button className="icon" aria-label="Close diagram source" onClick={()=>setBoardRecord(null)}><X size={15}/></button></header>
          {recordNode&&<div className="board-inspector-tabs" role="group" aria-label="Element inspector">
            {(recordNode.data.kind==='note'?['Mermaid','Style']:['Properties','Mermaid','Style']).map(tab=><button key={tab}
              aria-pressed={(recordNode.data.kind==='note'&&boardPane==='Properties'?'Mermaid':boardPane)===tab} onClick={()=>setBoardPane(tab)}>{tab}</button>)}
          </div>}
          {recordNode&&boardPane==='Properties'&&renderBlockProperties(recordNode.id)}
          {(!recordNode||boardPane==='Mermaid'||(recordNode.data.kind==='note'&&boardPane==='Properties'))&&<DiagramMermaid code={graphMermaid(nativeBoard,{selected:boardItem.id})}/>}
          {boardItem.source&&<section aria-label="Connection properties"><h4>Interfaces</h4>{(boardItem.interfaceIds||[boardItem.id]).map(id=>project.edges.find(e=>e.id===id)).filter(Boolean).map(edge=><details key={edge.id}><summary>{edge.label||edge.id}</summary><dl>{Object.entries(interfaceFields).filter(([key])=>edge.interfaceSpec?.[key]).map(([key,label])=><React.Fragment key={key}><dt>{label}</dt><dd>{edge.interfaceSpec[key]}</dd></React.Fragment>)}</dl><button className="btn" onClick={()=>openBlock(edge.source,edge)}>Open interface</button></details>)}</section>}
          {recordNode&&boardPane==='Style'&&<div className="board-style-fields">
            <label>Fill<input type="color" disabled={boardToolLocked} value={recordNode.data.drawingFill||boardItem.style.match(/fillColor=(#[0-9a-f]{6})/i)?.[1]||'#ffffff'} onChange={event=>styleBoardBlock('drawingFill',event.target.value)}/></label>
            <label>Outline<input type="color" disabled={boardToolLocked} value={recordNode.data.drawingStroke||'#7a8696'} onChange={event=>styleBoardBlock('drawingStroke',event.target.value)}/></label>
          </div>}
          {!boardItem.source&&<button className="btn" onClick={()=>openBoardRecord(boardItem.id)}>{recordNode?.data.drawingShape?'Edit label':recordNode?.data.kind==='note'?'Edit comment':'Open component'}</button>}
        </aside>}
        </div>
        {drawingBoard&&<DiagramPages pages={boardPages} active="board" onSelect={openDrawingPage} onAdd={boardToolLocked?null:createArchitectureDiagram}/>}
        {palette && <Palette onAdd={(item) => addComponent(item, paletteAt.current || undefined)} onClose={() => ((paletteAt.current = null), setPalette(false))} disabled={busy} />}

        {ctx && (
          <div className="ctx-menu" role="menu" style={{ left: Math.min(ctx.x,window.innerWidth-210), top: Math.min(ctx.y,window.innerHeight-200) }} onMouseLeave={() => setCtx(null)}>
            {ctx.node ? (
              <>
                <button role="menuitem" onClick={()=>{copySelection(picked.size>1&&picked.has(ctx.node.id)?picked:[ctx.node.id]);setCtx(null);}}>Copy</button>
                <button role="menuitem" onClick={()=>{reviewBlock(ctx.node.id);setCtx(null);}}>Edit block</button>
                <button role="menuitem" onClick={()=>{openBlock(ctx.node.id);setCtx(null);requestAnimationFrame(()=>{
                  const control=document.querySelector('.block-spec-content .module-facts + .design-comments');
                  if(control){control.open=true;control.querySelector('textarea')?.focus();}
                });}}>Comment on block</button>
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
                <button role="menuitem" onClick={() => ((paletteAt.current = ctx.at), showBlockLibrary(), setCtx(null))}>
                  <Plus size={16}/> Add block here
                </button>
                {boardClipboard?.projectId === project.id && <button role="menuitem" disabled={busy||agentBusy||!!pending} onClick={()=>{pasteSelection(ctx.at);setCtx(null);}}>Paste here</button>}
                <button role="menuitem" onClick={() => (addNote(ctx.at), setCtx(null))}>
                  <StickyNote size={16}/> Add comment here
                </button>
                <button role="menuitem" onClick={() => (setLevel("flow"), setPicked(new Set(project.nodes.map((n) => n.id))), setCtx(null))}>
                  <Scan size={16}/> Select all
                </button>
                <div className="ctx-divider" role="separator"/>
                <button role="menuitem" className="danger" disabled={!project.nodes.length} onClick={() => (newProject(), setCtx(null))}>
                  <Trash2 size={16}/> Reset board and context
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
              Preview · <strong>{pending.title}</strong>{pending.sourceRequirements&&` · ${pending.sourceRequirements.length} source-linked requirements · ${pending.quality.score}% structural coverage`}
            </span>
            <button className="btn primary" disabled={busy} onClick={() => applyProposal()}>
              Apply
            </button>
            <button className="btn ghost" onClick={() => setPending(null)}>
              Dismiss
            </button>
          </div>
        )}
        {!drawingBoard&&!shown.nodes.length && (
          <div className="empty-canvas">
            <p className="muted">Describe your idea in the chat — it takes shape here.</p>
          </div>
        )}

        {level === "block" && selectedNode && (
          <BlockDetail
            key={selectedNode.id}
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
            session={session}
            onPrepareSources={prepareSourceEvidence}
            onSaveInterface={saveBlockInterface}
            renderComments={renderDesignComments}
            onSystemDiagrams={(project.extensions?.systemModel||project.extensions?.architectureDiagrams)?openSystemDiagrams:undefined}
            onInterface={session?edgeId=>{setChatOpen(true);return send(`Define the directional interface for existing connection ${JSON.stringify(edgeId)}. Use a compact interfaceSpec update. Cover transport and version, request, result, authorization, failure and verifiable contract tests. Leave unverified vendor or owner details explicit and ask at most one material question.`,'workflow');}:null}
            onDraft={session?()=>{setChatOpen(true);return send(`Draft or refine the Block Spec Kit for ${selectedNode.data.label} (id ${selectedNode.id}) using its saved requirements, dependencies and source evidence. Propose a compact buildSpec update for just this block. Ask one linked question if a material decision is needed.`,'workflow');}:null}
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
        {mode==='design'&&designView==='overview'&&<ProjectOverview project={project} onDrawings={()=>{setDesignView('board');setStudioTab('Pages');}} onRequirements={()=>visitJourney('scope')} onReview={()=>visitJourney('review')} onBlock={id=>{setDesignView('board');openBlock(id);}}/>}
        {mode==='design'&&designView==='system-diagrams'&&<ArchitectureDiagramWorkspace
          key={project.id+':'+(entryPage||'')} project={project} onLayoutPage={saveDrawingLayout} onBack={()=>setDesignView('board')} librarySlot={librarySlot} onNewPage={createArchitectureDiagram} initialPage={entryPage} onPage={openDrawingPage} initiallyGenerating={openSpecOnEntry} initiallyCreating={openDiagramPicker} initialMermaid={openMermaidOnEntry}
          onSave={saveArchitectureDiagrams} onSaveProject={saveCurrentProject}
          onUndo={undo} onRedo={redo} canUndo={history.length>0} canRedo={future.length>0}
          onDraft={draftArchitectureDiagrams} locked={busy||agentBusy||!!pending}
          connected={!HOSTED&&!!session?.diagramAuthoringEnabled&&!!connection} onConnect={showConnections}
          onComments={renderDesignComments}
          onLegacy={(pending?.systemModel||project.extensions?.systemModel)?()=>setDesignView('system-model-legacy'):null}/>}
        {mode==='design'&&designView==='engineering-page'&&<div className="studio-engineering">
          <EngineeringModelView drawingLayouts={project.extensions?.drawingLayouts} onLayoutPage={saveDrawingLayout} key={entryPage} model={project.extensions?.engineeringModel} pageId={entryPage} onPageChange={setEntryPage} renderBlockProperties={renderBlockProperties} renderComments={renderDesignComments}/>
          <DiagramPages pages={boardPages} active={'engineering/'+entryPage} onSelect={openDrawingPage} onAdd={boardToolLocked?null:createArchitectureDiagram}/>
        </div>}
        {mode==='design'&&designView==='system-model-legacy'&&<SystemModelWorkspace onLayoutPage={saveDrawingLayout}
          key={project.id}
          project={pending?.systemModel?{...pending.next,...canvasProposalRecords(project,pending)}:project}
          renderBlockProperties={pending?undefined:renderBlockProperties} onBack={()=>openDrawingPage('board')} initialPage={entryPage} onPage={openDrawingPage} onNewDiagram={createArchitectureDiagram}
          onUndo={undo} onRedo={redo} canUndo={history.length>0} canRedo={future.length>0}
          onSave={busy||agentBusy||pending?undefined:saveDiagramModel}
          onSaveProject={saveCurrentProject}
          renderComments={pending?undefined:renderDesignComments}
          onOpenBlock={pending?undefined:id=>{setDesignView('board');openBlock(id);}}
          onGenerate={nativeDesignEnabled?()=>startArchitecture():undefined}/>}
        <div className={`review-workspace${boardProgressVisible?' board-engineering-panel':''}`}
          hidden={mode!=='review'&&mode!=='estimate'&&!(boardProgressVisible)}>
        <header className="review-intro"><h2>Review</h2></header>
        {mode==='review'&&<HandoffReview project={project} onOpen={openDrawingPage} onDelivery={()=>visitJourney('delivery')} busy={busy||agentBusy||!!pending}/>}
        {mode==='review'&&modelLinkIssues.length>0&&<details className="review-generation">
          <summary>{modelLinkIssues.length} model and test links need review</summary>
          <ul>{modelLinkIssues.map((issue,index)=><li key={index}>
            <strong>{issue.modelElementId||issue.caseId}</strong> · {issue.message} <code>{issue.ref}</code>
          </li>)}</ul>
        </details>}
        <div className="review-design-status"><ShieldCheck size={18}/><span>{findings.filter(f=>f.status==='open').length} design items</span><button className="icon" aria-label="Open design checks in specification" title="Specification" onClick={()=>visitJourney('scope')}><Code2 size={16}/></button></div>
        {mode==='review'&&nativeDesignEnabled&&project.extensions?.designSources?.length>0&&<section className="review-generation" aria-label="Source documents">
          <h3>Source documents</h3>
          <ul>{project.extensions.designSources.map(source=><li key={source.sha256}>{source.name} · {source.text.length.toLocaleString()} characters{source.figureEvidence?.manifestSha256?` · ${source.figureEvidence.figures.filter(figure=>figure.status==='available').length} figures available for inspection`:source.graphics?.length?` · ${source.graphics.length} figures need source re-upload`:null}</li>)}</ul>
        </section>}
        {session?.engineeringEnabled&&canObserveEngineering&&<section hidden={mode!=='review'&&!(boardProgressVisible)} className="review-generation engineering-workspace-panel" aria-label="Generation and verification">{boardProgressVisible&&<button className="icon board-progress-close" aria-label="Close architecture progress" onClick={()=>setBoardProgress(false)}><X size={16}/></button>}<EngineeringPanel key={project.id} project={project} onBusyChange={setGenerationPending} onActivity={receiveEngineeringActivity} onError={message=>setEngineeringError(message?{owner:project.id,message}:null)} onWorkModelChange={changeArchitectureWork} onIntentContext={syncEngineeringIntent} projectId={project.id} session={session} connection={connection} onRequestArchitecture={()=>startArchitecture()} contextBusy={busy||agentBusy||!!pending} saveProject={()=>saveEngineeringProject(project.id)} buildRequest={buildRequest} onCanvas={nativeDesignEnabled?previewArchitectureDraft:null} onAssessCanvas={nativeDesignEnabled?readArchitectureDraft:null} onBuildRequestHandled={id=>{setBuildRequest(current=>current?.id===id?null:current);const current=projectRef.current;if(current.extensions?.pendingArchitecture?.id===id){const {pendingArchitecture,...extensions}=current.extensions;updateEngagement({...current,extensions});}}} onConnections={()=>showConnections()}/></section>}
        {hasDesign&&<>
        <section className="review-costs" aria-label="Project costs">
        {["review","estimate"].includes(mode) && <EstimateView project={project} result={costs} onChange={updateEngagement} busy={busy||agentBusy||!!pending} onEstimate={refreshEstimate} onChooseRegion={()=>{visitJourney('cloud');requestAnimationFrame(()=>{const input=document.querySelector('.location-region-form input');input?.focus();input?.scrollIntoView({block:'center',behavior:'instant'});});}} pricing={pricingState} onNext={()=>{const section=document.querySelector('.review-generation');const target=section?.querySelector('button')||section;if(target){target.setAttribute('tabindex','-1');target.focus({preventScroll:true});target.scrollIntoView({block:'center'});}}} />}
        </section>
        </>}
        {mode==='review'&&!session?.engineeringEnabled&&<p>Generation and local checks require the engineering service. Your design is retained; Delivery can package the design and remaining tasks.</p>}
        {mode==='review'&&hasDesign&&<ProjectChecks generationPending={generationPending} receipt={checkReceipt} project={project} environment={environment} session={session} onReceipt={setCheckReceipt} onBusy={setChecking}/>}
        {mode==='review'&&hasDesign&&<footer className="review-finish"><div><strong>3. Package and download</strong><p>Explore all files and download one project ZIP in Delivery.</p></div><button className="btn primary" onClick={()=>{const next=acknowledgeStage(projectRef.current,'review');updateEngagement(costs.expected!==null&&!costs.mixedCurrencies?{...next,extensions:{...next.extensions,journey:{...next.extensions.journey,estimate:journey(next).keys.estimate}}}:next);visitJourney('delivery');}}>Complete →</button></footer>}
        </div>




        {onBoard&&level!=='block'&&!emulationOpen&&applyDockOpen&&<div className="emulation-dock"><TerraformApplyDock project={project} emulation={applyEmulation} blocked={!hasDesign} onClose={()=>setApplyDockOpen(false)} onOpenBlock={id=>{setApplyDockOpen(false);reviewBlock(id);}}/></div>}
        {onBoard&&emulationOpen&&<div className="emulation-dock"><EmulationPanel project={project} session={session} emulation={emulation} onDiscuss={discussEmulation} onOpenComponent={id=>{reviewBlock(id);setEmulationOpen(false);}} discussionBusy={busy||agentBusy||!!pending} onClose={()=>setEmulationOpen(false)} onBuild={()=>{setEmulationOpen(false);visitJourney('delivery');}}/></div>}

        {mode === "design" && designView === "outputs" && <OutputsView workStatus={engineeringStatus} onNavigate={async target=>{const [stage,selector]={requirements:['scope','.requirements-document'],location:['cloud','section[aria-label="Country and region"]'],cost:['review','.review-costs'],implementation:['review','.review-generation'],checks:['review','.project-checks']}[target];visitJourney(stage);await new Promise((resolve,reject)=>{const started=performance.now();function focus(){const element=document.querySelector(selector);if(element&&element.getClientRects().length){element.setAttribute('tabindex','-1');element.focus({preventScroll:true});element.scrollIntoView({block:'start',behavior:'instant'});resolve();}else if(performance.now()-started<5000)requestAnimationFrame(focus);else reject(Error('Section is unavailable. Use the stage tabs to continue.'));}requestAnimationFrame(focus);});}} checkReceipt={checkReceipt} onDownloaded={()=>{updateEngagement(acknowledgeStage(projectRef.current,'delivery'));setStarOffer(value=>value+1);}} onReview={()=>visitJourney('review')} onSave={expected=>saveEngineeringProject(project.id,expected)} onPrepareSources={prepareSourceEvidence} project={project} run={run} environment={environment} session={session} emulation={emulation} onDiscuss={discussEmulation} discussionBusy={busy||agentBusy||!!pending} onDownload={downloadBundle} onBuild={session?.engineeringEnabled?()=>visitJourney('review'):undefined} onBack={()=>setDesignView("board")} />}
        {mode === "design" && designView === "terraform" && <TerraformView onOpenBlock={id=>reviewBlock(id)} project={project} environment={environment} session={session} applyEmulation={applyEmulation} emulation={emulation} onDiscuss={discussEmulation} discussionBusy={busy||agentBusy||!!pending} onDelivery={()=>visitJourney("delivery")} onBuild={session?.engineeringEnabled?()=>visitJourney('review'):undefined} onBack={()=>setDesignView("board")} />}
        <div className="choices-workspace" hidden={!(mode==="design"&&["options","decisions","location"].includes(designView))}>
        {mode === "design" && ["options","decisions"].includes(designView) && (
          <OptionsView project={project} busy={busy||agentBusy||!!pending} onChoose={chooseCloud} onContinue={()=>{updateEngagement(acknowledgeStage(projectRef.current,'cloud'));visitJourney('review');}} onPreview={(provider)=>{setDesignView("board");setLevel("flow");setChatOpen(true);send(`Preview a concrete ${OPTION_NAMES[provider]} implementation of our working scope, using actual named services in data.service and explicit connections. Keep existing systems and comments. Use the known country/residency constraints, or leave region undecided and ask the country question. This is an alternative preview, not a cloud choice or deployment. Return a graph proposal and explain key integration assumptions.`,"preview",{mode:"design",view:"board"});}} onDiscuss={(question) => { setChatOpen(true); send(question, "workflow"); }} />
        )}
        {mode === "design" && ["options","decisions","location"].includes(designView) && <LocationChoices project={project} onChange={commit} onDiscuss={()=>{setChatOpen(true);send('Review the accepted cloud, data country and cloud region. Ask one material unresolved location question. Preserve selected regions and residency.','workflow');}}/>}
        </div>
        {mode === "design" && designView === "requirements" && (
          <RequirementsView onDocumentChange={command=>{
            const next=updateRequirementsDocument(projectRef.current,command);
            validateImport(next);
            toProjectFile(next);
            updateEngagement(next);
            return next;
          }} onCommentSave={saveDesignComment} renderComments={renderDesignComments} checks={specificationChecks} onContinue={()=>{updateEngagement(acknowledgeStage(projectRef.current,'scope'));visitJourney('cloud');}} onUpload={()=>{setChatOpen(true);requirementsInput.current.click();}} onOpenProject={()=>setModal("project-file")} project={project} onChange={updateEngagement} reviewing={agentBusy} onReview={(comments)=>{setChatOpen(true);send("Propose revisions for these user comments on the requirements document. The document will remain unchanged until the user applies each suggestion. Explain the proposed change; never say you have already changed the document. Return requirementUpdates for the existing IDs where the feedback is clear, quoting the user's comment exactly in sourceText. Preserve other requirements and the diagram. Ask one question if a comment is ambiguous.\n" + comments.map(c=>`Requirement ${c.requirementId}${c.selectedText ? ` (selected text: ${c.selectedText.slice(0,300)})` : ""} — comment: ${c.text}`).join("\n"), "document");}} onDiscuss={(question) => { setChatOpen(true); send(question, "workflow"); }} />
        )}
      </main>


      {chatOpen&&!buildView && (
        <aside className={`chat ${idleChat?"idle":""}`} aria-label="Chat"><ChatResizeHandle width={chatWidth} onChange={resizeChat}/>
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
            {HOSTED?<span className="model"><span className={`led ${connection&&session?'on':''}`}/>{connection?.model?.split('/').at(-1)} · Medium</span>:<>
            <button className="model" onClick={() => showConnections()} title="AI providers">
              <span className={`led ${connection && session ? "on" : ""}`} />
              {connection ? `${connection.model}${connection.effort ? ` · ${EFFORT_LABEL[connection.effort] || connection.effort}` : ""}` : "Connect a model"}
            </button></>}
            <span className="chat-top-utilities">
              {hasIntroduction&&<button type="button" aria-expanded={introOpen} onClick={()=>setIntroOpen(value=>!value)}>{introOpen?'▾':'▸'} Introduction</button>}
              {session&&<button type="button" className="icon" aria-label="Voice settings" title="Voice settings" onClick={()=>setVoiceOpenRequest(value=>value+1)}><Volume2 size={15}/></button>}
            </span>
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
          <div className="chat-body">
          <section className="chat-history" aria-label="Chat history"><h2 className="chat-history-label">Chat history</h2>
          <div className="messages" ref={chatScroll.viewport}>
            <div className="message-list" ref={chatScroll.content}>
            {architectureChatEntries(project,messages).filter(entry=>entry.kind==='message'?entry.index>=chatView.start:entry.kind==='activity'?!chatView.turnIds.includes(entry.turn.id):entry.kind==='legacy-activity'?entry.entries.some(item=>!chatView.turnIds.includes(item.turn.id)):true).map(entry=>{
              if(entry.kind==='activity-error')return <p key="activity-error" role="alert">{entry.error}</p>;
              if(entry.kind==='legacy-activity')return <EarlierArchitectureActivity key={entry.id} entries={entry.entries} projectId={project.id} session={session}/>;
              if(entry.kind==='activity')return <ArchitectureTurn key={project.id+':'+entry.turn.id} turn={entry.turn} number={entry.number} projectId={project.id} session={session} active={agentBusy&&entry.turn.clientStatus==='submitted'&&entry.turn.id===latestArchitectureTurn?.id} working={agentBusy&&entry.turn.clientStatus==='submitted'} onStop={()=>agentAbort.current?.abort()}/>;
              if(entry.index===0&&hasIntroduction&&!introOpen)return null;
              const m=entry.message,i=entry.index,turn=project.extensions?.architectureActivity?.turns?.find(t=>t.id===m.activityId),messageTime=m.createdAt||(m.role==='assistant'?turn?.completedAt:null)||turn?.startedAt;
              const changeRevision=/^Architecture updated to revision (\d+)\./.exec(m.text||'')?.[1];
              const changeScope=(m.text||'').split(/\r?\n/).find(line=>/^[+~−]\s/.test(line))?.replace(/^[+~−]\s*/,'');
              const changeLabel=(changeRevision?'Revision '+changeRevision:'Design change')+(changeScope?' · '+changeScope.split(/\s+/).slice(0,12).join(' '):'');
              return (
              <div key={i} className={`msg ${m.role}`}>
                <header className="message-meta"><span>{m.role==='user'?'You':'Architect'}</span><time dateTime={messageTime||undefined} title={messageTime?new Date(messageTime).toLocaleString():'No timestamp recorded'}>{messageTime?new Date(messageTime).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}):'—'}</time></header>{m.role==='assistant'&&/^(?:Applied:|Drew it:|Architecture updated to revision \d+\.)/.test(m.text)?<details className="chat-change"><summary>{changeLabel}</summary><ChatMessage text={m.text} concise/></details>:<ChatMessage text={m.text} concise={m.role==='assistant'}/>}
                {(m.workState==='queued'||m.workState==='processing'&&intake.some(q=>q.id===m.requestId))&&<small className="message-work-state">Queued for the next update <button className="link" onClick={()=>{updateIntake(intakeRef.current.filter(q=>q.id!==m.requestId));setRequestState([m.requestId],'cancelled');}}>Remove from queue</button><button className="link" onClick={()=>{if(input||attachments.length){notify('Your current draft is preserved. Send or clear it before editing a queued update.');return;}const queued=intakeRef.current.find(q=>q.id===m.requestId);if(!queued)return;setInput(queued.text);setAttachments(queued.attachments);updateIntake(intakeRef.current.filter(q=>q.id!==m.requestId));setRequestState([m.requestId],'cancelled');}}>Edit update</button>{m.attachments?.some(a=>!a.data)&&<button className="link" onClick={()=>{updateIntake(intakeRef.current.map(q=>q.id===m.requestId?{...q,attachments:[]}:q));setIntakePaused(false);}}>Continue with text only</button>}</small>}
                {!!m.attachments?.length&&<div className="sent-attachments">{m.attachments.map(a=><figure key={a.id}>{a.data&&a.mime.startsWith('image/')&&<img src={`data:${a.mime};base64,${a.data}`} alt={a.name}/>}<figcaption><Paperclip size={12}/>{a.name}{a.originalNotSaved && <small>Original file not saved; attach it again to review its contents.</small>}</figcaption></figure>)}</div>}
                {m.fix && (
                  <button className="btn fix" onClick={() => showConnections()}>
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
          </section>
          <div className="chat-compose-pane">
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
          {(agentBusy||generationPending||['starting','running'].includes(engineeringStatus?.state)||pricingState.busy||checking)&&<div className="chat-working-status" role="status" aria-live="polite"><BrainActivity size={26}/><span>{agentBusy?architectAction:generationPending?'Generating project files…':['starting','running'].includes(engineeringStatus?.state)?'Generating project files…':checking?'Running checks…':'Calculating costs…'}</span></div>}
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
            <label className="composer-label" htmlFor="architect-message">Your message</label>
            <textarea id="architect-message"
              onPaste={e=>{const files=[...e.clipboardData.files];if(files.length){e.preventDefault();void attachFiles(files);}}}
              ref={messageInput}
              aria-label="Your message"
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
              <ArrowUp size={15} /><span>Send</span>
            </button>
            </div>
          </form>
          {session&&<OpenAIVoicePanel hideTrigger openRequest={voiceOpenRequest} key={project.id} session={session} connection={connection} transportRef={openaiVoice} onConnections={()=>showConnections()} onStart={()=>{voice.current?.cancel();setVoiceError('');}} onTranscript={(text,automatic)=>{
            if(automatic&&!input.trim()&&!attachments.length){setInput(text);void send(text);}
            else setInput(current=>current+(current.trim()?' ':'')+text);
          }}/>}
          <div className="voice-status" role="status" aria-live="polite">
            {!voiceError&&["starting","transcribing"].includes(voiceState)&&<BrainActivity size={22}/>}
            {voiceError || ({ starting: "Opening microphone…", listening: "Dictating locally — review your words, then press Send.", transcribing: "Finishing your transcript…" }[voiceState] || "")}
          </div>
          </div>
          </div>
        </aside>
      )}

      <input type="file" id="requirements-file-input" ref={requirementsInput} accept={ATTACHMENT_ACCEPT} multiple hidden onChange={async e=>{const files=[...e.target.files];e.target.value='';if(!files.length||readingAttachments)return;const uploadOwner=projectRef.current.id;setReadingAttachments(true);setAttachmentError('');try{const live=sessionRef.current||await refreshSession();if(live?.engineeringEnabled&&!HOSTED){await receiveDesignSources(files,uploadOwner,live);return;}const added=await readAttachments(files,attachments);if(projectRef.current.id!==uploadOwner)return;const all=[...attachments,...added];setAttachments(all);setChatOpen(true);setInput('Read these requirements and diagrams. Summarise what you understand, propose requirements and a connected design, and ask one focused question about anything important that is unclear. Preserve existing systems and distinguish source facts from assumptions.');if(connection&&session){setReadingAttachments(false);void send('Read these requirements and diagrams. Summarise what you understand, propose requirements and a connected design, and ask one focused question about anything important that is unclear. Preserve existing systems and distinguish source facts from assumptions.','chat',null,null,{attachments:all});}else{showConnections();}}catch(error){setAttachmentError(error.message);notify(error.message);}finally{setReadingAttachments(false);}}}/>
      <input id="project-file-input" type="file" ref={fileRef} accept="application/json,.json" hidden onChange={importProject} />
      {toast && (
        <div className="toast" role="status">
          {toast === "Preparing documents and diagram exports…"&&<BrainActivity/>}{toast}
        </div>
      )}
      <StarPrompt offer={starOffer}/>

      {modal && (
        <div className="backdrop" onMouseDown={(e) => e.target === e.currentTarget && !(modal === "welcome" && !connection) && setModal(null)}>
          <section className={`modal ${modal==="memory"?"memory-modal":""}`} role="dialog" aria-modal="true" aria-label={modal==="save-as"?"Save as":modal}>
            {!(modal === "welcome" && !connection) && <button className="icon modal-close" onClick={() => setModal(null)} aria-label="Close dialog">
              <X size={16} />
            </button>}
            {modal === "save-as" ? <>
              <h2>Save as</h2>
              <form className="project-save-as" onSubmit={event=>{
                event.preventDefault();
                const name=String(new FormData(event.currentTarget).get('filename')).trim().replace(/[<>:"/\\|?*]/g,'-');
                if(!name){notify('Enter a file name.');return;}
                if(saveProjectFile(/\.json$/i.test(name)?name:`${name}.json`))setModal(null);
              }}>
                <label>File name<input name="filename" defaultValue={`${slug}.atmem-ai-architect.json`} required maxLength={200} autoFocus onFocus={event=>event.target.select()}/></label>
                <button className="btn primary" type="submit"><Download size={16}/>Download project</button>
              </form>
            </> : modal === 'edit-board-note' ? <form onSubmit={event=>{
              event.preventDefault();
              noteText(boardRecord,String(new FormData(event.currentTarget).get('note')||''));
              setModal(null);
            }}><h2>{recordNode?.data.drawingShape?'Edit shape label':'Edit comment'}</h2><textarea name="note" aria-label={recordNode?.data.drawingShape?"Label":"Comment"} rows={4} autoFocus defaultValue={project.nodes.find(row=>row.id===boardRecord)?.data.label}/>
              <button className="btn primary">Save</button></form> : modal === "project-file" ? (<><h2>Open project</h2><button className="btn primary" onClick={()=>{fileImportAsCopy.current=false;fileRef.current.click();}}>Open project</button></>) : modal === "memory" ? (
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
              <div><div className="row"><button className="btn" onClick={()=>setModal("project-file")}>Open project</button><button className="btn" onClick={saveCurrentProject} disabled={savingProject}>Save project</button><button className="btn" onClick={()=>setModal("save-as")}>Save as…</button></div><ProjectsDialog
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
                <h2>Reset board and context?</h2>
                <p>Start fresh with an empty board, chat, requirements and decisions. Your saved projects and model connection stay.</p>
                <div className="reset-actions">
                  <button className="btn primary" title="Download your project, then start a new one" aria-label="Save project and start over" onClick={() => {
                    if (!saveProjectFile()) return;
                    createOwnProject();
                  }}><Package size={18}/> Save & start new</button>
                  <button
                    className="btn" title="Start a new project without downloading this one" aria-label="Confirm reset board and context"
                    onClick={() => {
                      createOwnProject();
                    }}
                  >
                    <Trash2 size={18}/> Reset board and context
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
                purpose={buildRequest?.intent==='design'?'architecture':null}
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
                <h2>Licences</h2><p>AtMem · <a href={(HOSTED?'/architect/workspace/':'/')+'licenses/atmem-APACHE-2.0.txt'} target="_blank" rel="noreferrer">Apache 2.0</a></p>
                <p>draw.io graph engine · <a href={import.meta.env.BASE_URL+'drawio/LICENSE'} target="_blank" rel="noreferrer">Apache 2.0</a>{' · '}
                  <a href={import.meta.env.BASE_URL+'drawio/NOTICE'} target="_blank" rel="noreferrer">Notice</a>{' · '}<a href={import.meta.env.BASE_URL+'drawio/STENCIL-LICENSE'} target="_blank" rel="noreferrer">Stencil terms</a></p>
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

async function mountArchitect(){
 await connectHostedWorkspace();
 document.documentElement.dataset.theme=savedTheme();
 createRoot(document.getElementById("root")).render(<App />);
}
void mountArchitect().catch(error=>{
 const root=document.getElementById('root');root.replaceChildren();
 const message=document.createElement('p');message.textContent=error.message||'The workspace could not open.';
 const link=document.createElement('a');link.href='/architect';link.textContent='Return to Architect';root.append(message,link);
});
