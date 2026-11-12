# Cost and delivery clarity — 2026-11-12

Owner asks for project-size assumptions instead of manually entering every quantity,
one purpose per stage, and one final package download. This is authorized UI work;
the original28/native engine programme stays paused.

Implemented: Small/Medium/Large/Extra Large planning sizes; explicit usage and discovery
facts take precedence, and selected size survives project import/export sanitization.
No preset prices, invented quotes, training hours or changed requirements/provider/region.
The estimate action asks the existing Architect/pricing tools to price the saved design;
its response cannot apply topology, requirement, usage or cloud-choice changes. Price
quotes still pass existing source/provider/region checks. Routine quantities are visible
assumptions; advanced worksheets and repeated unresolved cost rows are collapsed.

Terraform routes to Delivery. Implementation workspace routes to Delivery and no longer
offers a second original archive. Delivery offers one combined handoff download when a
captured package can be packaged. Its original archive remains inside that combined ZIP.
Without engineering enabled, the only download is explicitly a design-only package.
Saving, artifact identity, source digest, stale-design classification and check gates remain.

Validation:569 JavaScript tests/zero skips; production build; desktop1440/mobile390
component browser fixtures cover preset selection, explicit override, no premature
package, and exactly one package control after capture. Full engineering fixture passes:
start/steer/recovery, existing queued intent, model selection, check state/reload and
Delivery navigation. One earlier attempt hit navigation during concurrent build/HMR;
settled-build rerun passes. Existing package verification unit tests remain unchanged.

Limits: current automated pricing supports selected storage services only, not all cloud
billable dimensions. Size selection does not manufacture a dollar total for unpriced
services. Complete automatic cross-service pricing is still required. No new native run,
cloud plan, deployment, live-price accuracy or full-system acceptance claim. Terraform
preview check receipts are still separate from native artifact checks; do not imply that
an unrelated receipt validates a captured implementation. No CSS files changed.
