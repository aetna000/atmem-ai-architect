// Monthly run-cost estimate. See specs/004-cost-estimate.
// Every line is quantity (from usage inputs) × unit price (entered with a source).
// No prices ship with AtMem AI Architect; a missing input or price leaves the estimate incomplete.
import { roleOf } from "./review.mjs";

export const DISCLAIMER = "Estimate — not a bill or guarantee.";

export const INPUTS = [
  { id: "requests_per_month", label: "Requests per month", unit: "requests", fact: "requests.per_month" },
  { id: "tokens_per_request", label: "Tokens per request (in + out)", unit: "tokens", hint: "A short question and answer with a few retrieved passages is often 2,000–4,000 tokens." },
  { id: "data_gb", label: "Data stored", unit: "GB", fact: "data.gb" },
  { id: "endpoint_hours", label: "Model endpoint hours per month", unit: "hours", assumption: 730, assumptionText: "always on (730 h/month)" },
  { id: "events_per_month", label: "Events or messages per month", unit: "events" },
  { id: "training_hours", label: "Training hours per month", unit: "hours" },
];

// Planning assumptions, not provider prices or capacity guarantees. Explicit inputs
// and discovered business facts always take precedence over these presets.
export const PROJECT_SIZES = Object.freeze([
  {id:'small', label:'Small', requests_per_month:10000, data_gb:10, events_per_month:10000},
  {id:'medium', label:'Medium', requests_per_month:100000, data_gb:100, events_per_month:100000},
  {id:'large', label:'Large', requests_per_month:1000000, data_gb:1000, events_per_month:1000000},
  {id:'extra-large', label:'Extra Large', requests_per_month:10000000, data_gb:10000, events_per_month:10000000},
].map(size=>Object.freeze({...size,tokens_per_request:3000,endpoint_hours:730})));
export function setProjectSize(project, id) {
  if (!PROJECT_SIZES.some(size=>size.id===id)) throw Error('Choose a listed project size.');
  return {...project,estimate:{...project.estimate,projectSize:id}};
}

// role/kind → how it is charged
const DRIVERS = {
  llm: { name: "Model tokens", unit: "1k tokens", inputs: ["requests_per_month", "tokens_per_request"], qty: (u) => (u.requests_per_month * u.tokens_per_request) / 1000 },
  index: { name: "Index storage", unit: "GB-month", inputs: ["data_gb"], qty: (u) => u.data_gb },
  ingest: { name: "Data processed", unit: "GB", inputs: ["data_gb"], qty: (u) => u.data_gb },
  data: { name: "Storage", unit: "GB-month", inputs: ["data_gb"], qty: (u) => u.data_gb },
  model: { name: "Endpoint hours", unit: "hours", inputs: ["endpoint_hours"], qty: (u) => u.endpoint_hours },
  guard: { name: "Checked requests", unit: "1k requests", inputs: ["requests_per_month"], qty: (u) => u.requests_per_month / 1000 },
  stream: { name: "Messages", unit: "million events", inputs: ["events_per_month"], qty: (u) => u.events_per_month / 1e6 },
  train: { name: "Training hours", unit: "hours", inputs: ["training_hours"], qty: (u) => u.training_hours },
};
function driverOf(n) {
  if (n.data.kind === "stream") return DRIVERS.stream;
  if (n.data.kind === "train") return DRIVERS.train;
  return DRIVERS[roleOf(n)] || null;
}

// Usage values with where they came from: entered, discovery, or a stated assumption.
export function usage(project) {
  const est = project.estimate || {};
  const facts = project.facts || [];
  return Object.fromEntries(
    INPUTS.map((i) => {
      const entered = est.usage?.[i.id];
      const fromFact = i.fact && [...facts].reverse().find((f) => f.name === i.fact);
      if (Number.isFinite(entered) && entered >= 0) return [i.id, { value: entered, source: "entered" }];
      if (fromFact && Number.isFinite(fromFact.value) && fromFact.value >= 0) return [i.id, { value: fromFact.value, source: `discovery (${fromFact.madeAt})` }];
      const preset = PROJECT_SIZES.find(size=>size.id===est.projectSize);
      if (preset && Number.isFinite(preset[i.id])) return [i.id, {value:preset[i.id], source:`${preset.label} planning assumption`}];
      if (i.assumption != null) return [i.id, { value: i.assumption, source: `assumption: ${i.assumptionText}` }];
      return [i.id, { value: null, source: "needed" }];
    }),
  );
}

export function estimate(project, now = new Date()) {
  const est = project.estimate || {};
  const u = usage(project);
  const values = Object.fromEntries(Object.entries(u).map(([k, v]) => [k, v.value]));
  const low = Number.isFinite(est.low) && est.low >= 0 && est.low <= 1 ? est.low : 0.7;
  const high = Number.isFinite(est.high) && est.high >= 1 ? est.high : 1.5;
  const lines = [];
  const notCosted = [];
  for (const n of project.nodes.filter((x) => x.data.kind !== "note")) {
    const detail = (est.details || []).filter((l) => l.componentId === n.id);
    if (detail.length) {
      for (const l of detail) {
        const validNumber = (v) => Number.isFinite(v) && v >= 0;
        const missing = validNumber(l.quantity) ? [] : ["quantity"];
        const priced = validNumber(l.price) && /^[A-Z]{3}$/.test(l.currency || "") && l.source?.trim() && l.unit?.trim();
        lines.push({ id: l.id, component: n.data.label, componentId: n.id, detailed: true,
          driver: l.description || "Charge", unit: l.unit, inputs: [], quantity: missing.length ? null : l.quantity,
          missing, note:l.note, price: priced ? l : null,
          cost: !missing.length && priced ? l.quantity * l.price : null,
          status: missing.length ? "input needed" : priced ? "priced" : "price needed" });
      }
      continue;
    }
    const d = driverOf(n);
    if (!d) {
      notCosted.push(n.data.label);
      continue;
    }
    const missing = d.inputs.filter((k) => values[k] == null);
    const quantity = missing.length ? null : Math.round(d.qty(values) * 100) / 100;
    const price = est.prices?.[n.id];
    const priced = price && Number.isFinite(price.price) && price.price >= 0 && /^[A-Z]{3}$/.test(price.currency || "") && String(price.source || "").trim() && !(price.tierLimit && quantity > price.tierLimit);
    lines.push({
      id: n.id,
      component: n.data.label,
      driver: d.name,
      unit: d.unit,
      inputs: d.inputs,
      quantity,
      missing,
      price: priced ? price : null,
      cost: quantity != null && priced ? quantity * price.price : null,
      status: missing.length ? "input needed" : priced ? "priced" : "price needed",
    });
  }
  const costed = lines.filter((l) => l.cost != null);
  const currencies = [...new Set(costed.map((l) => l.price.currency || "?"))];
  const total = costed.reduce((sum, l) => sum + l.cost, 0);
  const budget = [...(project.facts || [])].reverse().find((f) => f.name === "budget.per_month");
  const budgetCurrency = budget?.unit?.split("/")[0];
  const gaps = [
    ...(est.details || []).filter((l) => !project.nodes.some((n) => n.id === l.componentId && n.data.kind !== "note")).map((l) => `${l.description || l.id}: linked component was removed; reassign this charge (excluded from totals).`),
    ...lines.filter((l) => l.status !== "priced").map((l) => `${l.component} / ${l.driver}: ${l.status}${l.missing.length ? ` (${l.missing.join(", ")})` : ""}.`),
    ...lines.filter(l=>l.price?.coverageIncomplete).map(l=>`${l.component}: additional charges are excluded from this estimate.`),
    ...notCosted.map((name) => `${name}: no cost lines; add charges or an explicit zero-cost line with a reason.`),
    ...(currencies.length > 1 ? ["Choose one currency; different currencies cannot be added."] : []),
    ...lines.filter((l) => l.price && (!l.price.region?.trim() || !l.price.service?.trim() || !l.price.date || !Number.isFinite(Date.parse(l.price.date)))).map((l) => `${l.component} / ${l.driver}: confirm region, service/SKU and price date.`),
    ...lines.filter((l) => l.price?.date && (now - new Date(l.price.date)) / 86400000 > 90).map((l) => `${l.component} / ${l.driver}: price is over 90 days old; review it.`),
    ...lines.filter((l) => l.price?.date && new Date(l.price.date) > now).map((l) => `${l.component} / ${l.driver}: price date is in the future.`),
  ];
  return {
    lines,
    notCosted,
    preciseExpected:costed.length&&currencies.length===1?total:null,
    usage: u,
    currency: currencies.length === 1 ? currencies[0] : null,
    mixedCurrencies: currencies.length > 1,
    expected: currencies.length > 1 || !costed.length ? null : Math.round(total * 100) / 100,
    low: currencies.length > 1 || !costed.length ? null : Math.round(total * low * 100) / 100,
    high: currencies.length > 1 || !costed.length ? null : Math.round(total * high * 100) / 100,
    factors: { low, high },
    complete: lines.length > 0 && lines.every((l) => l.status === "priced") && !gaps.length,
    drivers: [...costed].sort((a, b) => b.cost - a.cost).slice(0, 3),
    budget: budget ? { amount: budget.value, currency: budgetCurrency, comparable: budgetCurrency === currencies[0] && currencies.length === 1 } : null,
    maturity: costed.length === 0 ? "Not estimated" : lines.every((l) => l.detailed && l.status === "priced") && !notCosted.length && currencies.length === 1 ? "Detailed worksheet" : "ROM",
    gaps,
  };
}

export function setPrice(project, componentId, price) {
  const est = project.estimate || {};
  const editedRate = ('price' in price || 'currency' in price) && !('source' in price);
  const provenance = editedRate ? {source:'entered by you',url:undefined,tierLimit:undefined,note:undefined,date:new Date().toLocaleDateString('en-CA')} : {};
  return {
    ...project,
    estimate: {
      ...est,
      prices: {
        ...(est.prices || {}),
        [componentId]: { source: "entered by you", date: new Date().toLocaleDateString("en-CA"), currency: "USD", ...(est.prices?.[componentId] || {}), ...provenance, ...price },
      },
    },
  };
}

export function setUsage(project, id, value) {
  const est = project.estimate || {};
  const next = { ...(est.usage || {}) };
  if (value === "" || value == null || !Number.isFinite(Number(value))) delete next[id];
  else if (Number(value) >= 0) next[id] = Number(value);
  return { ...project, estimate: { ...est, usage: next } };
}

export const WORK_PHASES = [
  ["discovery", "Discovery & specification"], ["design", "Architecture & security"],
  ["build", "Implementation & integration"], ["test", "Testing & acceptance"],
  ["deploy", "Deployment & handover"],
];

export function consultingEstimate(project) {
  const c = project.estimate?.consulting || {};
  const valid = (v) => Number.isFinite(v) && v >= 0;
  const lines = WORK_PHASES.map(([id, label]) => {
    const l = c.phases?.[id] || {};
    const complete = [l.lowDays, l.days, l.highDays, l.rate].every(valid) && l.lowDays <= l.days && l.days <= l.highDays && !!l.basis?.trim();
    return { id, label, ...l, complete, low: complete ? l.lowDays * l.rate : null, expected: complete ? l.days * l.rate : null, high: complete ? l.highDays * l.rate : null };
  });
  const currencyValid = /^[A-Z]{3}$/.test(c.currency || "USD");
  const sum = (key) => currencyValid && lines.some((l) => l.complete) ? Math.round(lines.reduce((s, l) => s + (l[key] || 0), 0) * 100) / 100 : null;
  return { lines, currency: c.currency || "USD", complete: currencyValid && lines.every((l) => l.complete), expected: sum("expected"), low: sum("low"), high: sum("high") };
}

export function setDetail(project, id, patch) {
  const est = project.estimate || {};
  return { ...project, estimate: { ...est, details: (est.details || []).map((l) => l.id === id ? { ...l, ...patch } : l) } };
}
