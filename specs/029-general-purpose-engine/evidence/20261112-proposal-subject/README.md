# Proposal title application fix

Owner reported: “A project record exceeds80 characters” while using Architect.
`applyProposal` passes the proposal title into `slugSubject` before saving its
design decision. That derived-key helper incorrectly imposed an80-character input
limit even though decision titles support200. This rejects ordinary design
proposals without an opportunity to apply the design.

The engine now bounds only the generated subject slug. Long slugs retain a readable
prefix and16 hexadecimal SHA256 characters derived from the entire title, so
same-prefix/different-tail proposals remain distinct. Existing short slugs stay
identical. Full title/context/requirements and decision history are preserved;
actual content limits still reject oversize content explicitly without truncation.
This is an internal key, not a requirement or permission token. No domain dispatch.

Tests transfer to museum/weather titles with a shared long prefix and a long
Unicode title; validateImport/save/export/revision chains retain their content.
All554JS tests pass; production build passes with existing bundle-size warning.
The initial new fixture omitted its decision revision and compared undefined with
normalization's null; supplying the actual applyProposal revision corrected the
fixture without changing production normalization.

The existing alpha.3.1 preview on5285 receives only records.mjs plus cache-busted
main/records import URLs. Frozen candidates under.local are intentionally excluded
from Vite watching, so the first static browser check still observed the cached
old module. Explicit import URLs now serve the patch after refresh, verified
through actual root HTML/main and browser execution. The backend PID59742 on8878
was not restarted. No owner project/record write, inference, CSS or layout change
was performed. Source/browser/activation receipts are bound below.

Manual check: refresh5285 and retry applying/drawing the pending proposal with
a title longer than80 characters. Verify its full title in Design choices and
export. Owner manual acceptance is still pending; this is a patch, not a new
runnable increment or full-system qualification. Rollback: restore the three
frontend files from ignored MEM0 backups under
.local/external-artifacts/long-proposal-subject/v1; refresh the frontend import
URLs as needed. No backend/project rollback is needed.
