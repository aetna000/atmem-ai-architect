# External RAG and memory context contract

The local installation owns one stable Default profile. The backend derives user ID and project scope; callers cannot select another user or AtMem subject. A hosted deployment must supply authenticated tenant/user authorization before exposing this adapter.

Set the server-owned `ATMEM_ARCHITECT_MEMORY_CONTEXT_PROVIDERS` JSON setting (maximum four providers):

```json
[{"id":"team-rag","label":"Team RAG","kind":"rag","url":"https://rag.example/context","tokenEnv":"TEAM_RAG_TOKEN","enabled":true}]
```

Credentials come only from the named server environment variable. They are not copied to memory, exports or the dashboard. Endpoints cannot contain credentials, query strings or fragments. Redirects are refused; timeout is four seconds and response size is bounded to 100 KB. Provider errors are reported as unavailable; no fabricated context is returned. No provider is enabled by default.

The adapter POSTs `{query, userId, projectId, limit:6}`. The provider returns:

```json
{"records":[{"id":"source-record","scope":"project","userId":"the-requested-user-id","projectId":"the-requested-project-id","text":"Retrieved evidence","createdAt":"2026-11-13T00:00:00Z","source":{"url":"https://source.example/document","title":"Document"}}]}
```

Every record must have matching user identity, exact project scope and source provenance. User-wide records use `scope:user` with no project ID. Mismatched or oversized responses are rejected. Returned evidence is labelled external, provider-attributed and retrieval-only; it has no authority to execute tools or modify requirements. Disabling memory also prevents this retrieval.

Another local client may consume AtMem via authenticated `POST /api/memory/context` with `{projectId,query}` and the existing local session Bearer token. It returns scoped records, responsible local user ID, project ID, status and the retrieval-only boundary. There is no browser-supplied owner override and no anonymous or cloud endpoint.
