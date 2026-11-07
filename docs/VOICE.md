# Local voice input: implementation and verification

7 November 2026, branch `fix/voice-conversation` (PR #3). The owner's clarified
requirement supersedes the earlier spoken conversation loop: live editable
voice-to-text, explicit posting, and output on the design. No playback/auto-send.
No application version bump or package publication is part of this correction.

## Behaviour and data flow

Start dictation requests the normal browser microphone permission after an
application disclosure. Web Audio captures mono audio; the client resamples to
16 kHz PCM, keeps a bounded in-memory clip and sends progressive WAV snapshots to
`/api/voice/transcribe` on the loopback helper, normally about once per second.
Only one decoding request per recorder is active. The resulting words appear in
the composer; partial hypotheses can revise earlier words. Nothing goes to the
architect or changes the design until the user presses Send.

Stop releases microphone tracks and finishes the latest words. Send while
recording first finishes the transcript and posts it once. The normal architect
path returns text/design proposals, retaining the existing review, live-drawing,
decision and undo rules. Typing cancels capture and protects the user's edits.
Epoch checks fence late transcription/permission events. No SpeechRecognition or
SpeechSynthesis browser service is used. The app handles a helper token refresh
once without changing accounts or posting a message.

The helper validates session token, Host/Origin, WAV framing, mono 16-bit PCM,
16 kHz rate and a maximum 60-second/1,920,000-byte PCM payload. A local worker
keeps the existing Whisper tiny.en checkpoint warm and decodes via private pipes.
Requests wait for model preparation rather than treating first-use warmup as a
microphone error. Worker startup/request/queue waits are bounded; shutdown closes
the worker. Audio is not written to project files, AtMem, logs or temporary files.
Browser/HTTP/worker memory contains the clip while processing; only explicitly
submitted text follows the existing chat/memory path.

Whisper is an optional existing local installation, not a new mandatory Python
dependency. `python3 scripts/setup-voice.py` downloads the official checksum-verified
tiny.en weights (~72 MiB) once. The recording endpoint never downloads a model or
calls a paid speech API. The current adapter requires an executable Python
shebang from the installed `whisper` CLI (verified on this macOS installation;
Windows transcription is not qualified). See [upstream Whisper](https://github.com/openai/whisper)
for its installation and licence. No claim of ChatGPT recognition quality, exact
latency, universal browser/OS support or physical microphone certification.

## Measured evidence

- `npm test`: 120 passed, including 10 dictation tests: progressive draft, silence,
  stop/finalise, late callback cancellation, delayed microphone permission,
  failed decode, pending-partial flush, denied microphone, unchanged audio,
  WAV framing/clipping and resampling.
- `npm run test:server`: 53 passed, including new audio auth/origin/type/rate/channel/
  duration/size/error contracts and first-partial-during-warmup concurrency.
- `npm run test:voice`: passed with synthetic browser microphone PCM and fixture
  transcription/model HTTP transports. It verifies incremental words in the actual
  composer, zero model calls before Send, Stop, finalisation on Send, exactly one
  user-triggered request, actual graph proposal application, permission failure,
  release of tracks and mobile status layout. Browser speech-service/playback
  accessors deliberately throw if used. Desktop/mobile screenshots inspected.
- Real local recognizer over authenticated HTTP: generated macOS speech, converted
  to 16 kHz WAV with ffmpeg, was transcribed by the actual warmed Whisper worker.
  Initial warmup: 2.52 seconds. Partial clip: 0.51 seconds, returning "created
  document assistant using." Complete clip: 0.28 seconds, returning "created
  document assistant using Azure in Australia." The source phrase began "Create";
  this is wiring/timing evidence on one synthetic phrase, not an accuracy benchmark.
  No microphone audio, model account or architecture-generation call was involved.
- The existing isolated real-AtMem browser journey passed again after the local
  audio changes (discovery, design, scoped memory/history/forget, save/reset and
  mobile); model/prices remain fixtures. The actual running helper at port 5174
  also transcribed the generated WAV successfully, and its frontend passed the
  dictation UI test in a separate browser context.
- Production build passed; existing non-fatal React Flow directive/bundle-size
  advisories remain. Source whitespace checks passed.

The existing combined browser gate has an independently reproduced baseline
failure: `scripts/delivery-smoke.mjs:100` finds horizontal overflow in the mobile
Outputs view. The same assertion failed unchanged at baseline `661324c`; it has
not been removed or skipped. Do not describe the combined browser gate as green.
Two old branding expectations in the memory journey were aligned with the
already released header/default light theme. Live hardware permission, device
selection and recognition with the owner's voice remain an operator check.

Test-only generated audio/results are under
`/private/tmp/architect-local-dictation-evidence/`; logs are
`/private/tmp/architect-dictation-*.log`, screenshots
`/private/tmp/atmem-architect-voice/`. These are synthetic operator evidence,
not production retained audio. The local app at port 5174 requires the updated
helper; its owned launcher was restarted to load the audio routes.
