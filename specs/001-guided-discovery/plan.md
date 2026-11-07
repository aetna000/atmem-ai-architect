# Guided discovery live dictation plan

Owner clarification supersedes the earlier spoken conversation loop. Implement
FR-008–FR-011: live voice-to-text, editable draft, explicit Send and design output.
There is no TTS, auto-send or dependency on browser-vendor speech recognition.

Capture via browser getUserMedia/Web Audio, resample mono PCM to 16 kHz and send
bounded cumulative WAV snapshots at roughly one-second intervals to the authenticated
loopback helper. Only one transcription request is active per recorder. A local
Whisper worker retains a warmed tiny.en model, returns progressive transcript text
and never writes audio files. Raw PCM crosses only the loopback boundary and worker
pipes; it does not enter chat/memory. No model download during recording.

Stop stops tracks and flushes pending audio. Send awaits the flush, then posts the
reviewed transcript through the existing send path once. Typing/project replacement/
unmount cancels and fences late audio/model results. The sidecar enforces format,
duration, request limits, process timeout/concurrency and existing session/Host/Origin
authorisation. One bounded session-token refresh tolerates helper restarts.

Explicit setup reuses a local Whisper installation and downloads checksum-verified
official tiny.en weights (~72 MiB). No paid API or new mandatory Python dependency.
Document Whisper/model/CPU requirements and the 60-second recording bound.

Constitution I–VIII: user explicitly posts; no invented output/latency; existing
project/proposals stay canonical; local-first audio with bounded authenticated
transport; browser/provider limits explicit; memory semantics unchanged; accessible
status and microphone control; controller, HTTP boundary and UI regression tests.

Validation: synthetic PCM capture browser fixtures prove progressive drafts, no
submission/playback until Send and real canvas updates. Real local engine HTTP test
uses generated speech and records partial/final text and timing separately. Run
unit/sidecar/build/existing journeys; preserve known baseline delivery-layout failure.
Physical microphone/OS permissions are not certified by generated or mocked audio.

Diagram change attention: compare node data/position/type and connections before application; keep affected IDs in transient React state, decorate React Flow elements and fit the affected nodes after measurement. Suppress competing whole-canvas fits during the cue, clear timers on replacement/unmount, and respect reduced motion. Verify diff targeting in unit tests and highlight, zoom, expiry and reduced motion in the browser proposal journey.
