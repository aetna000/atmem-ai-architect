# Preserve existing websites and services

An externally managed website or service can be represented without provisioning,
importing, replacing or modifying it. Select the existing block, open its inspector,
and choose **Existing system handling → Reference only — preserve existing service**.
The project retains its provider, service, IDs and connections and records
`origin: existing`, `binding: existing-service`. The same correction is available
through the connected architect. It does not convert proposed work to existing work.

Existing GCP blocks explicitly selecting `Firebase Hosting` or `Firebase App Hosting`
are recognized automatically when they have no implementation or other binding.
Labels alone are not used to infer this contract. Existing browser and IAM bindings
retain their own contracts.

Exports include `existing-references.json` and `EXISTING-SYSTEMS.md`. Reference-only
components do not generate cloud resources or import statements. No endpoint is
contacted and no external availability, permissions or behavior is asserted.
The normal and cross-cloud storage generators both support this boundary.

Connections and proposed application components still require implementations.
An export containing unresolved work remains blocked before runtime tests;
reference support is not general Cloud Run, Firebase Auth, reCAPTCHA, Firestore
or analytics implementation. Existing report digests remain historical; regenerate
and rerun to obtain evidence for the current design. The previous revision-12
artifact was not available as a saved project in this checkout and was not claimed
as tested.

Validation: 196 JavaScript tests, production build, 12 server/emulation tests,
including actual generated runtime execution with a preserved Firebase reference
and blocking of an unimplemented connection. Browser verification covers selecting
and persisting the explicit reference without changing its provider or ownership.
