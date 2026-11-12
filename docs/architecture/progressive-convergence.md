# Progressive architecture convergence

Owner direction: start with an intelligible topology, resolve consequential system
questions, then drill into contracts and implementation. A deployment goal must not
immediately become a port/Dockerfile questionnaire.

## One system, progressively exposed

Topology shows users, external systems, major responsibilities and named flows.
Components reveal the services within a selected responsibility. Block detail holds
contracts, scoped questions, design advice and implementation settings. All views use
one graph; topologyGroup is a presentation grouping, never a new deployed service.
Legacy diagrams without responsibility groups remain visible without inventing them.

Question priority follows the decision unlocked and the consequence of a wrong
answer: outcome/scope, existing-system ownership, user/data/access/money boundaries,
interfaces/state/failures, then implementation settings. Routine engineering choices
can be proposed with visible assumptions; consequential business decisions need the
owner. Direct technical questions still receive direct answers. Do not demand another
answer when the known information already supports a useful improvement.

## Judgment and the improvement direction

Architecture is a discrete, constrained design search; literal differentiable gradient
descent does not describe the graph edits. The intended feedback controller compares
candidate changes against preserved requirements and independent evidence:

1. Preserve accepted outcomes, scope, ownership and explicit constraints as invariants.
2. Keep a quality vector: requirement coverage, boundary/contract completeness,
   implementation correctness, security/reliability evidence and operational fitness.
3. Choose the highest-consequence unresolved decision or failed check. Ask the user
   only when the answer changes the design and cannot responsibly be proposed.
4. Make a bounded candidate change; name the expected improvement and affected checks.
5. Rebuild and compare independent results against the previous artifact. Reject
   constraint regressions even if a weighted score or diagram appearance improves.
6. Retain the better supported candidate, unresolved uncertainty and repair evidence.

Mandatory access/ownership/security failures cannot be compensated by better cost or
more green badges. Counts of questions, blocks or passing checks are not objective
quality. An existing browser is an external actor, not a missing cloud deployment.
No runtime checks means no runtime validation, regardless of an empty failures list.

At topology level, judge coherent responsibilities, boundaries and preserved scope;
at contract level, judge identity/state/interfaces/failure behavior; at implementation
level, judge emitted code/resources, configuration and tests. Unknowns may be deferred
visibly to the relevant level; they cannot be deleted to improve a score. Deployment
qualification remains separate and requires authorized account/runtime evidence.

## Implementation boundary

Implemented: visible topology/component views; explicit responsibility membership;
block review states, scoped model notes/questions and stored user answers; stale-review
invalidation; server-owned consultation focus; optional structured follow-up rather
than forcing the next checklist question. These are foundations for the controller.

Not yet implemented: a general candidate search/selection optimizer, comprehensive
cross-provider connected-application compilers or a validated numeric architecture
quality score. The six-step controller above defines the next engineering target,
not an assertion that it is already running. Hold-out complete-system evaluations and
independent runtime qualification must establish improvements in practice.
