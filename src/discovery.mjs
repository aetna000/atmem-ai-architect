// Gradual, open discovery driven by the agent skills in agent-skills/.
// The user describes things in their own words; we file what we heard, pull out
// numbers and quality needs, and ask the next easy question. Nothing is required.
import topicsFile from "../agent-skills/discovery/topics.json" with { type: "json" };
import workflowsFile from "../agent-skills/workflows/workflows.json" with { type: "json" };
import { PROVIDERS, pdmTemplate, template } from "./core.mjs";
import { newAssumption, newQuestion, newRequirement } from "./records.mjs";

export const TOPICS = [...topicsFile.topics].sort((a, b) => a.order - b.order);
export const WORKFLOWS = workflowsFile.workflows;
export const LEGACY_TOPICS = topicsFile.legacy;
const UNSURE = new RegExp(`\\b(${topicsFile.unsure})\\b`, "i");
const topic = (id) => TOPICS.find((t) => t.id === id);
const today = () => new Date().toLocaleDateString("en-CA");
const number = (s) => {
  const m = /^([\d.,]+)\s*(k|m)?$/i.exec(String(s).trim().replace(/\s+/g, ""));
  if (!m) return NaN;
  const n = Number(m[1].replace(/,/g, ""));
  return m[2]?.toLowerCase() === "k" ? n * 1000 : m[2]?.toLowerCase() === "m" ? n * 1e6 : n;
};
const PER_MONTH = { day: 30, week: 4.33, month: 1, year: 1 / 12, hour: 730 };

// How strongly some text points at a specialised skill: distinct cue words matched.
export function skillScore(w, text) {
  if (!w.detect) return 0;
  return new Set((String(text).match(new RegExp(w.detect, "gi")) || []).map((m) => m.toLowerCase())).size;
}
export function detectWorkflow(textContent) {
  const ranked = WORKFLOWS.filter((w) => w.detect)
    .map((w) => [w, skillScore(w, textContent)])
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1]);
  return ranked[0]?.[0] || null;
}

// Facts with values the review and estimate can use. Each keeps when it was said.
export function extractFacts(message) {
  const facts = [];
  const add = (name, value, unit, extra = {}) => facts.push({ name, value, unit, text: message.slice(0, 300), madeAt: today(), ...extra });
  const t = message.replace(/(\d),(\d{3})/g, "$1$2");
  const cloud = [
    ["aws", /\b(aws|amazon web services|bedrock|sagemaker)\b/i],
    ["azure", /\b(azure|microsoft cloud|foundry)\b/i],
    ["gcp", /\b(google cloud|gcp|vertex)\b/i],
    ["ibm", /\b(ibm|watsonx)\b/i],
  ].find(([, re]) => re.test(t));
  if (cloud) add("cloud.preference", cloud[0], "provider");
  const people = /(\d[\d.]*\s*k?)\s*(users|staff|people|customers|employees|agents|engineers|planners|members)/i.exec(t);
  if (people) add("users", number(people[1]), "users");
  const volume = /(\d[\d.]*\s*k?)\s*(questions|requests|queries|emails|tickets|invoices|messages|calls|chats|conversations|documents|forms|claims|orders)\s*(?:a|an|per|each|every)\s*(day|week|month|year|hour)/i.exec(t);
  if (volume) add("requests.per_month", Math.round(number(volume[1]) * PER_MONTH[volume[3].toLowerCase()]), "requests/month", { item: volume[2].toLowerCase() });
  const docs = /(\d[\d.]*\s*k?)\s*(documents|pdfs|files|pages|records)\b(?!\s*(?:a|an|per|each|every)\s)/i.exec(t);
  if (docs && !volume) add("documents", number(docs[1]), docs[2].toLowerCase());
  const size = /(\d[\d.]*)\s*(gb|tb|mb)\b/i.exec(t);
  if (size) add("data.gb", Number(size[1]) * { gb: 1, tb: 1000, mb: 0.001 }[size[2].toLowerCase()], "GB");
  const money = /(\b(?:US\$|AU\$|A\$|CA\$|C\$|NZ\$|usd|gbp|eur|aud|cad|nzd)|£|\$|€)\s?(\d[\d.]*\s*k?)\s*(?:a|per|\/)?\s*(month|year|mo)?/i.exec(t);
  if (money) {
    const symbol=money[1].toUpperCase();
    const currency=symbol==='$'?null:({"£":"GBP","€":"EUR",'US$':'USD','AU$':'AUD','A$':'AUD','CA$':'CAD','C$':'CAD','NZ$':'NZD'}[symbol]||symbol);
    const per = money[3]?.toLowerCase().startsWith("y") ? 1 / 12 : 1;
    add("budget.per_month", Math.round(number(money[2]) * per), `${currency||'currency unspecified'}/month`, { currency, period: money[3] ? "stated" : "assumed monthly" });
  }
  if (/\b(personal|pii|health|patient|medical|payment|card|salary|confidential|sensitive|gdpr)\b/i.test(t))
    add("data.sensitive", true, "flag");
  return facts;
}

// Quality statements with numbers become measurable requirements.
export function extractRequirements(message) {
  const found = [];
  const t = message;
  const latency = /within\s+(\d+(?:\.\d+)?)\s*(ms|milliseconds|s|sec|secs|seconds|minutes?)\b/i.exec(t);
  if (latency) {
    const unit = /^m(s|illi)/i.test(latency[2]) ? "ms" : /^min/i.test(latency[2]) ? "min" : "s";
    found.push(newRequirement({ kind: "nonfunctional", category: "performance", statement: `Responds within ${latency[1]} ${unit}`, priority: "should", measure: { metric: "p95 response time", op: "<=", target: Number(latency[1]), unit } }));
  }
  const avail = /(\d{2}(?:\.\d+)?)\s*%\s*(uptime|availab|of the time)?/i.exec(t);
  if (avail && (avail[2] || /availab|uptime/i.test(t)))
    found.push(newRequirement({ kind: "nonfunctional", category: "availability", statement: `Available ${avail[1]}% of the time`, priority: "should", measure: { metric: "monthly availability", op: ">=", target: Number(avail[1]), unit: "%" } }));
  else if (/\b(24\s*\/\s*7|always on|around the clock)\b/i.test(t))
    found.push(newRequirement({ kind: "nonfunctional", category: "availability", statement: "Available around the clock", priority: "should" }));
  else if (/\b(office|business|working) hours\b/i.test(t))
    found.push(newRequirement({ kind: "nonfunctional", category: "availability", statement: "Available during business hours", priority: "should" }));
  const region = /\b(?:stay|stays|kept|keep|remain|hosted|stored)\s+(?:in|within)\s+(?:the\s+)?(EU|Europe|UK|US|USA|Australia|Canada|Germany|India|Japan|[A-Z][a-z]+)\b/.exec(t);
  if (region)
    found.push(newRequirement({ kind: "nonfunctional", category: "compliance", statement: `Data stays in ${region[1]}`, priority: "must" }));
  if (/\b(person|human|someone|manager|staff|planner|agent)\s+(must\s+|should\s+|to\s+)?(approve|approves|review|reviews|check|checks|sign)/i.test(t))
    found.push(newRequirement({ kind: "functional", category: "security", statement: "A person approves sensitive actions before they happen", priority: "must" }));
  if (/\b(cite|citation|sources?|show where)\b/i.test(t) && /\b(answer|response)/i.test(t))
    found.push(newRequirement({ kind: "functional", category: "other", statement: "Every answer shows its sources", priority: "should" }));
  return found;
}

// Which question to ask next: topics in order after their prerequisites, then the workflow's.
export function nextQuestion(project) {
  const brief = project.brief || {};
  const asked = new Set(project.asked || []);
  const known = (id) => !!brief[id]?.trim();
  const workflow = WORKFLOWS.find((w) => w.id === project.workflow);
  const app = TOPICS.find((t) => t.id === "application");
  if (!known("application")) return { id: app.id, topic: app.id, question: app.question, beginner: app.beginner, why: app.why };
  // A consultant asks about the situation first: the workflow skill's own questions.
  if (workflow)
    for (const [i, q] of workflow.questions.entries()) {
      const id = `${workflow.id}:${i}`;
      if (!asked.has(id)) return { id, topic: q.topic, question: q.question, beginner: q.beginner, why: `It shapes the ${workflow.name} design.` };
    }
  // Then the general topics, with platform choices (cloud, budget) last.
  for (const t of TOPICS) {
    if (known(t.id) || asked.has(t.id) || !t.after.every(known)) continue;
    return { id: t.id, topic: t.id, question: t.question, beginner: t.beginner, why: t.why };
  }
  return null;
}

export function progress(project) {
  const brief = project.brief || {};
  return TOPICS.map((t) => ({
    ...t,
    state: brief[t.id]?.trim() ? (/^not sure/i.test(brief[t.id]) ? "assumed" : "known") : "open",
  }));
}
export const essentialsKnown = (project) => progress(project).every((t) => !t.essential || t.state !== "open");

// File one message. Returns the updated project fields and what to say back.
export function understand(message, project) {
  const brief = { ...(project.brief || {}) };
  const asked = [...(project.asked || [])];
  const lastAsked = project.lastAsked || null;
  const target = lastAsked?.topic || (brief.application?.trim() ? null : "application");
  const said = [];
  let needs = [...(project.needs || [])],
    assumptions = [...(project.assumptions || [])],
    openQuestions = [...(project.openQuestions || [])],
    facts = [...(project.facts || [])];
  let workflow = project.workflow || null;

  const file = (id, text) => {
    brief[id] = brief[id]?.trim() ? `${brief[id]}\n${text}` : text;
  };
  // Yes/no answers to a skill question decide whether its piece is drawn.
  const choices = { ...(project.choices || {}) };
  if (lastAsked?.id?.includes(":")) {
    if (/^\s*(yes|yeah|yep|sure|definitely|of course|absolutely|please do|y)\b/i.test(message)) choices[lastAsked.id] = true;
    else if (/^\s*(no|nope|not needed|don'?t|n)\b/i.test(message)) choices[lastAsked.id] = false;
  }
  if (target && UNSURE.test(message) && topic(target)?.ifUnsure) {
    const t = topic(target);
    file(target, `Not sure yet — assumed: ${t.ifUnsure}`);
    assumptions.push(newAssumption({ statement: t.ifUnsure, source: "agent", owner: "" }));
    openQuestions.push(newQuestion({ question: lastAsked?.question || t.question }));
    said.push(`No problem — for now let's assume ${t.ifUnsure.charAt(0).toLowerCase()}${t.ifUnsure.slice(1)} We'll confirm it later.`);
  } else if (target) {
    file(target, message);
  } else {
    // Unprompted: file under the topic the words most suggest, else the application.
    const guess =
      (/\b(aws|azure|google|gcp|ibm|cloud)\b/i.test(message) && "cloud") ||
      (/\b(users?|staff|customers|people|per (day|month))\b/i.test(message) && "users") ||
      (/\b(data|documents?|database|files|sharepoint|records)\b/i.test(message) && "data") ||
      (/\b(budget|£|\$|€|cost|deadline|timeline)\b/i.test(message) && "budget") ||
      (/\b(within|available|uptime|secure|approve|comply|gdpr)\b/i.test(message) && "quality") ||
      (/\b(crm|erp|salesforce|sap|servicenow|jira|zendesk|integrat|connect)\b/i.test(message) && "systems") ||
      "application";
    file(guess, message);
  }

  // Numbers and facts, wherever they appear.
  for (const f of extractFacts(message)) {
    const earlier = facts.find((x) => x.name === f.name && x.value !== f.value);
    facts.push({ id: `fact-${crypto.randomUUID().slice(0, 8)}`, ...f, ...(earlier ? { conflictsWith: earlier.id } : {}) });
    if (earlier) said.push(`Earlier you said ${earlier.value} ${earlier.unit} (${earlier.madeAt}); now ${f.value} ${f.unit}. Which is current? I've kept both.`);
    if (f.name === "cloud.preference" && (!brief.cloud?.trim() || /^not sure/i.test(brief.cloud))) {
      const unsure = /^not sure/i.test(brief.cloud || "");
      brief.cloud = PROVIDERS[f.value].name;
      const asked = topic("cloud").question;
      openQuestions = openQuestions.map((q) => (q.status === "open" && q.question === asked ? { ...q, status: "answered", answer: PROVIDERS[f.value].name } : q));
      if (target !== "cloud") said.push(`Noted your cloud: ${PROVIDERS[f.value].name}${unsure ? " (replacing the earlier assumption)" : ""}.`);
    }
  }
  const usage = facts.filter((f) => f.text === message.slice(0, 300) && ["users", "requests.per_month", "budget.per_month", "documents", "data.gb"].includes(f.name));
  if (usage.length) said.push(`Noted: ${usage.map((f) => `${f.value.toLocaleString("en")} ${f.unit}`).join(", ")}.`);
  if (facts.some((f) => f.name === "data.sensitive" && f.text === message.slice(0, 300)))
    said.push("Sensitive information noted — we'll check where it's stored and who can see it.");
  for (const r of extractRequirements(message)) {
    if (needs.some((n) => n.statement === r.statement)) continue;
    needs.push(r);
    said.push(`Added a requirement: ${r.statement.charAt(0).toLowerCase()}${r.statement.slice(1)}.`);
  }

  // Pick the skill that fits what's been said; switch when something else clearly fits better.
  const current = WORKFLOWS.find((w) => w.id === workflow);
  const specialised = !current || current.general;
  // First fit uses everything said; a switch needs the latest message to point clearly elsewhere.
  const best = detectWorkflow(specialised ? [...Object.values(brief), message].join(" ") : message);
  const fitsBetter =
    best &&
    best.id !== workflow &&
    (specialised || (skillScore(best, message) >= 2 && skillScore(best, message) > skillScore(current, message)));
  if (fitsBetter) {
    said.unshift(current && !current.general ? `This is really ${best.name} — switching skills.` : `Sounds like ${best.name} — ${best.summary}. I've started sketching it.`);
    workflow = best.id;
  } else if (!workflow && brief.application?.trim()) {
    workflow = "general";
  }
  if (!said.length) said.push(`Got it${target ? ` — noted under “${topic(target)?.label || "your answer"}”` : ""}.`);
  if (lastAsked) asked.push(lastAsked.id);

  const name = project.name === "New project" && brief.application?.trim() ? titleFrom(brief.application.split("\n")[0]) : project.name;
  const next = { ...project, name, brief, asked, needs, assumptions, openQuestions, facts, workflow, choices };
  const ask = nextQuestion(next);
  const ready = essentialsKnown(next) && !project.nodes?.length && !project.sketchOffered;
  const tail = [];
  if (ready) tail.push("We know enough for a first sketch — say “sketch it”.");
  if (ask) tail.push(`${ask.question}\n${ask.beginner}`);
  return {
    project: { ...next, lastAsked: ask, ...(ready ? { sketchOffered: true } : {}) },
    body: [...said, ...tail].join("\n\n"),
  };
}

// A project name from the user's own words, not the skill's.
export function titleFrom(text) {
  const t = String(text || "")
    .replace(/^\s*(hi|hello|hey)[,!.\s]+/i, "")
    .replace(/^\s*(i|we)('d| would)? (want|like|need)( to)?\s+/i, "")
    .replace(/^\s*(to\s+)?(build|create|make|add|set up|design)\s+/i, "")
    .trim();
  if (!t) return "New project";
  const cut = t.length > 42 ? `${t.slice(0, 42).replace(/\s+\S*$/, "")}…` : t;
  return cut.charAt(0).toUpperCase() + cut.slice(1).replace(/[.!]+$/, "");
}
export function opening(project) {
  const ask = nextQuestion(project);
  return ask ? `${ask.question}\n${ask.beginner}` : "Tell me what you'd like to change or add.";
}

// The RAG concept shows only what the user has said, or said yes to. Nothing is invented.
function ragConcept(workflow, project, provider) {
  const c = workflow.concept;
  // Only the user's own words shape the concept — never assumptions filled in for "not sure".
  const said = [...Object.values(project.brief || {}).flatMap((v) => String(v).split("\n")).filter((l) => !/^Not sure yet/i.test(l)), ...(project.facts || []).map((f) => f.text)].join(" ");
  const has = (re) => new RegExp(re, "i").test(said);
  const yes = (adds) => workflow.questions.some((q, i) => q.adds === adds && project.choices?.[`${workflow.id}:${i}`] === true);
  const label = (key) => c.labels[key][provider] || c.labels[key].generic;
  const provided = (key) => (c.labels[key][provider] ? provider : "tools");
  const nodes = [],
    edges = [];
  const add = (key, role, category, text, description, provider_ = "tools") => nodes.push({ key, role, category, text, description, provider: provider_ });
  const sources = c.sources.filter((x) => has(x.cue)).map((x) => x.label);
  (sources.length ? sources : [c.defaultSource]).forEach((src, i) => add(`src${i}`, "data", "Data", src, "Where the documents live"));
  if (has(c.index)) add("index", "index", "Data", label("index"), "Finds the passages that answer a question", provided("index"));
  const identity = has(c.sso) || yes("identity");
  const acl = has(c.permissions) || yes("acl");
  if (identity) add("identity", "guard", "Governance", label("identity"), "Who is asking", provided("identity"));
  if (acl) add("acl", "guard", "Governance", label("acl"), "Answers only from files the person may open");
  const rag = /\brag\b/i.test(said);
  add("llm", "llm", "Intelligence", rag ? `RAG · ${label("llm")}` : provider !== "tools" ? label("llm") : "AI that answers from them", `Answers from your documents${yes("citations") || has("cite|source") ? ", showing its sources" : ""}`, provided("llm"));
  if (has(c.guardrails)) add("guard", "guard", "Governance", label("guard"), "Blocks unsafe answers", provided("guard"));
  if (has(c.chat) || yes("channel")) add("chat", "app", "Delivery", c.channels.find((x) => has(x.cue))?.label || c.defaultChannel, "Where people ask questions");
  if (has(c.feedback)) add("feedback", "monitor", "Delivery", label("feedback"), "Tracks answer quality");
  const keys = new Set(nodes.map((n) => n.key));
  const into = keys.has("index") ? "index" : acl ? "acl" : "llm";
  nodes.filter((n) => n.key.startsWith("src")).forEach((n) => edges.push([n.key, into, "documents"]));
  if (keys.has("index")) edges.push(["index", acl ? "acl" : "llm", "passages"]);
  if (identity) edges.push(["identity", acl ? "acl" : "llm", "who is asking"]);
  if (acl) edges.push(["acl", "llm", "allowed documents"]);
  let last = "llm";
  if (keys.has("guard")) edges.push(["llm", "guard", "draft answer"]), (last = "guard");
  if (keys.has("chat")) edges.push([last, "chat", "answers"]);
  if (keys.has("feedback") && keys.has("chat")) edges.push(["chat", "feedback", "ratings"]);
  // Simple left-to-right placement by step.
  const depth = {};
  for (const n of nodes) depth[n.key] = 0;
  for (let i = 0; i < nodes.length; i++) for (const [a, b] of edges) depth[b] = Math.max(depth[b], depth[a] + 1);
  const row = {};
  for (const n of nodes) {
    const d = depth[n.key];
    n.at = [d, (row[d] = (row[d] ?? -1) + 1)];
  }
  return { nodes, edges };
}

// The general skill draws the three things every AI system has, named from the user's words.
function generalConcept(workflow, project, provider) {
  const c = workflow.concept;
  const said = [...Object.values(project.brief || {}).flatMap((v) => String(v).split("\n")).filter((l) => !/^Not sure yet/i.test(l)), ...(project.facts || []).map((f) => f.text)].join(" ");
  const has = (re) => new RegExp(re, "i").test(said);
  const nodes = [];
  const sources = c.sources.filter((x) => has(x.cue)).map((x) => x.label);
  sources.forEach((src, i) => nodes.push({ key: `src${i}`, role: "data", category: "Data", text: src, description: "Information it works with", provider: "tools" }));
  nodes.push({ key: "llm", role: "llm", category: "Intelligence", text: c.labels.llm[provider] || c.labels.llm.generic, description: "Does the AI work", provider: c.labels.llm[provider] ? provider : "tools" });
  const channel = c.channels.find((x) => has(x.cue));
  if (channel) nodes.push({ key: "use", role: "app", category: "Delivery", text: channel.label, description: "Where people use it", provider: "tools" });
  const edges = [...sources.map((_, i) => [`src${i}`, "llm", "data"]), ...(channel ? [["llm", "use", "results"]] : [])];
  nodes.forEach((n) => (n.at = [n.role === "data" ? 0 : n.role === "llm" ? 1 : 2, n.role === "data" ? Number(n.key.slice(3)) : 0]));
  return { nodes, edges };
}

// Fingerprint of a drawing, so we only redraw a concept the user hasn't changed by hand.
export const conceptSignature = (p) =>
  p.nodes.map((n) => `${n.data.label}|${n.data.role || n.data.kind}`).sort().join(";") + "#" + p.edges.map((e) => `${e.source}>${e.target}`).sort().join(";");

// A first sketch from the detected workflow and the cloud the user mentioned.
export function sketch(project) {
  const workflow = WORKFLOWS.find((w) => w.id === project.workflow) || WORKFLOWS.find((w) => w.general);
  const cloud = [...(project.facts || [])].reverse().find((f) => f.name === "cloud.preference")?.value;
  const provider = cloud || "tools";
  let next;
  if (workflow.template) {
    const maintenance = new RegExp(workflow.template.maintenance, "i").test(project.brief?.application || "");
    next = maintenance ? pdmTemplate(cloud || "aws") : template(cloud || "tools");
  } else if (workflow.concept) {
    const { nodes, edges } = (workflow.general ? generalConcept : ragConcept)(workflow, project, provider);
    next = {
      version: 1,
      revision: 1,
      name: project.name,
      provider,
      nodes: nodes.map((n) => ({
        id: n.key,
        type: "resource",
        position: { x: n.at[0] * 280, y: n.at[1] * 130 },
        data: { label: n.text, kind: "resource", role: n.role, category: n.category, provider: n.provider, description: n.description, config: { region: "To be selected", classification: n.role === "data" ? "Confidential" : "Internal", timeout: 5000 }, origin: n.role === "data" ? "existing" : "proposed" },
      })),
      edges: edges.map(([a, b, label]) => ({ id: `${a}-${b}`, source: a, target: b, type: "smoothstep", label })),
    };
  } else {
    const ids = Object.fromEntries(workflow.sketch.nodes.map((n, i) => [n.key, `${n.key}-${i}`]));
    next = {
      version: 1,
      revision: 1,
      name: project.name,
      provider,
      nodes: workflow.sketch.nodes.map((n, i) => ({
        id: ids[n.key],
        type: "resource",
        position: { x: i * 290, y: i % 2 ? 120 : 0 },
        data: {
          label: n.label[provider] || n.label.generic,
          kind: "resource",
          role: n.role,
          category: n.category,
          provider: n.label[provider] ? provider : "tools",
          description: n.description,
          config: { region: "To be selected", classification: "Internal", timeout: 5000 },
          origin: "proposed",
        },
      })),
      edges: workflow.sketch.edges.map(([a, b, label]) => ({ id: `${a}-${b}`, source: ids[a], target: ids[b], type: "smoothstep", label })),
    };
  }
  return {
    baseRevision: project.revision,
    title: `First sketch${cloud ? ` on ${PROVIDERS[cloud].name}` : ""}`,
    body: `A first ${workflow.name} sketch — ${workflow.summary}. ${cloud ? `Service names are ${PROVIDERS[cloud].name} suggestions to validate.` : "It stays provider-neutral until you pick a cloud."} Change anything on the board.`,
    next: { ...next, workflow: workflow.id },
  };
}
