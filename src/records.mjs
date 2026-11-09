// Project records beside the diagram: requirements, assumptions, open questions,
// and decisions with supersession history. See specs/002-project-model.

export const REQUIREMENT_KINDS = ["functional", "nonfunctional"];
export const CATEGORIES = [
  "security",
  "reliability",
  "availability",
  "scalability",
  "performance",
  "maintainability",
  "cost",
  "compliance",
  "other",
];
export const PRIORITIES = ["must", "should", "could"];
export const REQUIREMENT_STATUSES = ["open", "met", "at-risk", "not-met"];
export const SOURCES = ["user", "agent", "import"];
export const OPS = [">=", "<=", "=="];

const text = (value, max = 2000) => {const result=String(value??"");if(result.length>max)throw Error(`A project record exceeds ${max.toLocaleString('en')} characters; split it into linked records. No content was truncated.`);return result;};
const pick = (value, allowed, fallback) => (allowed.includes(value) ? value : fallback);
const links = (value) => {if(Array.isArray(value)&&value.length>50)throw Error("A record links more than 50 components; no links were truncated.");return Array.isArray(value)?value.map(id=>text(id,100)).filter(Boolean):[];};
const today = () => new Date().toLocaleDateString("en-CA");
const day = (value) => (/^\d{4}-\d{2}-\d{2}$/.test(value) ? value : today());
const uid = (prefix) => `${prefix}-${crypto.randomUUID().slice(0, 8)}`;

// A measure needs a numeric target when compared with >= or <=.
export function measureProblem(measure) {
  if (!measure) return null;
  if (!text(measure.metric).trim()) return "Name the metric.";
  if (!OPS.includes(measure.op)) return "Choose >=, <= or ==.";
  if (measure.op !== "==" && (typeof measure.target !== "number" || !Number.isFinite(measure.target)))
    return "Use a number for >= and <= targets.";
  return null;
}

function cleanMeasure(m) {
  if (!m || typeof m !== "object") return null;
  const target =
    typeof m.target === "number" && Number.isFinite(m.target)
      ? m.target
      : typeof m.target === "boolean"
        ? m.target
        : text(m.target, 100);
  const measure = { metric: text(m.metric, 150), op: m.op, target, unit: text(m.unit, 40) };
  return measureProblem(measure) ? null : measure;
}

export function cleanRequirement(r) {
  const measure = cleanMeasure(r?.measure);
  return {
    id: text(r?.id || uid("req"), 60),
    kind: pick(r?.kind, REQUIREMENT_KINDS, "functional"),
    category: pick(r?.category, CATEGORIES, "other"),
    statement: text(r?.statement, 1000),
    ...(r?.rationale ? {rationale:text(r.rationale,1000)} : {}),
    ...(r?.basis ? {basis:text(r.basis,1000)} : {}),
    priority: pick(r?.priority, PRIORITIES, "should"),
    status: pick(r?.status, REQUIREMENT_STATUSES, "open"),
    source: pick(r?.source, SOURCES, "user"),
    links: links(r?.links),
    ...(measure ? { measure } : {}),
  };
}

export function cleanAssumption(a) {
  return {
    id: text(a?.id || uid("asm"), 60),
    statement: text(a?.statement, 1000),
    source: pick(a?.source, SOURCES, "user"),
    owner: text(a?.owner, 120),
    links: links(a?.links),
    madeAt: day(a?.madeAt),
  };
}

export function cleanQuestion(q) {
  return {
    id: text(q?.id || uid("q"), 60),
    question: text(q?.question, 1000),
    owner: text(q?.owner, 120),
    status: q?.status === "answered" ? "answered" : "open",
    answer: text(q?.answer, 2000),
    links: links(q?.links),
  };
}

export const newRequirement = (fields = {}) => cleanRequirement({ kind: "nonfunctional", category: "performance", ...fields });
export const newAssumption = (fields = {}) => cleanAssumption(fields);
export const newQuestion = (fields = {}) => cleanQuestion(fields);

// Records that point at components no longer on the canvas.
export function missingLinks(project, record) {
  const ids = new Set(project.nodes.map((n) => n.id));
  return record.links.filter((id) => !ids.has(id));
}

export function linkedTo(project, componentId) {
  const has = (r) => r.links.includes(componentId);
  return {
    needs: (project.needs || []).filter(has),
    assumptions: (project.assumptions || []).filter(has),
    questions: (project.openQuestions || []).filter(has),
  };
}

// ---- Decisions ----

export const slugSubject = (title) =>
  text(title, 80)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "") || "general";

function nextDecisionId(decisions) {
  const max = Math.max(0, ...decisions.map((d) => Number(/^adr-(\d+)$/.exec(d.id)?.[1] || 0)));
  return `adr-${String(max + 1).padStart(3, "0")}`;
}

// Revise a decision: a new record becomes current, the old one is superseded and kept.
export function reviseDecision(project, id, changes, reason, revision = project.revision) {
  const decisions = project.decisions || [];
  const old = decisions.find((d) => d.id === id);
  if (!old) throw Error("Decision not found.");
  if (old.status === "Superseded") throw Error("This decision is already superseded; revise the current one.");
  if (!text(reason).trim()) throw Error("Give a reason for the change.");
  const next = {
    ...old,
    ...changes,
    id: nextDecisionId(decisions),
    subject: old.subject,
    status: "Accepted",
    date: today(),
    revision,
    supersedes: old.id,
    supersededBy: null,
    reason: text(reason),
  };
  return {
    ...project,
    decisions: [
      ...decisions.map((d) => (d.id === old.id ? { ...d, status: "Superseded", supersededBy: next.id } : d)),
      next,
    ],
  };
}

export function currentDecision(decisions = [], subject) {
  const live = decisions.filter((d) => d.subject === subject && d.status !== "Superseded");
  return live.at(-1) || null;
}

// Oldest first, ending with the current decision.
export function decisionHistory(decisions = [], subject) {
  const current = currentDecision(decisions, subject);
  if (!current) return [];
  const byId = new Map(decisions.map((d) => [d.id, d]));
  const chain = [current];
  const seen = new Set([current.id]);
  let at = current;
  while (at.supersedes && byId.has(at.supersedes) && !seen.has(at.supersedes)) {
    at = byId.get(at.supersedes);
    seen.add(at.id);
    chain.unshift(at);
  }
  return chain;
}
