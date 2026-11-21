// Architecture review: deterministic, provider-neutral rules over the project model.
// See specs/003-architecture-review. Each finding names its rule, so it can be traced.

export const RULES_VERSION = "1.0.0";
export const ATTRIBUTES = [
  ["security", "Security & controls"],
  ["reliability", "Reliability"],
  ["availability", "Availability"],
  ["scalability", "Scalability"],
  ["performance", "Performance"],
  ["maintainability", "Maintainability"],
  ["cost", "Cost"],
];
export const SEVERITIES = ["blocker", "major", "minor", "info"];

// What a block does, whether runnable (kind) or sketched (role).
export function roleOf(n) {
  const { kind, role } = n.data;
  if (role) return role;
  return (
    { source: "data", stream: "data", history: "data", features: "ingest", train: "model", registry: "model", predict: "model", monitor: "monitor", agent: "llm", guard: "guard", tool: "app", output: "output" }[kind] || "other"
  );
}
const isHuman = (n) => roleOf(n) === "human" || /\b(approv|human|review queue|person)\b/i.test(n.data.label);
const isGuard = (n) => roleOf(n) === "guard" || isHuman(n);

function downstream(p, id, seen = new Set()) {
  for (const e of p.edges)
    if (e.source === id && !seen.has(e.target)) {
      seen.add(e.target);
      downstream(p, e.target, seen);
    }
  return seen;
}
// Paths from `from` to any node matching `to` that avoid nodes matching `via`.
function reachesAvoiding(p, from, to, via) {
  const stack = [from],
    seen = new Set([from]);
  while (stack.length) {
    const id = stack.pop();
    for (const e of p.edges.filter((x) => x.source === id)) {
      const n = p.nodes.find((x) => x.id === e.target);
      if (!n || seen.has(n.id) || via(n)) continue;
      if (to(n)) return true;
      seen.add(n.id);
      stack.push(n.id);
    }
  }
  return false;
}

const hasNeed = (p, category, re) =>
  (p.needs || []).some((r) => r.category === category && (!re || re.test(`${r.statement} ${r.measure?.metric || ""}`)));
const fact = (p, name) => [...(p.facts || [])].reverse().find((f) => f.name === name);

const RULES = [
  {
    id: "SEC-001",
    attribute: "security",
    severity: "blocker",
    check(p) {
      const llms = p.nodes.filter((n) => roleOf(n) === "llm");
      const exits = (n) => ["app", "output"].includes(roleOf(n));
      const open = llms.filter((n) => reachesAvoiding(p, n.id, exits, isGuard));
      return open.map((n) => ({
        statement: `${n.data.label} can reach users or systems without a guardrail or approval step.`,
        rationale: "Generated content can be wrong, unsafe or leak data; it needs a check before it leaves the system.",
        action: "Define and represent output validation or an approval control where needed; specify failure behavior and test it. Verify source authorization before retrieval and citation grounding separately: a guardrail block alone proves neither.",
        components: [n.id],
      }));
    },
  },
  {
    id: "SEC-002",
    attribute: "security",
    severity: "major",
    check(p) {
      const sensitive = p.nodes.filter((n) => n.data.config?.classification === "Confidential");
      const flagged = fact(p, "data.sensitive")?.value === true;
      if (!sensitive.length && !flagged) return [];
      if (hasNeed(p, "compliance", /stay|resid|region|locat/i)) return [];
      return [
        {
          statement: "Sensitive data is involved but where it must be stored is not stated.",
          rationale: "Data residency rules decide which regions and services are allowed.",
          action: "Add a compliance requirement such as “data stays in the EU”, and set regions on data blocks.",
          components: sensitive.map((n) => n.id),
        },
      ];
    },
  },
  {
    id: "SEC-003",
    attribute: "security",
    severity: "major",
    check(p) {
      const actors = p.nodes.filter((n) => ["llm", "model"].includes(roleOf(n)));
      // Systems that receive actions (integrations), not the interface people read.
      const apps = p.nodes.filter((n) => roleOf(n) === "app" && (n.data.kind === "tool" || /integration/i.test(n.data.category || "")));
      const unchecked = apps.filter((a) => actors.some((m) => downstream(p, m.id).has(a.id) && reachesAvoiding(p, m.id, (x) => x.id === a.id, isHuman)));
      if (!unchecked.length || hasNeed(p, "security", /person|human|approv/i)) return [];
      return [
        {
          statement: "Automated results reach other systems with no person approving them.",
          rationale: "Actions taken on model output (orders, emails, records) need clear human accountability.",
          action: "Add an approval step, or record a requirement that states which actions need approval.",
          components: unchecked.map((n) => n.id),
        },
      ];
    },
  },
  {
    id: "REL-001",
    attribute: "reliability",
    severity: "major",
    check(p) {
      const models = p.nodes.filter((n) => ["llm", "model"].includes(roleOf(n)));
      if (!models.length || p.nodes.some((n) => roleOf(n) === "monitor")) return [];
      return [
        {
          statement: "No monitoring for model quality or drift.",
          rationale: "Model answers and predictions degrade quietly; someone needs to see it happen.",
          action: "Add a monitoring block (quality, drift, cost) and decide who is alerted.",
          components: models.map((n) => n.id),
        },
      ];
    },
  },
  {
    id: "REL-002",
    attribute: "reliability",
    severity: "minor",
    check(p) {
      const apps = p.nodes.filter((n) => roleOf(n) === "app" && n.data.origin === "existing");
      return apps.length
        ? [
            {
              statement: "The design depends on existing systems; their failure behaviour is not described.",
              rationale: "If an integration is down, requests may be lost or duplicated.",
              action: "State what happens when each existing system is unavailable (retry, queue, fallback).",
              components: apps.map((n) => n.id),
            },
          ]
        : [];
    },
  },
  {
    id: "AVL-001",
    attribute: "availability",
    severity: "minor",
    check: (p) =>
      p.nodes.length && !hasNeed(p, "availability")
        ? [{ statement: "No availability target.", rationale: "Without one, nobody can say whether a single region or a single endpoint is enough.", action: "Add a requirement such as “available 99.5% of the time” or “business hours only”.", components: [] }]
        : [],
  },
  {
    id: "PRF-001",
    attribute: "performance",
    severity: "minor",
    check: (p) =>
      p.nodes.some((n) => ["llm", "model"].includes(roleOf(n))) && !hasNeed(p, "performance")
        ? [{ statement: "No response-time target.", rationale: "Model size, retrieval depth and region all trade speed against cost.", action: "Add a requirement such as “responds within 5 seconds”.", components: [] }]
        : [],
  },
  {
    id: "SCL-001",
    attribute: "scalability",
    severity: "info",
    check: (p) =>
      p.nodes.length && !fact(p, "requests.per_month") && !fact(p, "users")
        ? [{ statement: "Expected usage is unknown, so scale can't be assessed.", rationale: "Usage drives capacity, limits and cost.", action: "Tell us in the chat roughly how many people use it and how often.", components: [] }]
        : [],
  },
  {
    id: "MNT-001",
    attribute: "maintainability",
    severity: "minor",
    check: (p) => {
      const loose = (p.needs || []).filter((r) => r.kind === "nonfunctional" && !r.measure);
      return loose.length
        ? [{ statement: `${loose.length} quality requirement${loose.length > 1 ? "s have" : " has"} no measurable target.`, rationale: "A target makes it testable and lets the review say met or not met.", action: `Add a metric and target to: ${loose.map((r) => `“${r.statement}”`).join(", ")}.`, components: [] }]
        : [];
    },
  },
  {
    id: "MNT-002",
    attribute: "maintainability",
    severity: "minor",
    check: (p) => {
      const unowned = (p.decisions || []).filter((d) => d.status === "Accepted" && !d.owner?.trim());
      return unowned.length
        ? [{ statement: `${unowned.length} accepted decision${unowned.length > 1 ? "s have" : " has"} no owner.`, rationale: "Someone must be accountable for each choice before build.", action: "Assign an owner in Design → Decisions.", components: [] }]
        : [];
    },
  },
  {
    id: "CST-001",
    attribute: "cost",
    severity: "info",
    check: (p) =>
      p.nodes.length && !fact(p, "budget.per_month") && !hasNeed(p, "cost")
        ? [{ statement: "No budget stated.", rationale: "Without one, the estimate can't flag an option as too expensive.", action: "Mention a monthly running budget, or a range, in the chat.", components: [] }]
        : [],
  },
  {
    id: "DSN-001",
    attribute: "maintainability",
    severity: "info",
    check: (p) => {
      const sketch = p.nodes.filter((n) => n.data.kind === "resource");
      return sketch.length
        ? [{ statement: `${sketch.length} block${sketch.length > 1 ? "s are" : " is"} sketch-only and can't be test-run yet.`, rationale: "Sketch blocks describe intent; runnable fixtures exist only for some workflows.", action: "Keep designing; assign a runnable behaviour in block detail when one exists.", components: sketch.map((n) => n.id) }]
        : [];
    },
  },
];

const keyOf = (rule, components) => `${rule}:${[...components].sort().join(",")}`;

// Findings are recomputed from current data; accepted risks persist by rule + components.
export function review(full) {
  const notes = new Set(full.nodes.filter((n) => n.data.kind === "note").map((n) => n.id));
  const project = { ...full, nodes: full.nodes.filter((n) => !notes.has(n.id)), edges: full.edges.filter((e) => !notes.has(e.source) && !notes.has(e.target)) };
  const accepted = project.reviewAccepted || {};
  return RULES.flatMap((rule) =>
    rule.check(project).map((f, i) => {
      const key = keyOf(rule.id, f.components);
      return {
        id: `${rule.id}-${i + 1}`,
        key,
        rule: rule.id,
        version: RULES_VERSION,
        attribute: rule.attribute,
        severity: rule.severity,
        ...f,
        source: `AtMem AI Architect rule ${rule.id} v${RULES_VERSION}`,
        status: accepted[key] ? "accepted" : "open",
        ...(accepted[key] ? { acceptance: accepted[key] } : {}),
      };
    }),
  );
}

export function acceptRisk(project, finding, reason, owner) {
  if (!String(reason || "").trim() || !String(owner || "").trim()) throw Error("Accepting a risk needs a reason and an owner.");
  return {
    ...project,
    reviewAccepted: { ...(project.reviewAccepted || {}), [finding.key]: { reason, owner, date: new Date().toLocaleDateString("en-CA") } },
  };
}

export const blockers = (findings) => findings.filter((f) => f.severity === "blocker" && f.status === "open");
