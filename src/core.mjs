import {validateArchitectureWork} from './architecture-work.mjs';
import {validateStateCustody} from './state-custody.mjs';
import {validateExternalReferences} from './external-identities.mjs';
import {validateDeploymentOwnership} from './deployment-ownership.mjs';
import { runtimeSettings } from "./runtime-settings.mjs";
import { UPSTREAM_DESCRIPTIONS } from "./upstream-catalog.mjs";
import { cleanEngagement, cleanMeasures } from "./engagement.mjs";
export const PROVIDERS = {
  aws: { name: "AWS", color: "#1f777c", letter: "a" },
  azure: { name: "Azure", color: "#2687d5", letter: "A" },
  gcp: { name: "Google Cloud", color: "#44956b", letter: "G" },
  ibm: { name: "IBM", color: "#6b6cce", letter: "ibm" },
  tools: { name: "Tools & data", color: "#7b879b", letter: "⌘" },
};
export const STAGES = ["Discovery", "Architecture", "Cost Analysis", "Review"];
export const CLOUDS = ["aws", "azure", "gcp", "ibm"];
export const KINDS = [
  "source",
  "predict",
  "agent",
  "guard",
  "output",
  "tool",
  "resource",
  "stream",
  "history",
  "features",
  "train",
  "registry",
  "monitor",
  "note",
];
// What a sketch block is for, when it has no runnable fixture (kind "resource").
export const ROLES = ["data", "ingest", "index", "llm", "guard", "human", "app", "output", "model", "monitor"];
// Blocks that start a flow: they take no input.
export const SOURCE_KINDS = ["source", "stream", "history"];
// Predictive maintenance building blocks, one row per cloud, in PDM_KINDS order.
const PDM_KINDS = ["stream", "history", "features", "train", "registry", "predict", "monitor", "agent", "guard"];
const PDM_LABELS = {
  aws: ["AWS IoT Core", "Amazon S3 maintenance history", "SageMaker feature pipeline", "SageMaker Pipelines training", "SageMaker Model Registry", "SageMaker endpoint", "SageMaker Model Monitor", "Amazon Bedrock", "Bedrock Guardrails + IAM"],
  azure: ["Azure IoT Hub", "Azure Data Lake maintenance history", "Azure ML feature pipeline", "Azure ML pipelines training", "Azure ML model registry", "Azure ML online endpoint", "Azure ML model monitoring", "Microsoft Foundry models", "Azure AI Content Safety + Entra ID"],
  gcp: ["Pub/Sub sensor ingestion", "BigQuery maintenance history", "Vertex AI Feature Store", "Vertex AI Pipelines training", "Vertex AI Model Registry", "Vertex AI endpoint", "Vertex AI Model Monitoring", "Gemini on Vertex AI", "Model Armor + Cloud IAM"],
  ibm: ["IBM Event Streams", "Db2 maintenance history", "watsonx.data feature pipeline", "watsonx.ai training", "watsonx.governance model inventory", "watsonx.ai deployment", "watsonx.governance monitoring", "watsonx.ai Granite", "watsonx.governance guardrails + IAM"],
};
const PDM_DESCRIPTIONS = [
  "Stream vibration, temperature and pressure readings",
  "Work orders and failure records",
  "Join readings with maintenance history into features",
  "Train the failure-risk model on history",
  "Version and approve models before use",
  "Score failure risk for each asset",
  "Watch for data and prediction drift",
  "Explain risk to engineers with cited evidence",
  "Block ungrounded or unauthorised insights",
];
export const CATALOG = [
  ["tools", "source", "Customer dataset", "Sample input records", "database"],
  [
    "tools",
    "predict",
    "Prediction service",
    "Existing analytics endpoint",
    "model",
  ],
  ["tools", "agent", "AI assistant", "Explain results with context", "agent"],
  [
    "tools",
    "guard",
    "Approval & policy",
    "Check access before output",
    "shield",
  ],
  [
    "tools",
    "output",
    "Response & assertions",
    "Verify the end-to-end result",
    "output",
  ],
  ["tools", "tool", "REST API", "Connect a business tool", "tool"],
  ["tools", "source", "PostgreSQL", "Relational data source", "database"],
  [
    "aws",
    "agent",
    "Amazon Bedrock",
    "Generative AI application layer",
    "agent",
  ],
  ["aws", "predict", "SageMaker AI", "Predictive model endpoint", "model"],
  ["aws", "source", "Amazon S3", "Object storage source", "database"],
  ["aws", "tool", "AWS Lambda", "Serverless integration", "tool"],
  ["aws", "guard", "IAM policy", "Identity & access boundary", "shield"],
  [
    "azure",
    "agent",
    "Microsoft Foundry",
    "Generative AI application layer",
    "agent",
  ],
  [
    "azure",
    "predict",
    "Azure Machine Learning",
    "Predictive model endpoint",
    "model",
  ],
  ["azure", "source", "Azure SQL", "Relational data source", "database"],
  ["azure", "tool", "Azure Functions", "Serverless integration", "tool"],
  [
    "azure",
    "guard",
    "Microsoft Entra ID",
    "Identity & access boundary",
    "shield",
  ],
  [
    "gcp",
    "agent",
    "Gemini on Google Cloud",
    "Generative AI application layer",
    "agent",
  ],
  [
    "gcp",
    "predict",
    "Vertex AI endpoint",
    "Predictive model endpoint",
    "model",
  ],
  ["gcp", "source", "BigQuery", "Analytics data source", "database"],
  ["gcp", "tool", "Cloud Run", "Application integration", "tool"],
  ["gcp", "guard", "Cloud IAM", "Identity & access boundary", "shield"],
  ["ibm", "agent", "watsonx.ai", "Generative AI application layer", "agent"],
  [
    "ibm",
    "predict",
    "watsonx model deployment",
    "Predictive model endpoint",
    "model",
  ],
  ["ibm", "source", "IBM Db2", "Relational data source", "database"],
  ["ibm", "tool", "watsonx Orchestrate", "Business tool orchestration", "tool"],
  ["ibm", "guard", "IBM Cloud IAM", "Identity & access boundary", "shield"],
  ...CLOUDS.flatMap((cloud) =>
    PDM_KINDS.map((kind, i) => [cloud, kind, PDM_LABELS[cloud][i], PDM_DESCRIPTIONS[i], kind]),
  ),
  ["tools", "tool", "Existing maintenance app", "Client's work-order system (API)", "tool"],
  ["tools", "output", "Success measures", "Check PoC success measures", "output"],
].map(([provider, kind, label, description, icon], i) => ({
  id: `component-${i}`,
  provider,
  kind,
  label,
  description: UPSTREAM_DESCRIPTIONS[label] || description,
  icon,
}));
const labels = {
  tools: [
    "Customer dataset",
    "Prediction service",
    "AI assistant",
    "Approval & policy",
    "Response & assertions",
  ],
  aws: [
    "Amazon S3",
    "SageMaker AI",
    "Amazon Bedrock",
    "IAM policy",
    "Response & assertions",
  ],
  azure: [
    "Azure SQL",
    "Azure Machine Learning",
    "Microsoft Foundry",
    "Microsoft Entra ID",
    "Response & assertions",
  ],
  gcp: [
    "BigQuery",
    "Vertex AI endpoint",
    "Gemini on Google Cloud",
    "Cloud IAM",
    "Response & assertions",
  ],
  ibm: [
    "IBM Db2",
    "watsonx model deployment",
    "watsonx.ai",
    "IBM Cloud IAM",
    "Response & assertions",
  ],
};
export function template(provider = "azure") {
  const kinds = ["source", "predict", "agent", "guard", "output"];
  const positions = [
    { x: 65, y: 170 },
    { x: 355, y: 170 },
    { x: 645, y: 170 },
    { x: 645, y: 395 },
    { x: 355, y: 395 },
  ];
  return {
    version: 1,
    revision: 1,
    name: "Predictive analytics → AI assistant",
    provider,
    nodes: kinds.map((kind, i) => ({
      id: `block-${i}`,
      type: "resource",
      position: positions[i],
      data: {
        label: labels[provider][i],
        kind,
        inputPosition: i === 3 ? "top" : i === 4 ? "right" : "left",
        outputPosition: i === 2 ? "bottom" : i === 3 ? "left" : "right",
        provider: i === 4 ? "tools" : provider,
        description: [
          "Read sample customer signals",
          "Call an existing prediction model",
          "Explain the prediction with evidence",
          "Enforce access and output policy",
          "Check response and evidence",
        ][i],
        config: {
          region: "To be selected",
          classification: "Internal",
          timeout: 5000,
        },
        origin: "proposed",
      },
    })),
    edges: kinds
      .slice(1)
      .map((_, i) => ({
        id: `wire-${i}`,
        source: `block-${i}`,
        target: `block-${i + 1}`,
        type: "smoothstep",
        label: ["records", "prediction", "draft response", "approved result"][
          i
        ],
        animated: false,
      })),
    requirements:
      "Help an analyst understand a churn prediction. Retain the existing prediction service; require evidence and authorised access.",
  };
}
export const DEFAULT_MEASURES = [
  { label: "Model precision", path: "training.precision", op: ">=", target: 0.8 },
  { label: "Warning lead time (days)", path: "prediction.days_to_failure", op: ">=", target: 7 },
  { label: "Insight grounded in sources", path: "grounded", op: "==", target: true },
  { label: "Planner approves every work order", path: "human_review", op: "==", target: true },
];
export function pdmTemplate(provider = "aws") {
  const at = (x, y) => ({ x: x * 290, y: y * 190 });
  const blocks = [
    ["sensors", "stream", at(0, 0)],
    ["history", "history", at(0, 1)],
    ["features", "features", at(1, 0)],
    ["training", "train", at(1, 1)],
    ["registry", "registry", at(2, 1)],
    ["endpoint", "predict", at(2, 0)],
    ["monitor", "monitor", at(3, 0)],
    ["insights", "agent", at(4, 0), { outputPosition: "bottom" }],
    ["guardrail", "guard", at(4, 1), { inputPosition: "top", outputPosition: "bottom" }],
    ["app", "tool", at(4, 2), { inputPosition: "top", outputPosition: "left" }],
    ["measures", "output", at(3, 2), { inputPosition: "right" }],
  ];
  const label = (id, i) =>
    id === "app" ? "Existing maintenance app" : id === "measures" ? "Success measures" : PDM_LABELS[provider][i];
  const description = (id, i) =>
    id === "app" ? "Client's work-order system; drafts orders for planners" : id === "measures" ? "Checks the PoC success measures" : PDM_DESCRIPTIONS[i];
  const wires = [
    ["sensors", "features", "readings"],
    ["history", "features", "work orders"],
    ["history", "training", "labelled failures"],
    ["training", "registry", "candidate model"],
    ["features", "endpoint", "features"],
    ["registry", "endpoint", "approved model"],
    ["endpoint", "monitor", "risk score"],
    ["monitor", "insights", "monitored score"],
    ["insights", "guardrail", "draft insight"],
    ["guardrail", "app", "approved insight"],
    ["app", "measures", "draft work order"],
  ];
  return {
    version: 1,
    revision: 1,
    name: `Predictive maintenance · ${PROVIDERS[provider].name}`,
    provider,
    domain: "maintenance",
    requirements:
      "Predict equipment failures early enough to plan maintenance, explain each alert to engineers with evidence, and raise draft work orders in the client's existing maintenance app. Planners approve every order.",
    nodes: blocks.map(([id, kind, position, sides = {}], i) => ({
      id,
      type: "resource",
      position,
      data: {
        label: label(id, i),
        kind,
        provider: ["app", "measures"].includes(id) ? "tools" : provider,
        description: description(id, i),
        inputPosition: sides.inputPosition || "left",
        outputPosition: sides.outputPosition || "right",
        config: { region: "To be selected", classification: id === "history" ? "Confidential" : "Internal", timeout: 5000 },
        origin: id === "app" ? "existing" : "proposed",
        poc: id !== "monitor",
        ...(id === "measures" ? { measures: DEFAULT_MEASURES } : {}),
      },
    })),
    edges: wires.map(([source, target, wire]) => ({
      id: `${source}-${target}`,
      source,
      target,
      type: "smoothstep",
      label: wire,
    })),
  };
}
export function checkProject(project) {
  const issues = [];
  // Comments are annotations: they never count as part of the system.
  const notes = new Set(project.nodes.filter((n) => n.data.kind === "note").map((n) => n.id));
  const p = notes.size ? { ...project, nodes: project.nodes.filter((n) => !notes.has(n.id)), edges: project.edges.filter((e) => !notes.has(e.source) && !notes.has(e.target)) } : project;
  const ids = new Set(p.nodes.map((n) => n.id));
  if (!p.nodes.length)
    issues.push({
      level: "error",
      text: "Add a source and connect an end-to-end flow.",
    });
  if (!p.nodes.some((n) => SOURCE_KINDS.includes(n.data.kind)))
    issues.push({ level: "error", text: "A data source is required." });
  if (!p.nodes.some((n) => n.data.kind === "output"))
    issues.push({
      level: "error",
      text: "Add a response block to verify the result.",
    });
  for (const e of p.edges)
    if (!ids.has(e.source) || !ids.has(e.target))
      issues.push({
        level: "error",
        text: "A connection points to a missing block.",
      });
  for (const n of p.nodes) {
    if (n.data.kind === "resource")
      issues.push({
        level: "warning",
        nodeId: n.id,
        text: `${n.data.label} is an architecture reference with no fixture executor.`,
      });
    if (!p.edges.some((e) => e.source === n.id || e.target === n.id))
      issues.push({
        level: "error",
        nodeId: n.id,
        text: `${n.data.label} is disconnected.`,
      });
    if (!SOURCE_KINDS.includes(n.data.kind) && !p.edges.some((e) => e.target === n.id))
      issues.push({
        level: "error",
        nodeId: n.id,
        text: `${n.data.label} has no input.`,
      });
    if (SOURCE_KINDS.includes(n.data.kind) && p.edges.some((e) => e.target === n.id))
      issues.push({
        level: "error",
        nodeId: n.id,
        text: `${n.data.label} is a source and cannot accept an input.`,
      });
    if (n.data.kind !== "output" && !p.edges.some((e) => e.source === n.id))
      issues.push({
        level: "error",
        nodeId: n.id,
        text: `${n.data.label} has no downstream result.`,
      });
  }
  try {
    orderProject(p);
  } catch {
    issues.push({
      level: "error",
      text: "The flow contains a cycle. This MVP supports directed flows.",
    });
  }
  const guards = new Set(
    p.nodes.filter((n) => n.data.kind === "guard").map((n) => n.id),
  );
  function unguarded(id, visited = new Set()) {
    if (guards.has(id)) return false;
    if (visited.has(id)) return false;
    visited.add(id);
    const n = p.nodes.find((n) => n.id === id);
    if (SOURCE_KINDS.includes(n?.data.kind)) return true;
    return p.edges
      .filter((e) => e.target === id)
      .some((e) => unguarded(e.source, new Set(visited)));
  }
  if (
    p.nodes.filter((n) => n.data.kind === "output").some((n) => unguarded(n.id))
  )
    issues.push({
      level: "error",
      text: "Every source-to-response path must pass through an access policy block.",
    });
  issues.push({
    level: "info",
    text: "Cloud resources are design components. Runs use local fixtures; no cloud APIs are called.",
  });
  return issues;
}
export function orderProject(p) {
  const remaining = new Set(p.nodes.map((n) => n.id)),
    result = [];
  while (remaining.size) {
    const next = p.nodes.filter(
      (n) =>
        remaining.has(n.id) &&
        !p.edges.some((e) => e.target === n.id && remaining.has(e.source)),
    );
    if (!next.length) throw Error("cycle");
    for (const n of next) {
      result.push(n);
      remaining.delete(n.id);
    }
  }
  return result;
}
function readPath(value, path) {
  return path.split(".").reduce((v, key) => (v == null ? undefined : v[key]), value);
}
export function checkMeasures(measures = [], payload = {}) {
  return measures.map((m) => {
    const value = readPath(payload, m.path);
    const pass =
      m.op === ">=" ? typeof value === "number" && value >= m.target
      : m.op === "<=" ? typeof value === "number" && value <= m.target
      : value === m.target;
    return { label: m.label, value: value ?? null, target: `${m.op} ${m.target}`, pass };
  });
}
// Predictive maintenance fixtures. Deterministic, local, no cloud calls.
function maintenanceBlock(kind, n, input, scenario) {
  if (kind === "stream")
    return {
      asset_id: "pump-P07",
      window: "last 14 days",
      coverage: scenario === "sensor-dropout" ? 0.55 : 0.98,
      readings: {
        vibration_rms: scenario === "sensor-dropout" ? null : 7.1,
        temperature_c: 82,
        pressure_bar: 5.2,
      },
      authorised: scenario !== "denied",
      source: "local-fixture",
    };
  if (kind === "history")
    return {
      asset_id: "pump-P07",
      hours_since_service: 1400,
      prior_failures: [{ work_order: "WO-1182", cause: "bearing wear", date: "2025-03-11" }],
    };
  if (kind === "train")
    return {
      model_version: "pdm-risk-v3",
      training: {
        precision: scenario === "weak-model" ? 0.72 : 0.84,
        recall: 0.78,
        dataset: "maintenance history 2019–2026 (fixture)",
      },
    };
  if (!input) throw Error("No input payload received.");
  if (kind === "features") {
    if (!input.readings) throw Error("Feature pipeline needs sensor readings.");
    if (input.coverage < 0.8)
      throw Error(`Data quality gate: sensor coverage ${Math.round(input.coverage * 100)}% is below the 80% minimum.`);
    return {
      ...input,
      features: {
        vibration_trend_14d: 0.35,
        temperature_delta_c: 9,
        hours_since_service: input.hours_since_service ?? null,
        similar_past_failures: input.prior_failures?.length ?? 0,
      },
    };
  }
  if (kind === "registry") {
    if (!input.model_version) throw Error("Registry needs a trained model version.");
    return { ...input, approved_model: input.model_version, model_card: "fixture model card" };
  }
  if (kind === "predict") {
    if (!input.features) throw Error("Model endpoint needs features. Connect the feature pipeline.");
    if (!input.approved_model) throw Error("No approved model version. Connect the model registry.");
    return {
      ...input,
      prediction: { failure_probability: 0.71, days_to_failure: 12, failure_mode: "bearing wear" },
    };
  }
  if (kind === "monitor") {
    if (!input.prediction) throw Error("Monitor needs predictions to watch.");
    if (scenario === "drift")
      throw Error("Drift detected: vibration feature PSI 0.31 exceeds 0.20. Retrain before trusting new scores.");
    return { ...input, drift: { psi: 0.07, status: "stable" } };
  }
  if (kind === "agent") {
    if (!input.prediction) throw Error("Insights need a risk score. Connect the model endpoint.");
    const grounded = scenario !== "ungrounded";
    return {
      ...input,
      answer: grounded
        ? `Pump P07: ${Math.round(input.prediction.failure_probability * 100)}% risk of ${input.prediction.failure_mode} within about ${input.prediction.days_to_failure} days. Vibration is up 35% over 14 days and temperature is 9 °C above baseline; the same pattern preceded WO-1182. Inspect at the next planned stop.`
        : "Pump P07 will probably fail soon; replace it this week.",
      evidence: grounded ? ["sensor.vibration_rms trend", "WO-1182 bearing wear", "maintenance manual §4.2"] : [],
      grounded,
      generated_by: "local-template (no LLM call)",
    };
  }
  if (kind === "guard") {
    if (!input.authorised) throw Error("Access denied: this fixture does not authorise the request.");
    if (input.answer && !input.grounded)
      throw Error("Guardrail blocked: the insight cites no maintenance records or manuals.");
    return { ...input, policy: "passed" };
  }
  if (kind === "tool") {
    if (scenario === "tool-error") throw Error("Existing maintenance app unavailable: work-order API timed out.");
    return {
      ...input,
      work_order: { id: "WO-DRAFT-2207", status: "draft", owner: "maintenance planner" },
      human_review: true,
    };
  }
  if (kind === "output") {
    if (input.policy !== "passed") throw Error("Assertion failed: access and grounding policy must pass.");
    const results = checkMeasures(n.data.measures, input);
    const missed = results.filter((r) => !r.pass);
    if (missed.length)
      throw Error(`Success measure not met: ${missed.map((r) => `${r.label} = ${r.value} (target ${r.target})`).join("; ")}.`);
    return { work_order: input.work_order, answer: input.answer, measures: results, status: "passed" };
  }
  throw Error("This block has no fixture for predictive maintenance.");
}
const MAINTENANCE_ONLY = ["stream", "history", "features", "train", "registry", "monitor"];
export function executeBlock(n, input, scenario = "happy") {
  const kind = n.data.kind;
  if (kind === "resource")
    throw Error(
      "Architecture reference has no executor. Assign a fixture behaviour explicitly.",
    );
  if (MAINTENANCE_ONLY.includes(kind) || input?.asset_id)
    return maintenanceBlock(kind, n, input, scenario);
  if (kind === "source")
    return {
      customer_id: "sample-1042",
      usage_drop: scenario === "missing" ? null : 0.42,
      support_tickets: 3,
      authorised: scenario !== "denied",
      source: "local-fixture",
    };
  if (!input) throw Error("No input payload received.");
  if (kind === "predict") {
    if (typeof input.usage_drop !== "number")
      throw Error("Schema check failed: usage_drop must be a number.");
    return {
      ...input,
      churn_probability: Number(
        Math.min(
          1,
          0.2 + input.usage_drop + input.support_tickets * 0.06,
        ).toFixed(2),
      ),
      model: "deterministic-test-fixture",
    };
  }
  if (kind === "agent") {
    if (typeof input.churn_probability !== "number")
      throw Error(
        "Agent needs a prediction. Connect the prediction service first.",
      );
    return {
      ...input,
      answer: `Customer ${input.customer_id} has a simulated churn score of ${Math.round(input.churn_probability * 100)}%. The fixture uses a ${Math.round(input.usage_drop * 100)}% usage drop and ${input.support_tickets} support tickets. This is a test explanation, not a causal conclusion.`,
      evidence: ["fixture.usage_drop", "fixture.support_tickets"],
      generated_by: "local-template (no LLM call)",
    };
  }
  if (kind === "guard") {
    if (!input.authorised)
      throw Error(
        "Access denied: this fixture does not authorise the request.",
      );
    return { ...input, policy: "passed" };
  }
  if (kind === "output") {
    if (input.policy !== "passed")
      throw Error("Assertion failed: access policy must pass.");
    if (!input.answer || !input.evidence?.length)
      throw Error(
        "Assertion failed: response and supporting evidence are required.",
      );
    return {
      answer: input.answer,
      evidence: input.evidence,
      assertions: {
        response_present: true,
        evidence_present: true,
        access_approved: true,
      },
      status: "passed",
    };
  }
  if (scenario === "tool-error")
    throw Error("Simulated tool failure: upstream API unavailable.");
  return { ...input, tool_result: "Local tool fixture succeeded" };
}
export function validateImport(p) {
  if (
    !p ||
    p.version !== 1 ||
    !Number.isInteger(p.revision) ||
    p.revision < 1 ||
    typeof p.name !== "string" ||
    !Array.isArray(p.nodes) ||
    !Array.isArray(p.edges) ||
    p.nodes.length > 200 ||
    p.edges.length > 600
  )
    throw Error("Unsupported or oversized project file.");
  if(String(p.requirements||"").length>64000)throw Error("Project requirements exceed 64,000 characters; no content was truncated.");
  if(p.extensions?.architectureWork!==undefined)validateArchitectureWork(p.extensions.architectureWork);
  validateStateCustody(p.extensions?.terraformState);
  validateExternalReferences(p);
  const ids = new Set();
  for (const n of p.nodes) {
    if (
      typeof n.id !== "string" ||
      ids.has(n.id) ||
      !n.data ||
      !Object.hasOwn(PROVIDERS, n.data.provider) ||
      !KINDS.includes(n.data.kind) ||
      typeof n.data.label !== "string" ||
      n.data.label.length > (n.data.kind === "note" ? 16000 : 150) ||
      !Number.isFinite(n.position?.x) ||
      !Number.isFinite(n.position?.y)
    )
      throw Error("Invalid component in project.");
    if(String(n.data.description||"").length>16000)throw Error("Component description exceeds 16,000 characters; split it into linked requirements. Nothing was truncated.");
    if(n.data.topologyGroup!=null&&(typeof n.data.topologyGroup!=="string"||n.data.topologyGroup.length>100))throw Error("Topology responsibility names must have at most 100 characters; no content was truncated.");
    validateDeploymentOwnership(n.data);
    ids.add(n.id);
  }
  const edgeIds = new Set();
  for (const e of p.edges) {
    if (
      typeof e.id !== "string" ||
      edgeIds.has(e.id) ||
      !ids.has(e.source) ||
      !ids.has(e.target) ||
      e.source === e.target
    )
      throw Error("Invalid connection in project.");
    edgeIds.add(e.id);
  }
  return {
    ...p,
    ...cleanEngagement(p),
    nodes: p.nodes.map((n) => ({
      id: n.id,
      type: "resource",
      position: n.position,
      data: {
        inputPosition: ["left", "right", "top", "bottom"].includes(
          n.data.inputPosition,
        )
          ? n.data.inputPosition
          : "left",
        outputPosition: ["left", "right", "top", "bottom"].includes(
          n.data.outputPosition,
        )
          ? n.data.outputPosition
          : "right",
        label: n.data.label,
        provider: n.data.provider,
        kind: n.data.kind,
        description: String(n.data.description || ""),
        config: {
          ...runtimeSettings(n.data.config),
          region: String(n.data.config?.region || "To be selected").slice(
            0,
            100,
          ),
          classification: String(
            n.data.config?.classification || "Internal",
          ).slice(0, 100),
          timeout: 5000,
        },
        ...(n.data.topologyGroup ? {topologyGroup:String(n.data.topologyGroup)}:{}),
        ...(["reference","create"].includes(n.data.deploymentMode)?{deploymentMode:n.data.deploymentMode}:{}),
        origin: String(n.data.origin || "proposed").slice(0, 100),
        ...(n.data.poc ? { poc: true } : {}),
        ...(["public-catalog-editor","cloud-storage-principal","aws-iam-principal","aws-bedrock-model","normalized-source-contract","web-browser","existing-service"].includes(n.data.binding) ? { binding: n.data.binding } : {}),
        ...(["invoice-workflow","public-faq-app","ibm-structured-app","gcp-structured-app","azure-structured-app","container-service","private-object-storage","rag-web-app","rag-user-pool","bounded-keyword-rag","iam-rag-api","bounded-rag-catalog","text-statistics","bedrock-summary","bedrock-structured","structured-api","structured-web-app","structured-user-pool","async-word-count","sqs-standard","sqs-dead-letter","word-count-results"].includes(n.data.implementation) ? { implementation: n.data.implementation } : {}),
        ...(ROLES.includes(n.data.role) ? { role: n.data.role } : {}),
        ...(Array.isArray(n.data.measures) ? { measures: cleanMeasures(n.data.measures) } : {}),
        ...(n.data.service
          ? { service: String(n.data.service).slice(0, 150) }
          : {}),
        ...(n.data.category
          ? { category: String(n.data.category).slice(0, 150) }
          : {}),
        ...(n.data.metadata
          ? {
              metadata: {
                columns: Array.isArray(n.data.metadata.columns)
                  ? n.data.metadata.columns
                      .slice(0, 100)
                      .map((c) => ({
                        name: String(c.name || "").slice(0, 100),
                        type: String(c.type || "").slice(0, 100),
                        isPrimaryKey: !!c.isPrimaryKey,
                        isForeignKey: !!c.isForeignKey,
                      }))
                  : [],
              },
            }
          : {}),
      },
    })),
    edges: p.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      type: "smoothstep",
      label: String(e.label || "data").slice(0, 80),
      ...(["storage-object-admin","s3-read", "s3-read-write", "lambda-invoke", "api-invoke"].includes(e.access) ? { access: e.access } : {}),
      ...(["approved-accounting-api","public-catalog-edit","browser-https","web-rag-api","oauth-pkce","jwt-authorizer","source-catalog-sync","http-api-lambda","lambda-catalog-read","bedrock-converse","s3-object-created","sqs-lambda","lambda-s3-read","lambda-dynamodb-write","sqs-redrive"].includes(e.integration) ? { integration: e.integration } : {}),
    })),
  };
}
export function propose(message, p) {
  const text = message.toLowerCase();
  const provider = text.includes("azure")
    ? "azure"
    : /google|gcp/.test(text)
      ? "gcp"
      : /ibm|watson/.test(text)
        ? "ibm"
        : /aws|bedrock|sagemaker/.test(text)
          ? "aws"
          : null;
  if (/compare|options|all (four|4)|which cloud/.test(text))
    return {
      action: "options",
      body: "Opening Options. Score the current approach, AWS, Azure, Google Cloud and IBM on cost, risk, scalability and security, then record the recommendation as a decision. Use “Show design” on any cloud to review its architecture as a proposal.",
    };
  if (/cost|price|spend/.test(text))
    return {
      body: "Main cost drivers for this design: always-on model endpoints, GenAI tokens per insight, sensor ingestion volume and feature storage. Compare them per cloud in Options; local patterns have no live pricing, so treat any figures as estimates to confirm with the client's account team.",
    };
  if (provider && (/maint|pdm|sensor|failure/.test(text) || p.domain === "maintenance"))
    return {
      baseRevision: p.revision,
      title: `Predictive maintenance on ${PROVIDERS[provider].name}`,
      body: `Draft a ${PROVIDERS[provider].name} predictive maintenance architecture: sensor ingestion and maintenance history → features → training, registry and endpoint → drift monitoring → GenAI insights behind a guardrail → draft work orders in the client's existing app. Service names are design choices to validate with the client.`,
      next: pdmTemplate(provider),
    };
  if (provider)
    return {
      baseRevision: p.revision,
      title: `Explore a ${PROVIDERS[provider].name} architecture`,
      body: `Replace the canvas with an illustrative ${PROVIDERS[provider].name} pattern: data → prediction → assistant → policy → response. This is a design alternative, not a validated service integration.`,
      next: template(provider),
    };
  if (/tool|api/.test(text) && p.domain !== "maintenance") {
    const next = structuredClone(p);
    const target = next.nodes.find((n) => n.data.kind === "agent");
    if (!target)
      return {
        body: "Add an assistant block first, then I can insert a tool before it.",
      };
    const id = `tool-${crypto.randomUUID()}`;
    next.nodes.push({
      id,
      type: "resource",
      position: { x: 645, y: -40 },
      data: {
        kind: "tool",
        provider: "tools",
        label: "Business API",
        description: "A local fixture for a business tool",
        config: {
          region: "Local fixture",
          classification: "Internal",
          timeout: 5000,
        },
        origin: "proposed",
      },
    });
    const incoming = next.edges.find((e) => e.target === target.id);
    if (incoming) {
      next.edges = next.edges.filter((e) => e.id !== incoming.id);
      next.edges.push({
        id: `${id}-in`,
        source: incoming.source,
        target: id,
        type: "smoothstep",
        label: "request",
      });
    }
    next.edges.push({
      id: `${id}-out`,
      source: id,
      target: target.id,
      type: "smoothstep",
      label: "tool context",
    });
    return {
      baseRevision: p.revision,
      title: "Connect a business tool",
      body: "Insert a REST API fixture before the assistant. In Staging / Test, choose “Tool unavailable” to see the failure propagate.",
      next,
    };
  }
  if (/review|risk|secur|valid/.test(text))
    return {
      body: `Local review: ${checkProject(p).filter((i) => i.level === "error").length} structural issues. Before real deployment, verify identity, network boundaries, data residency, endpoint contracts, and model evaluation. Cloud documentation and pricing are not connected in this MVP.`,
    };
  if (/test|run|fail|poc|proof/.test(text) && p.domain === "maintenance")
    return {
      body: "Open PoC and press Run. Try Sensor dropout, Weak model, Drift, Ungrounded insight or App unavailable to show stakeholders how each failure is caught. The success measures on the last block decide whether the PoC passes.",
    };
  if (/test|run|fail/.test(text))
    return {
      body: "Open Staging / Test and run a sample. Try “Missing input field” or “Access denied”. Click any executed block to inspect its input, output and error. Add a business API to test tool failures.",
    };
  return {
    body: "I’m the guided demo assistant; I use local patterns, not a live language model. I can draft predictive maintenance on AWS, Azure, Google Cloud or IBM, compare the four clouds, review risks, or explain the PoC tests. Connect a model in Connections for open-ended design.",
  };
}
export function makePlan(p, run, environment) {
  const tested = run?.status === "passed" && run.revision === p.revision;
  return {
    kind: "architecture-plan-only",
    environment,
    project: p.name,
    revision: p.revision,
    generatedAt: new Date().toISOString(),
    simulationPassed: tested,
    liveDeploymentEnabled: false,
    pocScope: p.nodes.filter((n) => n.data.poc).map((n) => n.data.label),
    blocks: p.nodes.map((n) => ({ id: n.id, ...n.data })),
    connections: p.edges,
    blockers: [
      ...(!tested ? ["Pass a simulation against the current revision."] : []),
      "Connect a cloud account and select target regions.",
      "Implement and verify provider-specific deployment adapters.",
      "Review IAM, networking, secrets, data residency and costs.",
      "Obtain staging integration-test results before production.",
    ],
    note: "This is not executable infrastructure code or evidence of a deployed environment.",
  };
}
