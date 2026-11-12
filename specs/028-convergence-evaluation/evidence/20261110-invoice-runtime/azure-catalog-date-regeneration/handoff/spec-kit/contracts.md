# Component and interface contracts

Snapshot 9e56b56c-f354-4d86-9089-eba95a5c71e8 · design r4 · generated 2026-11-09T23:57:26.530Z

The board describes intent. These contracts must be completed before integrations are declared implemented.

## Component faq-visitors: Website visitors

- Responsibility: Existing visitor browsers outside provisioning scope. Submit questions over HTTPS and receive answers with article citations or an explicit abstention. No visitor account is proposed.
- Service: Web browser
- Provider / placement: tools / External client
- Ownership: Existing system; confirm access and ownership
- Implementation task: TASK-RESOURCE-6661712d76697369746f7273
- Still to specify: runtime/configuration, identities, input/output schemas, health checks, failure behavior and operational owner.

- Preserve the external browser; no resource or import is required.
- Define and test its HTTPS/application interactions, including denied access and unavailable service behavior.

## Component faq-app: Public help assistant

- Responsibility: Proposed composed public-faq-app on Azure App Service. Owns the browser/API, private Azure Blob Storage versioned public-article catalog, regional Azure model transport and separate editor/runtime identities; these are internal module resources, not additional independent deployments.

Included scope: anonymous visitor questions, cited answers or explicit abstention, and authorized CLI publication/update/deletion of twenty supplied public UTF-8 article files under 30 KB each. Only approved public articles may ground answers. Private-source ingestion, arbitrary URL fetching and visitor editing are excluded. No visitor account is required. Additional business actions, private enterprise access and general workflows are outside this proposed scope.

Retrieval recommendation: bounded keyword ranking inside the application over the current curated catalog, supplying at most two complete retrieved articles to the model. This avoids a separate managed search service, embeddings pipeline and vector database for this small collection. Keyword matching can miss paraphrases; qualify it with representative questions before launch. Do not claim semantic search or guaranteed factual accuracy. Treat questions and articles as untrusted data. Validate returned source membership and exact supporting quotes, and abstain when support is insufficient; valid citations alone do not prove entailment.

The authorized editor CLI conditionally adds, updates and removes articles. Conflicting writes fail; in-flight source changes withhold affected answers, and there is no cached-source fallback. Runtime has read-only catalog access. Exact editor identity and scoped destination permissions remain required, unverified inputs. Files are already UTF-8, so no PDF extraction or source connector is proposed.

Capacity evidence: user expects about 1,000 questions per day and five at once. Use approximately 30,000 questions per 30-day month only as an estimating convention. Propose one small always-on App Service instance initially, subject to measured capacity, model quota and destination review; no SKU or availability guarantee is established. The implementation admits at most five concurrent requests per instance; overload must be bounded and visibly rejected or retried rather than silently exceeding that limit. Built-in bounds remain 100 public articles, 30000 bytes per article, 2000-byte questions and two complete retrieved articles. Verify supplied file byte sizes against that exact limit. Do not treat these bounds as an invoice cap.

Location: Australia is preferred, not a confirmed Australian-only processing rule. Australia East (australiaeast) is proposed for application and storage, not approved. Australian application/storage placement does not establish model inference location. Before inference, verify exact Azure model/version, deployment type, availability, quota, processing geography, retention and abuse-monitoring policy. Do not silently select Global or Data Zone inference, overseas fallback or cross-region recovery. Present proposed processing outside Australia for user review. One region is proposed; zone redundancy and regional recovery are not established. Visitor browsers may be outside Australia.

Operations proposals: exclude question text and article bodies from application logs; record request outcomes, latency, errors, abstentions and catalog revision identifiers. Platform/model logging and retention need separate verification. Provide an editor runbook for conditional changes and reviewed recovery from a known catalog revision, with deliberate deletion semantics so deleted content is not silently restored. Operational ownership, response-time expectations and recovery targets remain open. Public endpoint abuse controls and spending alerts require implementation review; concurrency limits alone do not prevent sustained spend.

Acceptance work: bind checks to the emitted artifact; test anonymous question access, denial of unauthorized catalog writes, editor add/update/delete and stale-write conflicts, removed-source exclusion, source changes during a request, citation membership/supporting quotes, unsupported-question abstention, prompt-injection cases, catalog/model failures, five concurrent requests and overload behavior. Evaluate representative paraphrases and real-model answer support separately from scripted tests. Build, scan and test the emitted pinned Python 3.13 image; review native provider configuration, destination permissions and an account-specific plan. No exported artifact, runtime report, live model test or deployment evidence is supplied here.

Price evidence: Azure Retail Prices API result dated 2026-11-09 quotes Australia East Blob Storage Hot LRS base storage at USD 0.02/GB-month, covering only the base tier up to 51200 GB. Source: https://prices.azure.com/api/retail/prices?%24filter=serviceName+eq+%27Storage%27+and+armRegionName+eq+%27australiaeast%27+and+meterName+eq+%27Hot+LRS+Data+Stored%27+and+priceType+eq+%27Consumption%27+and+productName+eq+%27Blob+Storage%27 . Twenty files imply less than approximately 0.0006 GB of raw article text, an upper bound rather than measured billed storage; catalog encoding and retained versions add storage. Current prices are missing for App Service compute, the exact model's input/output tokens, storage operations, transfer, logging and recovery storage. Model/token usage is unknown. External browsers and the existing editor are reference actors with no proposed hosted resource charge; their devices, connectivity and editor labor are outside the cloud subtotal. Monthly cloud running costs remain incomplete. One-off build/consulting effort, rates and exclusions are separately unestimated.
- Service: Azure App Service
- Provider / placement: azure / australiaeast
- Ownership: Proposed component
- Implementation task: TASK-RESOURCE-6661712d617070
- Still to specify: runtime/configuration, identities, input/output schemas, health checks, failure behavior and operational owner.

- Confirm the exact azure service, deployment mode, region and supported resource types using current primary documentation.
- Specify runtime/artifact, identity, network paths, secrets, capacity, health checks and operational owner; resolve whether this is infrastructure or a responsibility within another application.
- Document service-specific failure modes, retention/recovery and acceptance tests; do not substitute a similarly named service or another provider.

## Component faq-editor: Authorized article editor

- Responsibility: Existing authorized operator outside provisioning scope; exact identity and destination permissions remain required inputs, not verified identities. Supplies twenty public UTF-8 help-article files under 30 KB each through the generated management CLI, then publishes, updates and removes catalog entries. Only public content is permitted. Conditional writes reject stale edits. This operational interface is separate from anonymous visitor access; it is not a browser editing endpoint. Editor ownership and recovery procedures remain to be assigned.
- Service: Existing authorized operator
- Provider / placement: tools / External operator
- Ownership: Existing system; confirm access and ownership
- Implementation task: TASK-RESOURCE-6661712d656469746f72
- Still to specify: runtime/configuration, identities, input/output schemas, health checks, failure behavior and operational owner.

- Identify system owner, tenant/location, supported APIs and permitted read scopes; document a reference contract instead of recreating the system.
- Specify identity mapping, source permissions, pagination/rate limits, update/delete events and maximum synchronization lag.
- Define credential rotation, outages and recovery; test revoked access and unavailable sources using approved fixtures before live integration.

## Interfaces

### faq-visitors-to-app: faq-visitors → faq-app

- Drawn payload/purpose: HTTPS questions → cited answers or “I don’t know”
- Contract task: TASK-CONTRACT-6661712d76697369746f72732d746f2d617070
- Integration task: TASK-INTEGRATION-6661712d76697369746f72732d746f2d617070
- Still to specify: protocol, schema/version, authentication, authorization, retries, timeouts, idempotency, error semantics, observability and test fixtures.

### faq-editor-to-app: faq-editor → faq-app

- Drawn payload/purpose: Authorized CLI: publish, update and remove public articles
- Contract task: TASK-CONTRACT-6661712d656469746f722d746f2d617070
- Integration task: TASK-INTEGRATION-6661712d656469746f722d746f2d617070
- Still to specify: protocol, schema/version, authentication, authorization, retries, timeouts, idempotency, error semantics, observability and test fixtures.
