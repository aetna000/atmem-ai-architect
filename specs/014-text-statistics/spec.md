# Native authenticated text statistics

Provide a typed `text-statistics` Lambda implementation: Python handler, execution role, scoped log permissions, managed log group, immutable published version, stable live alias, explicit existing-principal invocation permission, and executable application tests. No generated function URL or public endpoint. Input is exactly {"text": string}; counts use Unicode code points and whitespace-delimited words. Invalid/oversized payloads fail without logging document text.

Reviewable defaults: 128 MiB, 10-second timeout, concurrency 1, 64 KiB input text, 30-day log retention. These are implementation defaults, not confirmed customer performance/compliance requirements; expose validated Terraform inputs. Existing roles are referenced through required ARN inputs. Rollback can point the alias at a prior published version. Other Lambda behaviors must not receive this implementation by matching labels alone.
