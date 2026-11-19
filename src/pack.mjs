import {diagramText,validateBlockSpecs} from './block-spec.mjs';
import { requirementNumber } from "./derive.mjs";
// Client pack: one Markdown document generated from the board.
import { PROVIDERS, checkProject } from "./core.mjs";
import { layerOf } from "./levels.mjs";
import { decisionHistory } from "./records.mjs";
import { BRIEF_FIELDS, CRITERIA, GATE, OPTIONS, defaultAssessment, optionScore } from "./engagement.mjs";

export const OPTION_NAMES = {
  current: "Current approach",
  aws: "AWS",
  azure: "Azure",
  gcp: "Google Cloud",
  ibm: "IBM",
};

export function mermaid(project) {
  validateBlockSpecs(project.nodes);
  const id = new Map(project.nodes.map((node, index) => [node.id, `n${index}`]));
  const children = new Map();
  for (const node of project.nodes) {
    const parent=node.data.parentBlockId||null;
    if(!children.has(parent))children.set(parent,[]);
    children.get(parent).push(node);
  }
  function draw(parent,indent) {
    return (children.get(parent)||[]).flatMap(node=>{
      const lines=[`${indent}${id.get(node.id)}["${diagramText(node.data.label)}"]`];
      if(!children.has(node.id))return lines;
      return [`${indent}subgraph group${id.get(node.id)}["${diagramText(node.data.label)}"]`,
        ...lines,...draw(node.id,indent+'  '),indent+'end'];
    });
  }
  return [
    'flowchart LR',
    ...draw(null,'  '),
    ...project.edges.map(edge=>`  ${id.get(edge.source)} -->|"${diagramText(edge.label||'data')}"| ${id.get(edge.target)}`),
  ].join('\n');
}

export function adrMarkdown(decisions = []) {
  const current = decisions.filter((d) => d.status !== "Superseded");
  if (!current.length) return "_No decisions recorded yet._\n";
  return current
    .map((d) => {
      const earlier = decisionHistory(decisions, d.subject).filter((h) => h.id !== d.id);
      return (
        `### ${d.id.toUpperCase()} · ${d.title || "Untitled"}\n\n` +
        `**Status:** ${d.status} · **Owner:** ${d.owner || "unassigned"} · **Date:** ${d.date}${d.revision ? ` · **Design:** r${d.revision}` : ""} · **Subject:** \`${d.subject}\`\n\n` +
        `**Context**\n\n${d.context || "—"}\n\n**Options considered**\n\n${d.options || "—"}\n\n` +
        `**Decision**\n\n${d.decision || "—"}${d.reason ? `\n\n_Changed because: ${d.reason}_` : ""}\n\n**Consequences**\n\n${d.consequences || "—"}\n` +
        (earlier.length
          ? `\n**History**\n\n${earlier.map((h) => `- ${h.id.toUpperCase()} (${h.date}, superseded): ${h.decision || h.title}${h.reason ? ` — ${h.reason}` : ""}`).join("\n")}\n`
          : "")
      );
    })
    .join("\n");
}

const cell = (s) => String(s ?? "").replace(/\|/g, "\\|").replace(/\n/g, " ");
export function recordsSection(project) {
  const names = Object.fromEntries(project.nodes.map((n) => [n.id, n.data.label]));
  const linked = (r) => r.links.map((id) => names[id] || "removed component").join(", ") || "—";
  const needs = project.needs || [];
  return needs.length
    ? [
        "| Requirement | Type | Priority | Target | Status | Components |",
        "|---|---|---|---|---|---|",
        ...needs.map(
          (r) =>
            `| ${project.extensions?.requirementNumbers?.[r.id] ? requirementNumber(project,r.id)+" — " : ""}${cell(r.statement)} | ${r.kind === "nonfunctional" ? `NFR · ${r.category}` : `functional · ${r.category}`} | ${r.priority} | ${r.measure ? cell(`${r.measure.metric} ${r.measure.op} ${r.measure.target}${r.measure.unit}`) : "not measurable yet"} | ${r.status} | ${cell(linked(r))} |`,
        ),
      ].join("\n")
    : "_No requirements recorded._";
}

export function measuresSection(project, run) {
  const outputs = project.nodes.filter((n) => n.data.measures?.length);
  if (!outputs.length) return "_No success measures defined._\n";
  const tested = run && run.revision === project.revision;
  const results = Object.fromEntries(
    (run?.steps || []).flatMap((s) => (s.output?.measures || []).map((m) => [m.label, m])),
  );
  return [
    "| Measure | Target | Last result |",
    "|---|---|---|",
    ...outputs.flatMap((n) =>
      n.data.measures.map((m) => {
        const r = tested ? results[m.label] : null;
        return `| ${m.label} | ${m.op} ${m.target} | ${r ? `${r.pass ? "Met" : "Not met"} (${r.value})` : "Not tested on this revision"} |`;
      }),
    ),
  ].join("\n");
}

export function clientPack(project, run) {
  const a = project.assessment || defaultAssessment();
  const brief = project.brief || {};
  const accepted = (project.decisions || []).filter((d) => d.status === "Accepted");
  const issues = checkProject(project).filter((i) => i.level === "error");
  const layers = new Map();
  for (const n of project.nodes) {
    const l = layerOf(n).label;
    layers.set(l, [...(layers.get(l) || []), n]);
  }
  const scope = project.nodes.filter((n) => n.data.poc);
  const confidential = project.nodes.filter((n) => n.data.config?.classification === "Confidential");
  const runLine =
    run && run.revision === project.revision
      ? `Last proof-of-concept run (${run.scenario} scenario): **${run.status}**, ${run.steps.filter((s) => s.status === "passed").length}/${project.nodes.length} steps passed. Runs use local sample data, not client systems.`
      : "The proof of concept has not been run against this design revision.";

  return `# ${project.name}

${brief.client ? `Prepared for ${brief.client} · ` : ""}${new Date().toISOString().slice(0, 10)} · design revision r${project.revision}

## Summary

${project.requirements || "_Problem statement not recorded._"}

${accepted.length ? accepted.map((d) => `- **${d.title}** — ${d.decision}`).join("\n") : "_No accepted decisions yet._"}

${runLine}

## Discover

${BRIEF_FIELDS.map((f) => `- **${f.label}:** ${brief[f.id] || "—"}`).join("\n")}

**Use cases**

${
  (project.useCases || []).length
    ? ["| Use case | Value | Risk | Strategic fit | Verdict | Why |", "|---|---|---|---|---|---|",
        ...project.useCases.map((u) => `| ${u.title} | ${u.value} | ${u.risk} | ${u.fit} | **${u.verdict}** | ${u.reason || "—"} |`)].join("\n")
    : "_No use cases qualified yet._"
}

## Design

### Target architecture


${[...layers]
  .map(
    ([label, nodes]) =>
      `**${label}**\n\n${nodes
        .map(
          (n) =>
            `- ${n.data.label} (${PROVIDERS[n.data.provider].name}${n.data.origin === "existing" ? ", existing" : ""}${n.data.poc ? ", in PoC" : ""}) — ${n.data.description}`,
        )
        .join("\n")}`,
  )
  .join("\n\n")}

\`\`\`mermaid
${mermaid(project)}
\`\`\`

### Cloud options

Scores 1–5, higher is better. Weighted totals are the consultant's assessment, not vendor quotes.

| Criterion (weight) | ${OPTIONS.map((o) => OPTION_NAMES[o]).join(" | ")} |
|---|${OPTIONS.map(() => "---").join("|")}|
${CRITERIA.map((c) => `| ${c.label} (×${a.weights[c.id]}) | ${OPTIONS.map((o) => a.scores[o][c.id] ?? "—").join(" | ")} |`).join("\n")}
| **Weighted** | ${OPTIONS.map((o) => `**${optionScore(a, o) ?? "—"}**`).join(" | ")} |

${OPTIONS.filter((o) => a.notes[o]).map((o) => `- **${OPTION_NAMES[o]}:** ${a.notes[o]}`).join("\n")}
${a.current ? `\nCurrent approach: ${a.current}\n` : ""}
### Requirements

${recordsSection(project)}

### Success criteria (set before build)

${measuresSection(project, run)}

### Security, governance and responsible AI

${issues.length ? issues.map((i) => `- Open design issue: ${i.text}`).join("\n") : "- No open structural issues."}
${confidential.length ? `- Confidential data: ${confidential.map((n) => n.data.label).join(", ")}.` : ""}
- Every path from data to a user-facing result passes through a policy / guardrail block (checked automatically).
- Still to confirm with the client: identity and access model, network boundaries, data residency, model risk sign-off, cost guardrails per environment.

## Build

**Prototype / PoC scope:** ${scope.length ? scope.map((n) => n.data.label).join(", ") : "not yet marked"}.

**Build approach:** a design-to-code scaffold (Pulumi) and a deployment plan are exported from the board. Nothing is provisioned until the client's delivery team applies it.

**Scale gate** — scale only when value demonstrably exceeds cost and risk.

${GATE.map((g) => `- **${g.label}:** ${project.gate?.[g.id] || "—"}`).join("\n")}

## Assumptions

${(project.assumptions || []).length ? project.assumptions.map((a) => `- ${a.statement} _(stated ${a.madeAt}${a.owner ? `, ${a.owner}` : ""})_`).join("\n") : "_None recorded._"}

## Open questions

${
  [
    ...(project.openQuestions || []).filter((q) => q.status === "open").map((q) => `- ${q.question}${q.owner ? ` _(${q.owner})_` : ""}`),
    ...BRIEF_FIELDS.filter((f) => !brief[f.id]?.trim()).map((f) => `- ${f.question} _(discovery)_`),
  ].join("\n") || "_None._"
}

## Decisions

${adrMarkdown(project.decisions)}`;
}
