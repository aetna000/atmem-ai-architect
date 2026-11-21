# Acceptance evidence

- [x] Visible user bubbles and safe formatted architect responses.
- [x] Clipboard image paste, document upload and explicit Send verified in `scripts/chat-browser-check.mjs`.
- [x] Transcript survives browser refresh; names retained without attachment bytes.
- [x] Project-file round trip, unchanged revision, separate projects and 40-turn preservation verified in `tests/conversation.test.mjs`.
- [x] Compact desktop/mobile controls and separate dialog close checked with browser bounding boxes and screenshots.
- [x] Server attachment validation and native transport contracts: 108 server tests passed.
- [x] Actual Codex vision identified the image label and document constraints; see evidence/live-vision.json. This is model evidence, not deployment evidence.

Screenshots and fixture browser results are in evidence/. Real cloud deployment and live vision on other connectors are not claimed.
- [x] Final regression: 188 JavaScript tests, 108 server tests, voice/main journey/delivery browser suites and production build passed. Build retains the existing large-chunk warning.

## Sticky-note follow-up

- Paper edges tilt independently of editable text and graph handles; a folded corner and shadow distinguish comments from components.
- Context menu uses icons, pink hover and a separator before destructive actions.
- Empty-canvas guidance no longer intercepts right-clicks.
- Blank notes are valid at the chat boundary; architecture component names remain mandatory. Regression: server/tests/test_note_contract.py.
- Live port 5190 accepted a blank-note request through schema validation (disabled Bedrock returned 409, with no model/cloud execution). Transport also represents empty annotations as whitespace for older sidecars, preserving node IDs and connections. 189 JavaScript and 110 server tests passed.
