import { runtimeSettings } from "./runtime-settings.mjs";
import { handoffAssessment } from './handoff.mjs';
import { journey } from "./journey.mjs";
import { requirementNumber } from "./derive.mjs";
import { estimate, consultingEstimate } from "./estimate.mjs";
import { resourcePlan } from "./resources.mjs";
import { toProjectFile } from "./project-file.mjs";

export function toAgentProject(p) {
  return {
    version: 1,
    revision: p.revision,
    name: p.name.slice(0, 200),
    provider: p.provider || "tools",
    ...(p.domain ? { domain: p.domain } : {}),
    requirements: String(p.requirements || ""),
    nodes: p.nodes.map((n) => ({
      id: n.id,
      type: "resource",
      position: n.position,
      data: {
        // A whitespace-only annotation also works with older sidecars requiring min_length=1.
        label: n.data.kind === "note" && !n.data.label ? " " : n.data.label,
        kind: n.data.kind,
        provider: n.data.provider,
        description: String(n.data.description || ""),
        config: {
          ...runtimeSettings(n.data.config),
          region: n.data.config?.region || "To be selected",
          classification: ["Public", "Internal", "Confidential"].includes(
            n.data.config?.classification,
          )
            ? n.data.config.classification
            : "Internal",
          timeout: 5000,
        },
        inputPosition: n.data.inputPosition || "left",
        outputPosition: n.data.outputPosition || "right",
        ...(n.data.topologyGroup ? {topologyGroup:String(n.data.topologyGroup)}:{}),
        ...(["reference","create"].includes(n.data.deploymentMode)?{deploymentMode:n.data.deploymentMode}:{}),
        origin: String(n.data.origin || "proposed").slice(0, 100),
        ...(n.data.service ? { service: n.data.service } : {}),
        ...(["cloud-storage-principal","aws-iam-principal","aws-bedrock-model","normalized-source-contract","web-browser","existing-service"].includes(n.data.binding) ? { binding: n.data.binding } : {}),
        ...(["container-service","private-object-storage","rag-web-app","rag-user-pool","bounded-keyword-rag","iam-rag-api","bounded-rag-catalog","text-statistics","bedrock-summary","async-word-count","sqs-standard","sqs-dead-letter","word-count-results"].includes(n.data.implementation) ? { implementation: n.data.implementation } : {}),
        ...(n.data.category ? { category: n.data.category } : {}),
        ...(n.data.poc ? { poc: true } : {}),
        ...(n.data.role ? { role: n.data.role } : {}),
        ...(n.data.measures?.length ? { measures: n.data.measures } : {}),
      },
    })),
    edges: p.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      type: "smoothstep",
      label: String(e.label || "data").slice(0, 150),
      ...(["storage-object-admin","s3-read", "s3-read-write", "lambda-invoke", "api-invoke"].includes(e.access) ? { access: e.access } : {}),
      ...(["browser-https","web-rag-api","oauth-pkce","jwt-authorizer","source-catalog-sync","http-api-lambda","lambda-catalog-read","bedrock-converse","s3-object-created","sqs-lambda","lambda-s3-read","lambda-dynamodb-write","sqs-redrive"].includes(e.integration) ? { integration: e.integration } : {}),
    })),
  };
}
// Read-only records for the architect: it may only change them through a proposal.
export function agentContext(p) {
  const item = (type, id, text) => ({ type, id: String(id).slice(0, 60), text: String(text).slice(0, 1000) });
  const measure = (m) => (m ? ` [${m.metric} ${m.op} ${m.target}${m.unit || ""}]` : "");
  const next = journey(p);
  const costs = estimate(p), work = consultingEstimate(p), resources = resourcePlan(p), handoff = handoffAssessment(p);
  return [
    item("discovery","guided-journey",`Current journey step: ${next.id} — ${next.title}. ${next.reason} Next action: ${next.action}. Improve the topology from known answers. Ask only a material question that unlocks the next design decision; defer packaging details. Later stages remain hidden until the working draft progresses; never direct the user to a hidden tab. Named service mapping is not verified cloud compatibility.`),
    item("discovery", "estimate-summary", `Current estimate stage: ${costs.maturity}. Monthly cloud subtotal ${costs.expected ?? "unknown"} ${costs.currency || "currency unresolved"}; range ${costs.low ?? "?"}–${costs.high ?? "?"}; ${costs.gaps.length} worksheet gaps. One-off consulting/build subtotal ${work.expected ?? "unknown"} ${work.currency}; ${work.complete ? "all phases entered" : "incomplete"}. Values are user inputs, not provider quotes. Later journey stages provide costs and a downloadable delivery draft with a Terraform sketch. Follow guided-journey before directing the user to those stages.`),
    ...costs.gaps.slice(0, 5).map((g, i) => item("question", `cost-gap-${i}`, g)),
    item("discovery", "infrastructure-coverage", `${resources.rows.length} diagram components; ${resources.gaps.length} infrastructure/integration gaps. Native Terraform coverage is AWS S3 foundations, typed text-statistics, asynchronous word counts, Bedrock summaries and explicit existing-IAM-principal access, plus typed private-object-storage with one existing cloud-storage-principal on Azure/GCP/IBM. Other AI application paths must retain their implementation gaps. Deployment is not connected.`),
    item("discovery", "handoff-readiness", `Handoff: ${handoff.status}; ${handoff.counts.priorityDecisions} priority decisions. Next: ${handoff.nextAction} Preserve accepted design decisions, distinguish country from deployment region, and resolve one highest-impact gap at a time. Do not equate schema validation with deployed behavior.`),
    ...handoff.findings.filter(f=>f.priority===1).slice(0,5).map(f=>item("question",`handoff-${f.id}`,`${f.message} ${f.action}`)),
    ...(p.needs || []).map((r) => item("requirement", r.id, `${requirementNumber(p,r.id)} — ${r.priority} ${r.kind} ${r.category}: ${r.statement}${measure(r.measure)} (${r.status})`)),
    ...(p.assumptions || []).map((a) => item("assumption", a.id, `${a.statement} (stated ${a.madeAt})`)),
    ...(p.openQuestions || []).filter(q=>q.status==='open'||q.answer?.trim()).map(q=>item('question',q.id,q.status==='answered'?`Answered: ${q.question} User-recorded answer: ${q.answer}`:q.question)),
    ...(p.decisions || [])
      .filter((d) => d.status !== "Superseded")
      .map((d) => item("decision", d.id, `${d.subject} — ${d.title}: ${d.decision} (${d.status}${d.owner ? `, owner ${d.owner}` : ""})`)),
    ...(p.lastAsked?.question ? [item("discovery", "next-question", `Optional planner candidate (${p.lastAsked.topic}; defer if a larger decision matters more): ${p.lastAsked.question} Beginner wording: ${p.lastAsked.beginner || ""}`)] : []),
    ...Object.entries(p.brief || {})
      .filter(([, v]) => String(v).trim())
      .map(([k, v]) => item("discovery", `brief-${k}`, `${k}: ${v}`)),
    ...(p.workflow ? [item("discovery", "workflow", `Detected workflow: ${p.workflow}`)] : []),
  ].slice(0, 300);
}
export async function discoverLocalAgent() {
  const response = await fetch("/api/session", {
    // Native account status probes can each take up to eight seconds.
    signal: AbortSignal.timeout(20000),
  });
  if (!response.ok) throw Error("Local sidecar unavailable");
  const session = await response.json();
  if (!session.token || session.status !== "local-sidecar")
    throw Error("Invalid local sidecar response");
  return session;
}
// Plain reasons instead of status codes or validation dumps.
export function explain(status, detail) {
  if (typeof detail === "string") return detail;
  if (status === 401) return "AtMem AI Architect's helper restarted, so this page lost its session. Reload the page.";
  if (status === 422 && Array.isArray(detail) && detail.length) {
    const d = detail[0];
    const where = (d.loc || []).filter((x) => x !== "body").join(" → ");
    return `Part of our request didn't fit (${where || "request"}: ${d.msg}). Reload the page; if it keeps happening, tell us what you were doing.`;
  }
  if (status === 409) return "Still working on your last message — give it a moment.";
  if (status >= 500) return "The model didn't answer. Let's check the connection.";
  return "Something went wrong talking to the model. Let's check the connection.";
}
export async function requestArchitect({
  session,
  connection,
  message,
  project,
  history,
  stage = "discover",
  origin = "chat",
  extra = [],
  attachments = [],
  signal,
}) {
  const scoped = project.id && !/^Connection check/.test(message);
  if (scoped) {
    try { await memoryCall(session, "sync", { projectId: project.id, file: toProjectFile(project) }, signal); }
    catch (error) { if (error.name === "AbortError") throw error; }
  }
  const response = await fetch("/api/architect", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.token}`,
    },
    body: JSON.stringify({
      provider: connection.provider,
      ...(scoped ? { projectId: project.id } : {}),
      origin,
      model: connection.model,
      ...(connection.effort ? { effort: connection.effort } : {}),
      message,
      ...(attachments.length?{attachments:attachments.map(({name,mime,data})=>({name,mime,data}))}:{}),
      project: toAgentProject(project),
      stage,
      context: [...agentContext(project), ...extra].slice(0, 300),
      history: history
        .slice(-12)
        .map((m) => ({ role: m.role, text: m.text.slice(0, 12000) })),
    }),
    signal,
  });
  const result = await response.json();
  if (!response.ok) throw Error(explain(response.status, result.detail));
  return result;
}

export async function memoryCall(session, action, payload, signal) {
  if (!session?.token) throw Error("AtMem AI Architect's local service is not connected.");
  const response = await fetch(`/api/memory/${action}`, { method:"POST",headers:{"Content-Type":"application/json",Authorization:`Bearer ${session.token}`},body:JSON.stringify(payload),signal:signal || AbortSignal.timeout(30000) });
  const value = await response.json();
  if (!response.ok) throw Error(typeof value.detail === "string" ? value.detail : "The memory request was rejected.");
  return value;
}

// Projects saved by AtMem AI Architect's helper under the user's account on this computer.
export async function projects(session, action, body = {}) {
  const response = await fetch(`/api/projects/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.token}` },
    body: JSON.stringify(body),
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw Error(typeof result.detail === "string" ? result.detail : "Couldn't reach your saved projects.");
  return result;
}
