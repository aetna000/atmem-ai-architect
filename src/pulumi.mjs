/** AtMem AI Architect's initial Pulumi interchange. Does not execute infrastructure commands. */
export function importPulumiSnapshot(raw) {
  const deployment = raw?.deployment || raw;
  if (
    !deployment ||
    !Array.isArray(deployment.resources) ||
    deployment.resources.length > 1000
  )
    throw Error(
      "Expected a Pulumi stack export with deployment.resources (up to 1,000 resources).",
    );
  if(deployment.resources.some(r=>!r||typeof r!=='object'||typeof r.type!=='string'||typeof r.urn!=='string'))throw Error('Pulumi resource metadata is invalid; no resource was silently discarded.');
  const resources = deployment.resources
    .filter(
      (r) =>
        typeof r.type === "string" &&
        typeof r.urn === "string" &&
        !r.type.startsWith("pulumi:"),
    )
    .map((r, i) => {
      const name=r.urn.split("::").at(-1);
      if(!r.urn.startsWith('urn:pulumi:')||r.urn.length>600||!r.type||r.type.length>200||!name||name.length>150)throw Error('Pulumi resource identity exceeds the supported metadata bounds or is invalid; nothing was clipped. Preserve the original export.');
      return ({
      id: `observed-${i}`,
      urn: r.urn,
      type: r.type,
      name,
      provider: r.type.startsWith("aws:")
        ? "aws"
        : r.type.startsWith("azure")
          ? "azure"
          : r.type.startsWith("gcp:")
            ? "gcp"
            : r.type.startsWith("ibm:")
              ? "ibm"
              : "tools",
    });});
  if(new Set(resources.map(r=>r.urn)).size!==resources.length)throw Error('Duplicate Pulumi resource identities require an explicit ownership decision; no resource was selected or discarded.');
  // Never retain inputs, outputs, secret envelopes, credentials, provider config or raw state.
  return {
    kind: "imported-pulumi-snapshot",
    importedAt: new Date().toISOString(),
    liveRefresh: false,
    resources,
    notice:
      "Imported state metadata only. Not a live cloud refresh. Inputs and outputs were discarded.",
  };
}
export function snapshotToProject(snapshot) {
  if (snapshot.resources.length > 100)
    throw Error("Select a snapshot with at most 100 resources for the canvas.");
  return {
    version: 1,
    revision: 1,
    name: "Pulumi snapshot — proposed design import",
    provider: "tools",
    requirements:
      "Explicitly imported resource references from a Pulumi stack export. No properties, secrets, cloud access or live drift verification are included.",
    ...(snapshot.resources.some(r=>r.urn)?{extensions:{externalReferences:{version:1,references:snapshot.resources.filter(r=>r.urn).map(r=>({componentId:r.id,source:'pulumi-stack-export',externalId:r.urn,resourceType:r.type}))}}}:{}),
    nodes: snapshot.resources.map((r, i) => ({
      id: r.id,
      type: "resource",
      position: { x: (i % 3) * 310, y: Math.floor(i / 3) * 230 },
      data: {
        label: r.name,
        provider: r.provider,
        kind: "resource",
        description: r.type,
        origin: "existing",
        binding: "existing-service",
        service: r.type,
        config: {
          region: "Unknown — not imported",
          classification: "Internal",
          timeout: 5000,
        },
      },
    })),
    edges: [],
  };
}
export function pulumiScaffold(project, environment = "staging") {
  const graph = project.nodes.map((n) => ({
    id: n.id,
    name: n.data.label,
    provider: n.data.provider,
    kind: n.data.kind,
    dependsOn: project.edges
      .filter((e) => e.target === n.id)
      .map((e) => e.source),
  }));
  return {
    "Pulumi.yaml":
      "name: atforma-design\nruntime: nodejs\ndescription: AtMem AI Architect architecture scaffold; no cloud resource implementations\n",
    "package.json": JSON.stringify(
      {
        name: "atforma-design",
        private: true,
        scripts: { typecheck: "tsc --noEmit" },
        dependencies: { "@pulumi/pulumi": "3.273.0" },
        devDependencies: { typescript: "5.9.3", "@types/node": "22.19.11" },
      },
      null,
      2,
    ),
    "tsconfig.json": JSON.stringify(
      {
        compilerOptions: {
          target: "ES2022",
          module: "commonjs",
          strict: true,
          esModuleInterop: true,
          skipLibCheck: true,
        },
        include: ["index.ts"],
      },
      null,
      2,
    ),
    "index.ts": `import * as pulumi from '@pulumi/pulumi';\n\n// AtMem AI Architect revision ${project.revision}; ${environment}.\n// These metadata components are NOT cloud resources.\n// Implement reviewed provider-native resources before any infrastructure deployment.\nconst design = ${JSON.stringify(graph, null, 2)};\nconst blocks = new Map<string, pulumi.ComponentResource>();\nconst remaining = new Map(design.map(block => [block.id, block]));\nwhile (remaining.size) {\n  let progress = false;\n  for (const [id, block] of remaining) {\n    if (block.dependsOn.every(parent => blocks.has(parent))) {\n      blocks.set(id, new pulumi.ComponentResource('atforma:design:Block', id, { label: block.name, provider: block.provider, kind: block.kind }, { protect: true, dependsOn: block.dependsOn.map(parent => blocks.get(parent)!) }));\n      remaining.delete(id); progress = true;\n    }\n  }\n  if (!progress) throw new Error('Design contains cycles or missing dependencies');\n}\nexport const designRevision = ${project.revision};\nexport const environment = ${JSON.stringify(environment)};\nexport const cloudResourcesImplemented = false;\n`,
    "README.md": `# AtMem AI Architect Pulumi scaffold\n\nDesign revision ${project.revision}; environment ${environment}.\n\nThis scaffold registers metadata ComponentResources only. It does not provision cloud resources, create network connections, enforce IAM, or implement AI inference. Wire dependencies express ordering only. Do not treat a successful preview of this scaffold as cloud validation.\n\nNext: implement provider-specific resource constructors and configuration, review costs/permissions, then run Pulumi preview in a separately configured staging stack.\n\nPulumi import brings existing resources into management; refresh updates recorded state from cloud reality. Neither automatically reconstructs an arbitrary application graph or edits its source code. AtMem AI Architect currently imports sanitised metadata from stack-export JSON; it does not execute import, refresh, preview, or update.\n`,
  };
}
