// Deployment document, generated only from project data. See specs/005-deployment-document.
import { PROVIDERS, orderProject } from "./core.mjs";
import { layerOf } from "./levels.mjs";
import { BRIEF_FIELDS, CRITERIA, OPTIONS, optionScore } from "./engagement.mjs";
import { OPTION_NAMES, adrMarkdown, mermaid, measuresSection } from "./pack.mjs";
import { ATTRIBUTES, blockers, review, roleOf } from "./review.mjs";
import { DISCLAIMER, INPUTS, estimate, consultingEstimate } from "./estimate.mjs";
import { resourceMarkdown } from "./resources.mjs";
import { FORMAT_VERSION } from "./project-file.mjs";

const cell = (s) => String(s ?? "").replace(/\|/g, "\\|").replace(/\n/g, " ");
const RANK = { Public: 0, Internal: 1, Confidential: 2 };
const money = (v, c) => (v == null ? "—" : `${c || ""} ${v.toLocaleString("en", { maximumFractionDigits: 2 })}`.trim());

export function deploymentSteps(project) {
  let order;
  try {
    order = orderProject(project);
  } catch {
    order = project.nodes;
  }
  const layers = [];
  for (const n of order) {
    const l = layerOf(n).label;
    if (!layers.includes(l)) layers.push(l);
  }
  const by = (l) => order.filter((n) => layerOf(n).label === l && n.data.origin !== "existing");
  const existing = project.nodes.filter((n) => n.data.origin === "existing");
  return [
    "Confirm accounts, target regions and who approves each step; resolve every blocker in this document.",
    "Create least-privilege identities for each component; keep credentials in the provider's secret store, never in the project.",
    ...layers.filter((l) => by(l).length).map((l) => `Provision ${l.toLowerCase()}: ${by(l).map((n) => n.data.label).join(", ")}.`),
    ...(existing.length ? [`Connect existing systems: ${existing.map((n) => n.data.label).join(", ")}; test failure behaviour.`] : []),
    "Run the acceptance checks (success measures and requirements) in staging; record results.",
    "Review results and approve promotion to production; keep a rollback plan for each step.",
  ];
}

export function deploymentDocument(project, run, now = new Date()) {
  const findings = review(project);
  const blocking = blockers(findings);
  const est = estimate(project, now);
  const work = consultingEstimate(project);
  const brief = project.brief || {};
  const names = Object.fromEntries(project.nodes.map((n) => [n.id, n]));
  const nfr = (project.needs || []).filter((r) => r.kind === "nonfunctional");
  const fr = (project.needs || []).filter((r) => r.kind === "functional");
  const controls = project.nodes.filter((n) => ["guard", "human"].includes(roleOf(n)));
  const openQs = [
    ...(project.openQuestions || []).filter((q) => q.status === "open").map((q) => `- ${q.question}${q.owner ? ` _(${q.owner})_` : ""}`),
    ...BRIEF_FIELDS.filter((f) => f.essential && !brief[f.id]?.trim()).map((f) => `- ${f.question} _(discovery)_`),
    ...est.lines.filter((l) => l.status !== "priced").map((l) => `- ${l.component}: ${l.status === "input needed" ? `needs ${l.missing.join(", ")}` : "needs a unit price with a source"} _(estimate)_`),
  ];
  const cloud = project.provider && project.provider !== "tools" ? PROVIDERS[project.provider].name : "not chosen";
  const useCases = project.useCases || [];
  const a = project.assessment;
  const scored = a && OPTIONS.some((o) => optionScore(a, o) != null);
  const r = (s) => (s === "met" ? "Met" : s === "not-met" ? "Not met" : s === "at-risk" ? "At risk" : "Open");

  return `# ${project.name} — deployment document

Generated ${now.toISOString().slice(0, 16).replace("T", " ")} UTC from design revision r${project.revision} · project format ${FORMAT_VERSION} · AtMem AI Architect workbench

> ${blocking.length ? `**Not ready for deployment.** ${blocking.length} blocker${blocking.length > 1 ? "s" : ""}: ${blocking.map((f) => f.statement).join(" ")}` : "No blockers found by the automated review. Human review and the open questions below still apply."}
>
> Statements are **facts** from project data unless marked _assumption_ or listed under open questions. ${DISCLAIMER}

## 1. Summary

${brief.application?.trim() || project.requirements || "_What is being built has not been described yet._"}

- **Cloud:** ${cloud}
- **Usage:** ${est.usage.requests_per_month.value != null ? `${est.usage.requests_per_month.value.toLocaleString("en")} requests/month (${est.usage.requests_per_month.source})` : "unknown"}
- **Estimated run cost:** ${est.lines.length ? `${money(est.expected, est.currency)}/month expected (${money(est.low, est.currency)}–${money(est.high, est.currency)})${est.complete ? "" : " — **incomplete**"}` : "not estimated"}
- **Review:** ${findings.filter((f) => f.status === "open").length} open findings (${blocking.length} blockers)
- **Current decisions:** ${(project.decisions || []).filter((d) => d.status !== "Superseded").length}

## 2. Scope and context

${BRIEF_FIELDS.map((f) => `- **${f.label}:** ${cell(brief[f.id] || "—")}`).join("\n")}
${useCases.length ? `\n**Use cases considered**\n\n${useCases.map((u) => `- ${u.title} — **${u.verdict}**${u.reason ? `: ${u.reason}` : ""}`).join("\n")}\n` : ""}
## 3. Architecture

${[...new Set(project.nodes.map((n) => layerOf(n).label))]
  .map((l) => `**${l}**\n\n${project.nodes.filter((n) => layerOf(n).label === l).map((n) => `- ${n.data.label} (${PROVIDERS[n.data.provider].name}${n.data.origin === "existing" ? ", existing" : ""}${n.data.kind === "resource" ? ", sketch" : ""}) — ${n.data.description}`).join("\n")}`)
  .join("\n\n") || "_No components yet._"}

\`\`\`mermaid
${mermaid(project)}
\`\`\`
${resourceMarkdown(project)}
${scored ? `\n**Options compared** (scores 1–5, higher is better; judgement, not quotes)\n\n| Criterion | ${OPTIONS.map((o) => OPTION_NAMES[o]).join(" | ")} |\n|---|${OPTIONS.map(() => "---").join("|")}|\n${CRITERIA.map((c) => `| ${c.label} ×${a.weights[c.id]} | ${OPTIONS.map((o) => a.scores[o][c.id] ?? "—").join(" | ")} |`).join("\n")}\n| **Weighted** | ${OPTIONS.map((o) => optionScore(a, o) ?? "—").join(" | ")} |\n` : ""}
## 4. Data flows

${project.edges.length ? ["| From | To | Data | Classification |", "|---|---|---|---|", ...project.edges.map((e) => {
    const s = names[e.source], t = names[e.target];
    const c = [s, t].map((n) => n?.data.config?.classification || "Internal").sort((x, y) => RANK[y] - RANK[x])[0];
    return `| ${cell(s?.data.label)} | ${cell(t?.data.label)} | ${cell(e.label || "data")} | ${c} |`;
  })].join("\n") : "_None recorded._"}

## 5. Security controls

${controls.length ? controls.map((n) => `- **${n.data.label}** — ${n.data.description}`).join("\n") : "- _No guardrail or approval components in the design._"}
${(project.needs || []).filter((x) => ["security", "compliance"].includes(x.category)).map((x) => `- Requirement: ${x.statement} (${x.priority})`).join("\n")}
${findings.filter((f) => f.attribute === "security").map((f) => `- ${f.status === "accepted" ? "Accepted risk" : "Open finding"} ${f.rule}: ${f.statement}${f.acceptance ? ` — accepted by ${f.acceptance.owner}: ${f.acceptance.reason}` : ""}`).join("\n")}

## 6. Requirements

**Non-functional**

${nfr.length ? ["| Requirement | Category | Target | Status |", "|---|---|---|---|", ...nfr.map((x) => `| ${cell(x.statement)} | ${x.category} | ${x.measure ? cell(`${x.measure.metric} ${x.measure.op} ${x.measure.target}${x.measure.unit}`) : "not measurable yet"} | ${r(x.status)} |`)].join("\n") : "_None recorded._"}

**Functional**

${fr.length ? fr.map((x) => `- ${x.statement} (${x.priority}, ${r(x.status).toLowerCase()})`).join("\n") : "_None recorded._"}

**Success measures**

${measuresSection(project, run)}

## 7. Review findings

${ATTRIBUTES.map(([id, label]) => {
    const fs = findings.filter((f) => f.attribute === id);
    return fs.length ? `**${label}**\n\n${fs.map((f) => `- [${f.severity}] ${f.statement} ${f.action} _(${f.source})_${f.acceptance ? ` — **Accepted risk** (${f.acceptance.owner}, ${f.acceptance.date}): ${f.acceptance.reason}` : ""}`).join("\n")}` : null;
  }).filter(Boolean).join("\n\n") || "_No findings._"}

## 8. Cost estimate

${DISCLAIMER} Monthly run cost only. Prices are as entered, with their sources.

**Estimate stage:** ${est.maturity}. ${est.maturity === "Detailed worksheet" ? "User-entered charge coverage; still needs engineering and pricing validation." : "Rough order of magnitude, refined as scope and charge dimensions become known."}

${est.lines.length ? ["| Component | Driver | Quantity | Unit price | Monthly | Source |", "|---|---|---|---|---|---|", ...est.lines.map((l) => `| ${cell(l.component)} | ${l.driver} | ${l.quantity == null ? `needs ${l.missing.join(", ")}` : `${l.quantity.toLocaleString("en")} ${l.unit}`} | ${l.price ? `${l.price.currency} ${l.price.price} / ${l.unit}` : "price needed"} | ${l.cost == null ? "—" : money(l.cost, l.price.currency)} | ${l.price ? cell(`${l.price.source}${l.price.url ? ` ${l.price.url}` : ""}, ${l.price.date}`) : "—"} |`)].join("\n") : "_No costed components._"}

**Usage inputs:** ${INPUTS.filter((i) => est.lines.some((l) => l.inputs.includes(i.id))).map((i) => `${i.label}: ${est.usage[i.id].value ?? "—"} (${est.usage[i.id].source})`).join("; ") || "Quantities are entered directly on detailed charge lines above"}.

**Range:** low ×${est.factors.low}, high ×${est.factors.high} of expected.${est.notCosted.length ? ` Not costed in this release: ${est.notCosted.join(", ")}.` : ""}${est.budget ? ` Budget stated: ${est.budget.currency} ${est.budget.amount}/month${est.budget.comparable ? (est.expected > est.budget.amount ? " — **expected cost is over budget**" : " — within budget") : " (different currency; not compared)"}.` : ""}

**Estimate gaps:**\n\n${est.gaps.map((g) => `- ${g}`).join("\n") || "No worksheet gaps detected; validate dimensions, quotations and assumptions before treating this as a full estimate."}

### Consulting and build estimate (one-off)

${work.expected == null ? "Not estimated; enter work-package days, rates and a basis." : `${money(work.expected, work.currency)} expected; ${money(work.low, work.currency)}–${money(work.high, work.currency)} range. ${work.complete ? "All five work packages entered." : "Incomplete subtotal; work packages remain unestimated."}`}

| Work package | Low / expected / high days | Rate / day | Expected | Basis and exclusions |
|---|---|---|---|---|
${work.lines.map((l) => `| ${l.label} | ${l.lowDays ?? "—"} / ${l.days ?? "—"} / ${l.highDays ?? "—"} | ${money(l.rate, work.currency)} | ${money(l.expected, work.currency)} | ${cell(l.basis || "Needed")} |`).join("\n")}

One-off effort is separate from monthly cloud charges. Days are person-days, not elapsed time. Taxes, support, licences and migration are excluded unless explicitly included in the basis or charge lines.

## 9. Deployment steps

_Draft generated from the design; validate against the provider's current documentation before use. Nothing has been provisioned._

${deploymentSteps(project).map((s, i) => `${i + 1}. ${s}`).join("\n")}

## 10. Decisions

${adrMarkdown(project.decisions)}
## 11. Assumptions

${(project.assumptions || []).length ? project.assumptions.map((x) => `- _Assumption:_ ${x.statement} _(stated ${x.madeAt}${x.owner ? `, ${x.owner}` : ""})_`).join("\n") : "_None recorded._"}
${INPUTS.filter((i) => est.lines.some((l) => l.inputs.includes(i.id)) && est.usage[i.id].source.startsWith("assumption")).map((i) => `- _Assumption:_ ${i.label} = ${est.usage[i.id].value} (${i.assumptionText})`).join("\n")}

## 12. Open questions

${openQs.join("\n") || "_None._"}
`;
}
