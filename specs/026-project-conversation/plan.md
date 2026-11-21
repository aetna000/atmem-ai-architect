# Implementation

Use the existing project storage and portable extensions, with a dedicated transcript serializer. Decorate persistence snapshots rather than mutate design state. Restore messages at each project boundary. Keep safe Markdown rendering separate from attachment validation and provider transport. Validate extracted documents in a bounded subprocess; validate image content before forwarding.

Verify unit round trips and unchanged revision, browser paste/upload/send/reload and layout, server attachment contracts and actual Codex vision. Do not equate these checks with cloud deployment.
