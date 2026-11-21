/** AtMem AI Architect adapters for pinned upstream modules. See docs/merge-manifest.json. */
import { AWS_SERVICES } from "./upstream/openarchflow/providers/aws.ts";
import { AZURE_SERVICES } from "./upstream/openarchflow/providers/azure.ts";
import { GENERIC_SERVICES } from "./upstream/openarchflow/providers/generic.ts";
import { CLOUDNATIVE_SERVICES } from "./upstream/openarchflow/providers/cloudnative.ts";
import { INTEGRATION_SERVICES } from "./upstream/openarchflow/providers/integration.ts";
import { TEMPLATES } from "./upstream/openarchflow/templates.ts";
import { parseMermaid } from "./upstream/openarchflow/import/mermaid.ts";
import { parseSqlDdl } from "./upstream/openarchflow/import/sql-ddl.ts";
import { getLayoutedElements } from "./upstream/openarchflow/layout.ts";
export { prettyPayload } from "./upstream/openarchflow/format-payload.ts";

const catalogues = [
  ["aws", AWS_SERVICES],
  ["azure", AZURE_SERVICES],
  ["tools", GENERIC_SERVICES],
  ["tools", CLOUDNATIVE_SERVICES],
  ["tools", INTEGRATION_SERVICES],
] as const;
export const UPSTREAM_CATALOG = catalogues.flatMap(
  ([provider, categories], group) =>
    categories.flatMap((category, c) =>
      category.items.map((item, i) => ({
        id: `upstream-${group}-${c}-${i}`,
        provider,
        kind: "resource",
        label: item.name,
        description: item.description,
        service: item.service,
        category: category.category,
        origin: "OpenArchFlow",
        support: "design-only",
      })),
    ),
);
export const UPSTREAM_TEMPLATES = TEMPLATES;
function convertGraph(parsed: any, name: string, provider = "tools") {
  if (!parsed.nodes.length)
    throw Error(
      "No supported blocks found. Try a simple flowchart or CREATE TABLE statements.",
    );
  if (parsed.nodes.length > 100)
    throw Error("Import is limited to 100 blocks.");
  const ids = new Set(parsed.nodes.map((n: any) => n.id));
  const edges = parsed.edges
    .filter((e: any) => ids.has(e.source) && ids.has(e.target))
    .map((e: any, i: number) => ({
      id: `import-wire-${i}`,
      source: e.source,
      target: e.target,
      label: String(e.label || "relationship"),
      type: "smoothstep",
    }));
  const nodes = parsed.nodes.map((n: any) => ({
    id: n.id,
    type: "resource",
    position: n.position,
    data: {
      kind: "resource",
      provider:
        n.data.provider === "azure"
          ? "azure"
          : n.data.provider === "aws"
            ? "aws"
            : provider,
      label: String(n.data.label || "Imported block"),
      description: "Imported architecture reference — no fixture executor",
      service: n.data.service,
      origin: "OpenArchFlow import",
      config: {
        region: "To be selected",
        classification: "Internal",
        timeout: 5000,
      },
      metadata: n.data.metadata,
    },
  }));
  const layout = getLayoutedElements(nodes, edges, "LR");
  return {
    version: 1,
    revision: 1,
    name,
    provider,
    nodes: layout.nodes,
    edges: layout.edges,
    requirements:
      "Imported architecture reference. Assign fixture behaviours explicitly before running. Relationships do not grant access or imply runtime compatibility.",
    importReport: {
      droppedEdges: parsed.edges.length - edges.length,
      notice:
        "Architecture-only import. Sequence lifelines, table port handles and non-runtime presentation are normalised; source-specific metadata is kept where available.",
    },
  };
}
export function importDiagram(code: string, format: string) {
  if (code.length > 100000) throw Error("Paste fewer than 100,000 characters.");
  if (format === "mermaid" && !/^\s*(flowchart|graph)\b/i.test(code))
    throw Error("This integration currently supports Mermaid flowcharts only.");
  if (format === "sql")
    return convertGraph(parseSqlDdl(code), "Imported database schema");
  if (format === "mermaid")
    return convertGraph(parseMermaid(code), "Imported architecture diagram");
  throw Error("Unsupported import format.");
}
export function importUpstreamProject(raw: any) {
  if (!raw || !Array.isArray(raw.nodes) || !Array.isArray(raw.edges))
    throw Error("OpenArchFlow import needs nodes and edges.");
  const allowed = new Set(["aws", "azure", "gcp", "ibm", "tools"]);
  const p = convertGraph(
    raw,
    String(raw.name || raw.diagramName || "OpenArchFlow architecture"),
  );
  p.nodes = p.nodes.map((n: any) => ({
    ...n,
    data: {
      ...n.data,
      provider: allowed.has(n.data.provider) ? n.data.provider : "tools",
    },
  }));
  return p;
}
export function loadUpstreamTemplate(id: string) {
  const t = TEMPLATES.find((t) => t.id === id);
  if (!t) throw Error("Unknown template.");
  return convertGraph(
    t,
    t.name,
    t.category === "AWS" ? "aws" : t.category === "Azure" ? "azure" : "tools",
  );
}
export function autoLayout(project: any) {
  const nodes = project.nodes.map((n: any) => ({
    ...n,
    data: { ...n.data, inputPosition: "left", outputPosition: "right" },
  }));
  return { ...project, ...getLayoutedElements(nodes, project.edges, "LR") };
}
