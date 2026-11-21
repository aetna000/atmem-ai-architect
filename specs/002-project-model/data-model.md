# Data model: AtMem AI Architect project 2.1.0

2.1.0 (minor, backwards compatible) adds `discovery.facts|workflow|asked|lastAsked|sketchOffered`, `estimate` (usage overrides, sourced unit prices, range factors) and `review.accepted` (accepted risks).

## File shape (`.atforma.json`)

```jsonc
{
  "format": "atforma.project",
  "formatVersion": "2.1.0",
  "meta": { "id": "uuid", "name": "…", "createdAt": "ISO", "updatedAt": "ISO", "revision": 7, "generator": "atforma-workbench 0.2.0", "domain": "maintenance" },
  "design": { "provider": "aws", "nodes": [ /* components */ ], "edges": [ /* connections */ ] },
  "discovery": { "problem": "…", "brief": { /* 001 fields */ }, "useCases": [], "gate": {} },
  "requirements": [ /* Requirement */ ],
  "assumptions": [ /* Assumption */ ],
  "openQuestions": [ /* OpenQuestion */ ],
  "decisions": [ /* Decision */ ],
  "options": { /* assessment: weights, scores, notes */ },
  "extensions": { /* unknown fields preserved verbatim */ }
}
```

## Entities

| Entity | Fields | Rules |
|---|---|---|
| Component | `id`, `position {x,y}`, `data {label, kind, provider, description, config {region, classification, timeout}, origin, poc?, measures?, service?, category?, inputPosition, outputPosition}` | kind ∈ 13 kinds; provider ∈ aws, azure, gcp, ibm, tools |
| Connection | `id`, `source`, `target`, `label` | endpoints exist; no self-loops |
| Requirement | `id`, `kind` (functional, nonfunctional), `category`, `statement`, `priority` (must, should, could), `status` (open, met, at-risk, not-met), `source` (user, agent, import), `links[]`, `measure? {metric, op, target, unit}` | op ∈ `>=`, `<=`, `==`; numeric target for `>=`/`<=` |
| Assumption | `id`, `statement`, `source`, `owner`, `links[]`, `madeAt` | `madeAt` is the date the statement was made (time-sensitive) |
| OpenQuestion | `id`, `question`, `owner`, `status` (open, answered), `answer`, `links[]` | answer required when answered |
| Decision | `id`, `subject`, `title`, `status` (Proposed, Accepted, Superseded), `owner`, `date`, `revision`, `context`, `options`, `decision`, `consequences`, `supersedes?`, `supersededBy?`, `reason?` | at most one non-superseded decision per subject; `reason` required when `supersedes` set |

## Internal (browser) model

The browser keeps the flat version 1 shape plus new arrays, so existing code paths continue to work:

```text
project = { version: 1, revision, name, provider, domain, requirements: "<problem text>", nodes, edges,
            brief, useCases, assessment, gate, decisions,
            needs: Requirement[], assumptions: Assumption[], openQuestions: OpenQuestion[], extensions }
```

`needs` holds Requirement records because `requirements` already holds the problem text in version 1. The file uses the clear names (`discovery.problem`, `requirements`).

## Migrations

| From | To | Steps |
|---|---|---|
| workbench v1 (`version: 1`, no `format`) | 2.0.0 | wrap into sections; `requirements` text → `discovery.problem`; decisions gain `subject` (`general.<id>`) |
| 2.x (higher minor) | 2.0.0 reader | unknown top-level and section fields → `extensions` |
| 3.x+ | — | refuse |

## Credential patterns (refused)

`AKIA[0-9A-Z]{16}`, `sk-[A-Za-z0-9_-]{20,}`, `sk-ant-[A-Za-z0-9_-]{20,}`, `AIza[0-9A-Za-z_-]{35}`, `ghp_[A-Za-z0-9]{36}`, `-----BEGIN [A-Z ]*PRIVATE KEY-----`, and any object key named `password`, `secret`, `apiKey`, `api_key`, `accessKey`, `token` with a non-empty string value.
