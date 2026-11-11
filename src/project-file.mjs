import {validateArchitectureWork} from './architecture-work.mjs';
import {validateStateCustody} from './state-custody.mjs';
// The durable project file: atforma.project 2.0.0. See specs/002-project-model.
import { validateImport } from "./core.mjs";

export const FORMAT = "atmem.ai-architect.project";
export const FORMAT_VERSION = "2.3.0";
export const MAX_FILE_BYTES = 2_000_000;
const GENERATOR = "atmem-ai-architect 0.2.0";

// Section keys the 2.0 reader understands; anything else is kept in extensions.
const KNOWN_TOP = ["format", "formatVersion", "meta", "design", "discovery", "requirements", "assumptions", "openQuestions", "decisions", "options", "estimate", "review", "extensions"];
const KNOWN = {
  meta: ["id", "name", "createdAt", "updatedAt", "revision", "generator", "domain"],
  design: ["provider", "nodes", "edges"],
  discovery: ["problem", "brief", "useCases", "gate", "facts", "workflow", "asked", "lastAsked", "sketchOffered"],
  review: ["accepted"],
};

const SECRET_VALUE = [
  /AKIA[0-9A-Z]{16}/,
  /sk-ant-[A-Za-z0-9_-]{20,}/,
  /sk-[A-Za-z0-9_-]{20,}/,
  /AIza[0-9A-Za-z_-]{35}/,
  /ghp_[A-Za-z0-9]{36}/,
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/,
];
const SECRET_KEY = /^(password|secret|apiKey|api_key|accessKey|access_key|token|clientSecret|client_secret)$/i;

// Paths of values that look like credentials.
export function findCredentials(value, path = "") {
  if (typeof value === "string") return SECRET_VALUE.some((re) => re.test(value)) ? [path || "(root)"] : [];
  if (Array.isArray(value)) return value.flatMap((v, i) => findCredentials(v, `${path}[${i}]`));
  if (value && typeof value === "object")
    return Object.entries(value).flatMap(([k, v]) => {
      const at = path ? `${path}.${k}` : k;
      if (SECRET_KEY.test(k) && typeof v === "string" && v.trim()) return [at];
      return findCredentials(v, at);
    });
  return [];
}

function refuseCredentials(value, verb) {
  const found = findCredentials(value);
  if (found.length)
    throw Error(`${verb} refused: ${found.slice(0, 3).join(", ")}${found.length > 3 ? "…" : ""} looks like a credential. Remove it and try again.`);
}

function unknown(section, allowed) {
  return Object.fromEntries(Object.entries(section || {}).filter(([k]) => !allowed.includes(k)));
}

export function toProjectFile(project, now = new Date()) {
  validateStateCustody(project.extensions?.terraformState);
  const {
    version, revision, name, provider, domain, requirements, nodes, edges,
    brief, useCases, gate, needs, assumptions, openQuestions, decisions, assessment,
    facts, workflow, asked, lastAsked, sketchOffered, estimate, reviewAccepted,
    id, createdAt, extensions, importReport, ...rest
  } = project;
  const file = {
    format: FORMAT,
    formatVersion: FORMAT_VERSION,
    meta: {
      id: id || crypto.randomUUID(),
      name,
      createdAt: createdAt || now.toISOString(),
      updatedAt: now.toISOString(),
      revision,
      generator: GENERATOR,
      ...(domain ? { domain } : {}),
    },
    design: { provider: provider || "tools", nodes, edges },
    discovery: {
      problem: requirements || "",
      ...(brief ? { brief } : {}),
      ...(useCases ? { useCases } : {}),
      ...(gate ? { gate } : {}),
      ...(facts ? { facts } : {}),
      ...(workflow ? { workflow } : {}),
      ...(asked ? { asked } : {}),
      ...(lastAsked ? { lastAsked } : {}),
      ...(sketchOffered ? { sketchOffered } : {}),
    },
    requirements: needs || [],
    assumptions: assumptions || [],
    openQuestions: openQuestions || [],
    decisions: decisions || [],
    ...(assessment ? { options: assessment } : {}),
    ...(estimate ? { estimate } : {}),
    ...(reviewAccepted ? { review: { accepted: reviewAccepted } } : {}),
    // Browser-only fields the file format doesn't name yet are preserved, not dropped.
    extensions: { ...(extensions || {}), ...rest },
  };
  if(file.extensions.architectureWork!==undefined)validateArchitectureWork(file.extensions.architectureWork);
  refuseCredentials(file, "Export");
  if(new TextEncoder().encode(JSON.stringify(file)).length>MAX_FILE_BYTES)throw Error("Project files must be 2 MB or smaller; no content was truncated.");
  return file;
}

// Returns the browser project plus what happened, so the UI can say so.
export function fromProjectFile(raw) {
  if (!raw || typeof raw !== "object") throw Error("Not a project file.");
  refuseCredentials(raw, "Import");
  if (raw.format === undefined && raw.version === 1)
    return { project: validateImport(raw), migrated: true, from: "workbench v1" };
  if (![FORMAT,"atforma.project"].includes(raw.format)) throw Error("Not an AtMem AI Architect project file.");
  const [major] = String(raw.formatVersion || "").split(".").map(Number);
  if (major !== 2)
    throw Error(`This file is format ${raw.formatVersion}; this version of AtMem AI Architect reads ${FORMAT_VERSION}. Update AtMem AI Architect to open it.`);
  const meta = raw.meta || {},
    design = raw.design || {},
    discovery = raw.discovery || {};
  const extensions = {
    ...(raw.extensions || {}),
    ...unknown(raw, KNOWN_TOP),
    ...Object.fromEntries(
      Object.entries(KNOWN)
        .map(([section, allowed]) => [section, unknown(raw[section], allowed)])
        .filter(([, extra]) => Object.keys(extra).length)
        .map(([section, extra]) => [`${section}.extra`, extra]),
    ),
  };
  const project = validateImport({
    version: 1,
    revision: meta.revision,
    name: meta.name,
    provider: design.provider,
    ...(meta.domain ? { domain: meta.domain } : {}),
    id: meta.id,
    createdAt: meta.createdAt,
    requirements: discovery.problem || "",
    nodes: design.nodes,
    edges: design.edges,
    ...(discovery.brief ? { brief: discovery.brief } : {}),
    ...(discovery.useCases ? { useCases: discovery.useCases } : {}),
    ...(discovery.gate ? { gate: discovery.gate } : {}),
    ...Object.fromEntries(["facts", "workflow", "asked", "lastAsked", "sketchOffered"].filter((k) => discovery[k] !== undefined).map((k) => [k, discovery[k]])),
    ...(raw.estimate ? { estimate: raw.estimate } : {}),
    ...(raw.review?.accepted ? { reviewAccepted: raw.review.accepted } : {}),
    needs: raw.requirements || [],
    assumptions: raw.assumptions || [],
    openQuestions: raw.openQuestions || [],
    decisions: raw.decisions || [],
    ...(raw.options ? { assessment: raw.options } : {}),
    ...(Object.keys(extensions).length ? { extensions } : {}),
  });
  return { project, migrated: raw.format !== FORMAT || raw.formatVersion !== FORMAT_VERSION, from: raw.formatVersion };
}

export function parseProjectFile(textContent) {
  if (new TextEncoder().encode(textContent).length > MAX_FILE_BYTES) throw Error("Project files must be 2 MB or smaller.");
  return fromProjectFile(JSON.parse(textContent));
}
