# Source and licensing audit — local integration, 2026-11-01

## Scope

Three public repositories were pinned in `upstream-lock.json`. The current integration ports 18 tracked source modules, listed with original/destination hashes in `merge-manifest.json`, plus the earlier six description adaptations. This is a preliminary engineering inventory, not legal clearance or a production-readiness assessment.

| Source | Verified root licence | Current reuse |
| --- | --- | --- |
| OpenArchFlow | MIT | Catalogues, templates, parsers, layout and payload formatting; attributed adapted modules |
| AWS architect sample | MIT No Attribution | Agent/rate limiter and supporting modules in the local Python sidecar; neutral active prompt |
| AWS Labs MCP | Apache-2.0 | Disabled planning metadata only; no server code or execution |

The verified root licences permit commercial use subject to their conditions; none by itself requires publishing original product source. They do not clear third-party assets, dependencies, patents beyond their grants, trademarks, provider service terms or subscription usage. Preserve MIT copyright/permission notices. Apache redistribution requires the licence, applicable retained attribution/NOTICE and change notices in modified distributed files, and has an explicit conditional patent grant and trademark exclusion. MIT-0 does not require notice retention; full provenance is retained voluntarily.

## Integration review

The OpenArchFlow Next.js shell and AWS Streamlit UI are not executed. The unified canvas uses React Flow 12. The adapted Mermaid parser fixes upstream label loss and bracket-node wire parsing. SQL import remains a basic parser, not a complete SQL grammar. Imported architecture resources do not masquerade as runnable endpoints.

The AWS source includes automatic `@latest` MCP launch, an AWS-only prompt and a generic file-writing tool. AtMem AI Architect never calls its upstream `initialize()` and registers none of those tools. Only its composed agent retry/backoff/rate-limit path is used for explicit SDK access. Claude/Codex/Copilot/Gemini account adapters use official external clients in isolated local request processes. No account tokens are extracted or redistributed.

## Dependencies and assets

Node versions/integrities are locked in `package-lock.json`; Python versions are pinned in `server/requirements.txt`. Generated Node and Python inventories and supplied legal texts are distributed under `docs/` and `public/licenses/`. These inventories are scoped to packages installed on the verified Mac, not every platform-specific optional package, every file, or every future container. Missing/ambiguous licence metadata and wheel notices remain review items. Two native Node build packages lack root legal files; parent tool notices are included, but distribution review must verify their exact artifacts.

No cloud logo packs, upstream screenshot/video assets, model weights, sample secrets or upstream datasets are copied. Fonts use AtMem's system stack. The AtMem token snapshot and identity mark come from the user's private source; the original platform is unchanged. Pulumi SDK/CLI are not bundled; exported scaffolds declare a pinned SDK dependency for the user to review/install separately.

## Before commercial distribution

- Review exact shipped artifacts, all copied files and redistributed dependency/asset licences; generate release-target SBOMs and complete notices.
- Recheck upstream changes against pinned source and file-level obligations. Do not import arbitrary future upstream assets or execute upstream install/deployment scripts.
- Verify official model/client terms separately for local-user, desktop, internal-server and commercial hosted distribution. A local subscription adapter is not a licence to share one subscriber's account among customers.
- Establish ownership/licensing for original code and contributions. AtMem AI Architect is a requested working name; product-name/trademark clearance is not completed here.
- Complete authentication, credential isolation, quotas, data handling and cloud execution controls for any multi-user hosting. The current sidecar is loopback-only, single-user.

No atmem.ai website change or new publication is performed in this milestone. The local workbench now uses the pinned AtMem 2.3.10 core SDK in a separate environment, with scoped first-party dashboard routes. Memory dependency notices and pinned reference skill licences are recorded separately in THIRD_PARTY_NOTICES.md. Local fixture tests do not establish cloud interoperability, real cost, compliance, model quality, deployment success or a complete Pulumi round trip.
