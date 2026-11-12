import topicsFile from "../agent-skills/discovery/topics.json" with { type: "json" };
import { cleanAssumption, cleanQuestion, cleanRequirement } from "./records.mjs";
// The consultant's engagement record: brief, cloud options, decisions.
// Kept beside the design so every deliverable traces back to the board.

export const CRITERIA = [
  { id: "cost", label: "Cost", hint: "Build and run cost, licence fit, cost controls" },
  { id: "risk", label: "Risk", hint: "Delivery risk, skills, lock-in, vendor maturity" },
  { id: "scalability", label: "Scalability", hint: "Fleet size, latency, throughput, regions" },
  { id: "security", label: "Security", hint: "Identity, data residency, guardrails, compliance" },
];
export const OPTIONS = ["current", "aws", "azure", "gcp", "ibm"];
export const STATUSES = ["Proposed", "Accepted", "Superseded"];
// Discovery topics come from the agent skill, so the planner, UI and outputs agree.
export const BRIEF_FIELDS = [...topicsFile.topics]
  .sort((x, y) => x.order - y.order)
  .map((t) => ({ id: t.id, label: t.label, question: t.question, beginner: t.beginner, essential: t.essential }));
export const VERDICTS = ["Pursue", "Park", "Rule out"];
export const LEVELS = ["High", "Medium", "Low"];
export const GATE = [
  { id: "adoption", label: "Adoption evidence", hint: "Who used the prototype, and what changed?" },
  { id: "economics", label: "Value vs cost", hint: "Measured value against run and build cost" },
  { id: "risks", label: "Residual risk", hint: "Open risks and who accepted them" },
];

const text = (value, max = 2000) => {const result=String(value??"");if(result.length>max)throw Error(`A project field exceeds ${max.toLocaleString('en')} characters. Split it into linked requirements; no content was truncated.`);return result;};
const score = (value) => (Number.isInteger(value) && value >= 1 && value <= 5 ? value : null);

export function defaultAssessment() {
  return {
    weights: Object.fromEntries(CRITERIA.map((c) => [c.id, 1])),
    scores: Object.fromEntries(OPTIONS.map((o) => [o, Object.fromEntries(CRITERIA.map((c) => [c.id, null]))])),
    notes: Object.fromEntries(OPTIONS.map((o) => [o, ""])),
    current: "",
  };
}

export function cleanMeasures(list) {
  return list.slice(0, 10).flatMap((m) => {
    if (!m || !/^[a-z_][a-z0-9_.]{0,79}$/i.test(m.path || "") || ![">=", "<=", "=="].includes(m.op)) return [];
    const target =
      typeof m.target === "number" && Number.isFinite(m.target)
        ? m.target
        : typeof m.target === "boolean"
          ? m.target
          : text(m.target, 100);
    return [{ label: text(m.label || m.path, 150), path: m.path, op: m.op, target }];
  });
}

export function cleanEngagement(p) {
  for(const name of ['needs','assumptions','openQuestions','facts'])if(Array.isArray(p[name])&&p[name].length>300)throw Error(`The project has more than 300 ${name}; no records were truncated.`);
  const out = {};
  if (["maintenance", "churn"].includes(p.domain)) out.domain = p.domain;
  if (typeof p.id === "string" && p.id) out.id = text(p.id, 100);
  if (typeof p.createdAt === "string" && !isNaN(Date.parse(p.createdAt))) out.createdAt = p.createdAt;
  if (Array.isArray(p.needs)) out.needs = p.needs.slice(0, 300).map(cleanRequirement);
  if (Array.isArray(p.assumptions)) out.assumptions = p.assumptions.slice(0, 300).map(cleanAssumption);
  if (Array.isArray(p.openQuestions)) out.openQuestions = p.openQuestions.slice(0, 300).map(cleanQuestion);
  if (p.extensions && typeof p.extensions === "object" && !Array.isArray(p.extensions)) out.extensions = p.extensions;
  if (p.brief && typeof p.brief === "object") {
    // Older briefs used consultant headings; fold them into the discovery topics.
    const brief = Object.fromEntries(BRIEF_FIELDS.map(({ id }) => [id, text(p.brief[id])]));
    for (const [old, id] of Object.entries(topicsFile.legacy)) {
      const value = text(p.brief[old]).trim();
      if (value && !brief[id].includes(value)) brief[id] = brief[id] ? `${brief[id]}\n${value}` : value;
    }
    out.brief = brief;
  }
  if (Array.isArray(p.facts))
    out.facts = p.facts.slice(0, 300).map((f) => ({
      id: text(f?.id, 60),
      name: text(f?.name, 60),
      value: typeof f?.value === "number" || typeof f?.value === "boolean" ? f.value : text(f?.value, 100),
      unit: text(f?.unit, 40),
      text: text(f?.text, 300),
      madeAt: /^\d{4}-\d{2}-\d{2}$/.test(f?.madeAt) ? f.madeAt : new Date().toLocaleDateString("en-CA"),
      ...(f?.item ? { item: text(f.item, 40) } : {}),
      ...(f?.period ? { period: text(f.period, 40) } : {}),
      ...(f?.conflictsWith ? { conflictsWith: text(f.conflictsWith, 60) } : {}),
    }));
  if (typeof p.workflow === "string") out.workflow = text(p.workflow, 60);
  if (Array.isArray(p.asked)) out.asked = p.asked.slice(0, 100).map((a) => text(a, 80));
  if (p.lastAsked && typeof p.lastAsked === "object")
    out.lastAsked = Object.fromEntries(["id", "topic", "question", "beginner", "why"].map((k) => [k, text(p.lastAsked[k], 400)]));
  if (p.sketchOffered) out.sketchOffered = true;
  if (typeof p.conceptSig === "string") out.conceptSig = p.conceptSig.slice(0, 20000);
  if (p.choices && typeof p.choices === "object")
    out.choices = Object.fromEntries(Object.entries(p.choices).slice(0, 100).filter(([, v]) => typeof v === "boolean").map(([k, v]) => [text(k, 80), v]));
  if (p.reviewAccepted && typeof p.reviewAccepted === "object")
    out.reviewAccepted = Object.fromEntries(
      Object.entries(p.reviewAccepted)
        .slice(0, 200)
        .map(([k, v]) => [text(k, 300), { reason: text(v?.reason, 1000), owner: text(v?.owner, 120), date: text(v?.date, 10) }]),
    );
  if (p.estimate && typeof p.estimate === "object") {
    const num = (v) => (typeof v === "number" && Number.isFinite(v) && v >= 0 ? v : undefined);
    out.estimate = {
      ...(["small","medium","large","extra-large"].includes(p.estimate.projectSize) ? {projectSize:p.estimate.projectSize} : {}),
      details: (Array.isArray(p.estimate.details) ? p.estimate.details : []).slice(0, 500).map((l, i) => ({
        id: text(l?.id || `charge-${i + 1}`, 100), componentId: text(l?.componentId, 100),
        description: text(l?.description, 200), quantity: num(l?.quantity), price: num(l?.price),
        unit: text(l?.unit, 80), currency: text(l?.currency || "USD", 3).toUpperCase(),
        source: text(l?.source, 500), date: text(l?.date, 10), region: text(l?.region, 80), service: text(l?.service, 200),
      })),
      ...(p.estimate.consulting ? { consulting: {
        currency: text(p.estimate.consulting.currency || "USD", 3).toUpperCase(),
        phases: Object.fromEntries(["discovery", "design", "build", "test", "deploy"].map((id) => {
          const l = p.estimate.consulting.phases?.[id] || {};
          return [id, { lowDays: num(l.lowDays), days: num(l.days), highDays: num(l.highDays), rate: num(l.rate), basis: text(l.basis, 1000) }];
        })),
      } } : {}),
      usage: Object.fromEntries(Object.entries(p.estimate.usage || {}).filter(([, v]) => num(v) !== undefined).slice(0, 20).map(([k, v]) => [text(k, 40), v])),
      prices: Object.fromEntries(
        Object.entries(p.estimate.prices || {})
          .slice(0, 200)
          .map(([k, v]) => [
            text(k, 100),
            { price: num(v?.price), currency: text(v?.currency || "USD", 3).toUpperCase(), source: text(v?.source, 300), url: text(v?.url, 500), date: text(v?.date, 10), note: text(v?.note, 300), region: text(v?.region, 80), service: text(v?.service, 200), ...(num(v?.tierLimit) !== undefined ? { tierLimit:v.tierLimit } : {}) },
          ]),
      ),
      ...(num(p.estimate.low) !== undefined ? { low: p.estimate.low } : {}),
      ...(num(p.estimate.high) !== undefined ? { high: p.estimate.high } : {}),
    };
  }
  if (Array.isArray(p.useCases))
    out.useCases = p.useCases.slice(0, 20).map((u, i) => ({
      id: text(u?.id || `uc-${i + 1}`, 60),
      title: text(u?.title, 200),
      value: LEVELS.includes(u?.value) ? u.value : "Medium",
      risk: LEVELS.includes(u?.risk) ? u.risk : "Medium",
      fit: LEVELS.includes(u?.fit) ? u.fit : "Medium",
      verdict: VERDICTS.includes(u?.verdict) ? u.verdict : "Park",
      reason: text(u?.reason, 1000),
    }));
  if (p.gate && typeof p.gate === "object")
    out.gate = Object.fromEntries(GATE.map(({ id }) => [id, text(p.gate[id])]));
  if (p.assessment && typeof p.assessment === "object") {
    const base = defaultAssessment();
    const a = p.assessment;
    out.assessment = {
      weights: Object.fromEntries(
        CRITERIA.map((c) => {
          const w = a.weights?.[c.id];
          return [c.id, Number.isInteger(w) && w >= 0 && w <= 5 ? w : 1];
        }),
      ),
      scores: Object.fromEntries(
        OPTIONS.map((o) => [o, Object.fromEntries(CRITERIA.map((c) => [c.id, score(a.scores?.[o]?.[c.id])]))]),
      ),
      notes: Object.fromEntries(OPTIONS.map((o) => [o, text(a.notes?.[o], 1000)])),
      current: text(a.current ?? base.current, 1000),
    };
  }
  if (Array.isArray(p.decisions))
    out.decisions = p.decisions.slice(0, 200).map((d, i) => ({
      id: text(d?.id || `adr-${i + 1}`, 60),
      subject: text(d?.subject || `general.${d?.id || i + 1}`, 120),
      title: text(d?.title, 200),
      owner: text(d?.owner, 120),
      status: STATUSES.includes(d?.status) ? d.status : "Proposed",
      date: /^\d{4}-\d{2}-\d{2}$/.test(d?.date) ? d.date : new Date().toLocaleDateString("en-CA"),
      context: text(d?.context),
      options: text(d?.options),
      decision: text(d?.decision),
      consequences: text(d?.consequences),
      revision: Number.isInteger(d?.revision) ? d.revision : null,
      supersedes: d?.supersedes ? text(d.supersedes, 60) : null,
      supersededBy: d?.supersededBy ? text(d.supersededBy, 60) : null,
      reason: text(d?.reason, 1000),
    }));
  return out;
}

// Weighted mean on the 1–5 scale; null until every weighted criterion is scored.
export function optionScore(assessment, option) {
  const scores = assessment.scores[option];
  let total = 0,
    weight = 0;
  for (const c of CRITERIA) {
    const w = assessment.weights[c.id];
    if (!w) continue;
    if (scores[c.id] == null) return null;
    total += w * scores[c.id];
    weight += w;
  }
  return weight ? Math.round((total / weight) * 10) / 10 : null;
}

export function newDecision(project, fields = {}) {
  const decisions = project.decisions || [];
  const n = Math.max(0, ...decisions.map((d) => Number(/^adr-(\d+)$/.exec(d.id)?.[1] || 0))) + 1;
  const id = `adr-${String(n).padStart(3, "0")}`;
  return {
    id,
    subject: fields.subject || `general.${id}`,
    title: "",
    owner: "",
    status: "Proposed",
    date: new Date().toLocaleDateString("en-CA"),
    context: "",
    options: "",
    decision: "",
    consequences: "",
    revision: project.revision,
    supersedes: null,
    supersededBy: null,
    reason: "",
    ...fields,
  };
}

export function recommendationDecision(project, option, names) {
  const a = project.assessment || defaultAssessment();
  const line = (o) => {
    const s = optionScore(a, o);
    return `- ${names[o]}: ${s ?? "not fully scored"}${a.notes[o] ? ` — ${a.notes[o]}` : ""}`;
  };
  return newDecision(project, {
    subject: "platform.cloud",
    title: `Platform for ${project.domain === "maintenance" ? "predictive maintenance" : project.name}: ${names[option]}`,
    context: project.requirements || "",
    options: [
      `Weights: ${CRITERIA.map((c) => `${c.label} ×${a.weights[c.id]}`).join(", ")} (scores 1–5, higher is better).`,
      ...OPTIONS.map(line),
    ].join("\n"),
    decision: `Recommend ${names[option]}.`,
    consequences: "",
  });
}

// Proposals and templates replace the design, never the engagement record.
export function keepEngagement(next, current) {
  const kept = {};
  for (const key of ["id", "createdAt", "requirements", "brief", "useCases", "assessment", "decisions", "gate", "needs", "assumptions", "openQuestions", "extensions", "facts", "workflow", "asked", "lastAsked", "sketchOffered", "estimate", "reviewAccepted", "conceptSig", "choices"]) if (current[key] !== undefined) kept[key] = current[key];
  // The problem statement is the client's, not the design's.
  if (current.requirements?.trim()) kept.requirements = current.requirements;
  return { ...next, ...kept };
}

// Offline consultant answers for questions about the engagement itself.
export function consult(message, project) {
  const t = message.toLowerCase();
  const brief = project.brief || {};
  const cases = project.useCases || [];
  const open = BRIEF_FIELDS.filter((f) => !brief[f.id]?.trim());
  if (/ask next|next question|what should i ask/.test(t))
    return open.length
      ? `Ask about ${open[0].label.toLowerCase()}: “${open[0].question}”${open[1] ? `\n\nThen ${open[1].label.toLowerCase()}.` : ""}`
      : "The brief is complete. Play it back to the client to confirm, then qualify the use cases.";
  if (/summari[sz]e|what we know|play back/.test(t)) {
    const known = BRIEF_FIELDS.filter((f) => brief[f.id]?.trim());
    return [
      project.requirements ? `Problem: ${project.requirements}` : "Problem: not captured yet.",
      ...known.map((f) => `${f.label}: ${brief[f.id].replace(/\n/g, "; ")}`),
      open.length ? `Still unknown: ${open.map((f) => f.label.toLowerCase()).join(", ")}.` : "Nothing major unknown.",
    ].join("\n");
  }
  if (/viable|qualif|rule out|use cases?/.test(t)) {
    if (!cases.length)
      return "No use cases listed yet. Add each one you heard in Discover. Pursue only what is high value with acceptable risk and a clear strategic fit; rule out the rest explicitly so nobody invests in them by accident.";
    const by = (v) => cases.filter((c) => c.verdict === v).map((c) => c.title || "untitled");
    const risky = cases.filter((c) => c.verdict === "Pursue" && (c.risk === "High" || c.value === "Low"));
    return [
      `Pursue: ${by("Pursue").join(", ") || "none"}.`,
      `Park: ${by("Park").join(", ") || "none"}.`,
      `Ruled out: ${by("Rule out").join(", ") || "none"}.`,
      ...risky.map((c) => `Check “${c.title}”: marked Pursue with ${c.risk === "High" ? "high risk" : "low value"}. Is that defensible?`),
    ].join("\n");
  }
  if (/evidence|scale|go live|production/.test(t))
    return "Scale only when value demonstrably exceeds cost and risk. Before scaling, record in Build: who used the prototype and what changed (adoption), measured value against run and build cost (economics), and the open risks with who accepted them. Every success measure should pass on the current design.";
  return null;
}
