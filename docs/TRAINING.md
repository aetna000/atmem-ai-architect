# AtMem AI Architect training: your first AI architecture

This walkthrough teaches the local design workflow. It is not model training
or a cloud deployment exercise. [Install AtMem AI Architect](INSTALLATION.md) first, open
the local application and choose Local patterns or an explicitly configured
model connection. Local patterns is a bounded fallback; a connected model
request may consume provider usage.

## Exercise: a small internal document assistant

Use a fictional project so the first exercise needs no customer information:

> Design an internal document assistant for ten colleagues. Use approved
> documents only, show sources with answers and keep data in Australia. We
> have not chosen a cloud or monthly budget yet. Ask me about the missing
> decisions before treating them as requirements.

The connected architect asks discovery questions and drafts a sketch. Treat
its initial recommendations as proposals. If a detail is unknown, say so;
keep it as an assumption or open question rather than inventing a value.

## 1. Sketch and document

Describe the users, existing systems, document sources, expected usage,
access boundaries and desired outcome. Review components and connections
on the canvas. Add a comment or explain a change in chat.

With **Draw as we talk** enabled, semantic diagram edits are sent to the
architect and its diagram proposals can be applied as they arrive. Use
**Undo / Redo** to inspect or reverse a board change. Routine dragging does
not itself trigger a consultation.

Open the requirements document. Distinguish confirmed requirements from
**Suggestions still to discuss**. Use **Explain why we need this**, **Discuss**
or **Clarify with AtMem AI Architect** to continue the interview. Stable REQ numbers
help track each requirement across revisions.

Try changing one requirement: use **Comment or request a change**, then
**Suggest a revision**. Compare current and proposed wording. Choose
**Apply this revision**, **Keep current wording**, or save feedback for later.
A document proposal is not a cloud or board deployment action.

## 2. Compare cloud options

Choose **Continue to cloud options** after reviewing the working scope.
Compare the proposed service combinations and their assumptions. The options
are architectural judgments, not validated compatibility or price quotes.
**Preview service architecture** creates a pending alternative; it does not
select a cloud or replace the current board automatically.

Choose a provider using **Choose AWS & continue** or the corresponding
Azure, Google Cloud or IBM action. There is no universally best provider;
base the choice on the stated project constraints and missing information.

## 3. Refine country, region and service architecture

Answer the data-residency questions. Review named services, placement and
connections. Explain which existing resources should be referenced instead
of recreated. Revisit the journey strip to amend a reached stage; a changed
scope or architecture can reopen an earlier checkpoint.

Country selection is not proof that every proposed service, model or data
flow satisfies the residency requirement. Retain that verification work in
the project and handoff.

## 4. Review the design

Discuss security, reliability, availability, scalability, performance,
maintainability and cost findings. Inspect each finding's reason and action.
If accepting a risk, record its owner and reason. An accepted risk remains
an explicit decision; it does not prove that a control is implemented.

Sample-data **Test run** fixtures exist for selected templates. They are
local simulations, not real cloud or application acceptance tests.

## 5. Build an estimate with assumptions

Provide expected users, requests, model usage, storage, currency and region
when known. Inspect the summary, sources, missing rates and cost drivers.
A rough order of magnitude uses stated low/high factors; detailed charge
lines should retain quantity, unit, service, region, date and source.

Supported automatic storage prices cover selected AWS S3 Standard and Azure
Blob Hot LRS cases. Google Catalog lookup needs the documented API access;
IBM needs a sourced quote. This is not full service-price coverage. Keep
uncosted components, stale rates and mixed currencies visible. Do not turn
missing rates into zeros or a guaranteed monthly bill. Record one-off
engineering effort separately from recurring cloud costs.

## 6. Inspect outputs and download a delivery pack

Choose **Outputs** once a diagram exists. Review the directory groups:
**Spec Kit**, **Specification & handoff**, **Design**, and **Terraform**.
Inspect the generated documents, numbered requirements, diagram, estimate,
resource schedule, decisions, engineering gaps and implementation tasks.
Use **Download reviewed ZIP** for the displayed snapshot. If the project
changes, wait for the outputs to regenerate and review them again.

The coding-agent kit includes `START_HERE.md`, `AGENTS.md`, a project-specific
implementation specification, task dependencies, acceptance criteria,
questions and a progress ledger. Receiving agents must resolve missing
contracts and permissions; a generated kit is not already implemented code.

Terraform output remains a partial draft. Native AWS S3 foundations are
represented for selected proposed S3 blocks; other services and integrations
remain unfinished. Optional **Run Terraform checks** validates generated
provider schemas through the local service. It does not perform a real cloud
plan or apply, prove permissions, deploy resources or test the application.

## 7. Save, reopen and inspect memory

Use **Save project file** to keep an editable `.atforma.json`, then **Open
project file** to revisit it. Confirm the diagram, requirements, decisions and
open questions are present. Regenerate outputs after a change. Project files
and delivery packs can contain your project information; handle them as your
own documents and never add credentials.

Open **⋯ → AtMem dashboard**. Inspect **About you**, **This project**, **Skills**
and **Activity**. Explicit reusable preferences, accepted project decisions
and selected authored requirements can qualify for memory. Draft chat,
canvas positions and ordinary comments do not automatically become personal
memory. Inspect current and earlier values, preview forgetting, or turn
memory off per project. Content entered while opted out is not replayed later.

## Completion checklist

- The diagram and requirements describe the same intended project.
- Facts, assumptions, suggestions, decisions and open questions are distinct.
- Cloud choice, region, price sources and missing cost coverage are explicit.
- Risks and implementation/deployment gaps remain visible.
- The reviewed output ZIP and editable project file represent the intended snapshot.
- No infrastructure has been provisioned by this exercise.

For a later session, reopen the saved project and continue from its working
state. For installation issues, see [installation and troubleshooting](INSTALLATION.md).
For hosting boundaries, see [self-hosting](SELF_HOSTING.md).
