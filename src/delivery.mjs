import {architectureWork} from './architecture-work.mjs';
import {artifactWorkProjection} from './artifact-work.mjs';
import {generationQuality} from './generation-quality.mjs';
import {implementationOutcome} from './implementation-outcome.mjs';
import {systemDescriptionMarkdown,requirementExplanation} from './system-description.mjs';
import { specKit } from "./spec-kit.mjs";
import { requirementNumber } from "./derive.mjs";
// All deliverables are generated from one project snapshot, never independently edited copies.
import { toProjectFile } from "./project-file.mjs";
import { deploymentDocument } from "./document.mjs";
import { mermaid, adrMarkdown, OPTION_NAMES } from "./pack.mjs";
import { OPTIONS, CRITERIA, optionScore } from "./engagement.mjs";
import { estimate, consultingEstimate, DISCLAIMER } from "./estimate.mjs";
import { resourcePlan, resourceMarkdown } from "./resources.mjs";
import { terraformSketch } from "./terraform.mjs";
import { review, blockers } from "./review.mjs";

const text = (s) => String(s ?? "").replaceAll("|", "\\|").replaceAll("\n", " ");
const json = (v) => JSON.stringify(v, null, 2);
const list = (items) => items.length ? items.map((x) => `- ${x}`).join("\n") : "None recorded.";
export function solutionSpecification(project) {
  const a = project.assessment;
  return `# ${project.name} — solution specification\n\n## Problem and intended outcome\n\n${implementationOutcome(project)}\n\n## Scope\n\n${list((project.useCases || []).map((u) => `${u.title}: ${u.verdict}${u.reason ? ` — ${u.reason}` : ""}`))}\n\n## Requirements and acceptance criteria\n\n${list((project.needs || []).map((r) => `[${requirementNumber(project,r.id)}] ${r.statement} (${r.priority}, ${r.status}); target: ${r.measure ? `${r.measure.metric} ${r.measure.op} ${r.measure.target}${r.measure.unit || ""}` : "acceptance target needed"}; linked blocks: ${r.links?.join(", ") || "not linked"}${`\n\nDesign explanation: ${requirementExplanation(r)}`}${r.basis ? `\n\nBasis: ${r.basis}` : ""}`))}\n\n${systemDescriptionMarkdown(project)}\n\n## Architecture\n\n\`\`\`mermaid\n${mermaid(project)}\n\`\`\`\n\n${resourceMarkdown(project)}\n\n## Options and tradeoffs\n\n${a ? `Scores are entered judgements (1–5), not provider benchmarks or prices. Unscored options remain open.\n\n| Option | ${CRITERIA.map((c) => c.label).join(" | ")} | Weighted score | Rationale |\n|---|${CRITERIA.map(() => "---|").join("")}---|---|\n${OPTIONS.map((o) => `| ${OPTION_NAMES[o]} | ${CRITERIA.map((c) => a.scores?.[o]?.[c.id] ?? "—").join(" | ")} | ${optionScore(a, o) ?? "—"} | ${text(a.notes?.[o])} |`).join("\n")}` : "Use Design → Options to compare cloud choices and record the rationale before choosing."}\n\n## Design checks and decisions\n\n${adrMarkdown(project.decisions)}\n\n### Design checks\n\n${review(project).map(f=>`- [${f.status}] ${f.statement}\n  Rationale: ${f.rationale}\n  Next action: ${f.action}\n  Source: ${f.source}${project.reviewAccepted?.[f.key]?`\n  Accepted by: ${project.reviewAccepted[f.key].owner}; reason: ${project.reviewAccepted[f.key].reason}`:''}`).join('\n\n')}\n\n## Assumptions\n\n${list((project.assumptions || []).map((a) => `[${a.id}] ${a.statement} (${a.madeAt})`))}\n\n## Questions to resolve\n\n${list((project.openQuestions || []).filter((q) => q.status === "open").map((q) => `[${q.id}] ${q.question}${q.owner ? ` — ${q.owner}` : ""}`))}\n`;
}

export function deliveryPack(project, run, environment = "staging", now = new Date()) {
  // Credential refusal runs before producing any files, including the plain-language outputs.
  const file = toProjectFile(project, now);
  const cloud = estimate(project, now), consulting = consultingEstimate(project), resources = resourcePlan(project);
  const findings = review(project);
  const snapshotId = crypto.randomUUID();
  const stamp = `Snapshot ${snapshotId} · design r${project.revision} · generated ${now.toISOString()}`;
  const outstanding = [
    ...blockers(findings).map((f) => `Architecture: ${f.statement}`), ...cloud.gaps,
    ...resources.gaps,
    ...consulting.lines.filter((l) => !l.complete).map((l) => `${l.label}: effort, rate, ordered day range and basis needed.`),
    ...(project.openQuestions || []).filter((q) => q.status === "open").map((q) => q.question),
  ];
  const files = {
    ...specKit(project,{snapshotId,stamp,now,environment:environment === "production" ? "production" : "staging"}),
    "project.atmem-ai-architect.json": json(file),
    "architecture-work.json": json(architectureWork(project)),
    "architecture-artifact-mappings.json": json(artifactWorkProjection(project)),
    "specification.md": `${stamp}\n\n${solutionSpecification(project)}\n\n## Implementation specification and coding-agent handoff\n\nThe Spec Kit translates these requirements and the architecture into implementation work. Start with START_HERE.md and AGENTS.md; read spec-kit/implementation-spec.md (or PDF) for the implementation plan, contracts, detailed tasks and validation plan. Requirements remain the source of desired outcomes; the kit is the build plan derived from them.\n`,
    "architecture-and-deployment.md": `${stamp}\n\n${deploymentDocument(project, run, now)}`,
    "diagram.mmd": mermaid(project),
    "decisions.md": `${stamp}\n\n${adrMarkdown(project.decisions)}`,
    "resource-schedule.json": json(resources),
    "estimate.json": json({ snapshotId, revision: project.revision, generatedAt: now.toISOString(), disclaimer: DISCLAIMER, cloud, consulting }),
    "handoff.md": `# Delivery handoff\n\n${stamp}\n\nThis is a reviewable design handoff, not deployment evidence.\n\n## Readiness\n\nRead spec-kit/readiness.md for prioritised decisions, task links and separate evidence stages. Schema checks cannot establish application deployment readiness.\n\n## Work remaining\n\n${list(outstanding)}\n\n## Before deployment\n\n- Confirm provider, region, data residency, account owner and environment.\n- Complete the resource implementations, application code, IAM and data-flow integrations.\n- Validate the estimate against every billable dimension and a current provider quote.\n- Review least-privilege access, quotas, secrets handling and Terraform state storage.\n- Run and review the infrastructure plan in the intended account.\n- Agree acceptance tests, rollback and an explicit deployment approval.\n- Capture results and handover ownership. No cloud operation has been performed by this export.\n`,
    ...Object.fromEntries(Object.entries(terraformSketch(project, environment)).map(([name, content]) => [`terraform/${name}`, content])),
    "README.md": `# ${project.name} — delivery pack\n\n${stamp}\n\nFor a coding-agent handoff, start with START_HERE.md and AGENTS.md, then spec-kit/implementation-spec.md or PDF. The kit includes detailed task dependencies, acceptance criteria, contracts and a progress journal.\n\nOpen specification.md for scope, requirements, options and decisions; architecture-and-deployment.md for the diagram, review, costs and steps. estimate.json separates monthly cloud cost and one-off consulting/build cost. resource-schedule.json links resources to diagram IDs. terraform/ contains provider-specific generated artifacts where supported; generation-quality.json records component coverage, missing implementations, selected skill digests and validation boundaries.\n\nReopen project.atmem-ai-architect.json in AtMem AI Architect to change requirements, assumptions, decisions, prices or the diagram, then regenerate this pack. All files come from the same snapshot; do not maintain edited copies as the source of truth. Design revision tracks board changes; snapshot ID and generation time identify exports including changes to costs and requirements.\n\nCloud prices and professional-service rates are only those entered in the project. A ROM or detailed worksheet is not a fixed-price quote. No cloud access, deployment or successful infrastructure validation is implied.\n`,
  };
  const terraformFiles=Object.fromEntries(Object.entries(files).filter(([name])=>name.startsWith('terraform/')).map(([name,content])=>[name.slice(10),content]));
  files['generation-quality.json']=json(generationQuality(project,resources,terraformFiles));
  files["manifest.json"] = json({ format: "atmem.ai-architect.delivery", version: "1.0.0", snapshotId, projectId: file.meta.id, designRevision: project.revision, generatedAt: now.toISOString(), environment: environment === "production" ? "production" : "staging", estimateStage: cloud.maturity, deploymentExecuted: false, handoffStatus: 'engineering_required', readinessFile: 'spec-kit/readiness.json', files: [...Object.keys(files), "manifest.json"] });
  return files;
}
