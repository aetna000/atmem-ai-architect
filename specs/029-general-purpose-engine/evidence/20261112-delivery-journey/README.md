# Delivery tied to a captured implementation

Reusable capability: tenant/project-scoped delivery inspection and lossless receiving packaging, independent of provider, business domain, native adapter and deployment. Uses existing immutable artifact/context/check receipts and saved project data; no model, command execution, recovery or cloud action on opening Delivery.

Delivery now selects the most recently captured implementation for the authorized project, exposes exact-artifact checks and links from Implementation through Review and download handoff. The compiler design draft stays available under an explicitly separate details section. The Board action strip no longer repeats unrelated actions on Delivery.

A submitted-context receipt and current completed native run are required for combined packaging. Unknown/earlier-turn artifacts remain explicitly historical, with the original immutable download available. A saved-context difference is visible; changed requirements are retained without claiming implementation. Only export updatedAt is excluded from semantic comparison; other context differences stay conservative review signals.

Explicit download confirms the current browser design save and refreshes its receipt. Changed design/package identity requires review rather than silently downloading a different version. The server checks the expected design identity again. The handoff includes a receiving implementation/ tree, exact original implementation ZIP, submitted and latest saved project files, artifact receipt and original check results. Source bytes, executable bits and paths remain preserved. It creates no substitute implementation or Spec Kit. Standard native specs/<feature>/ and design-compiler spec-kit/ layouts remain valid; file presence is not semantic acceptance.

The browser independently checks transport hash, original ZIP hash, full receiving file inventory and each file hash against the selected artifact. Wrong transport/source/embedded original, changed/missing/extra files are denied. Expanded receiving size has an explicit150MB client bound; the original artifact adapter bounds source to64MB. Larger handoffs retain their original download instead of silently truncating content.

Validation:558 JS tests/no failures/skips;479 server tests pass; production build passes with the existing chunk warning. Six new real SQLite/artifact/context/receiving tests include actual authenticated ASGI delivery/download/unpack; two route tests cover scope/override/read-only behavior. Real browser fixtures cover missing/current/changed/unknown implementation, save failure, checksum denial and unpack, plus existing engineering lifecycle/navigation/review. Browser service/model responses are synthetic, not live generation or cloud evidence.

Real prior Google native archive69bdacf7 independently receives through the product packager from a read-only SQLite backup:159 files rehashed, seven standard Spec Kit files retained, exact original archive verified, submitted/current context matches. Its one registered failed check remains failed. No original DB/source write, new native turn, application execution or full-system requalification. Earlier separate independent runtime successes remain separate; this wrapper does not replace failed history with those results.

Failed evaluator attempts retained on MEM0: first receiving oracle assumed only spec-kit/ and was corrected to the actual standard specs/<feature>/spec.md, plan.md and tasks.md; ASGI fixture initially crossed SQLite threads via TestClient and was corrected to the production same-thread async transport. Neither required a generated-source fix or weakened receiving hash assertion. Bulk logs/archives/screenshots/database copy: .local/external-artifacts/delivery-journey/.

Reproduce real receiving from repo root with a fresh MEM0 output directory:

    .venv/bin/python -c "import runpy; runpy.run_path('specs/029-general-purpose-engine/evidence/20261112-delivery-journey/check-native-receiving.py', run_name='__main__')" /absolute/MEM0/fresh-directory

UI-001 remains in progress: finish remaining navigation/menu duplication, real fresh generation-to-handoff usability and OpenAI voice. No alpha.5, original28, owner acceptance or measured-quality promotion. Existing owner5288 untouched.
