# Running and deploying AtMem AI Architect yourself

## Local workstation — supported first path

Run `npm run local` after installing the Node and Python dependencies. Sign in through the desired official Claude, Codex, Copilot or Gemini client. Clients retain their own authentication. Model API keys can instead be entered into sidecar memory or provided through the environment. Do not share native credential directories or extract/copy account tokens into the application.

A frontend-only build is available with `npm run build`, then `npm run preview`. This serves the zero-key design/simulation UI. A static host alone cannot run local account adapters or the Python architect sidecar.

## Private development server or desktop packaging — next path

The architecture permits a desktop wrapper or a separately authenticated, self-hosted web frontend plus agent service. No vendor hosting service is required to develop or build it. This milestone does not yet include a production container or multi-user server configuration.

Before exposing a backend beyond loopback:

- Replace the local bearer bootstrap with authenticated user sessions and explicit tenant/workspace ownership.
- Isolate native account clients per operating-system user; never share one subscriber's login across customers. Verify provider terms for hosted/commercial usage. Prefer server API credentials with clear billing/usage policies for shared deployments.
- Put the application behind TLS and an authenticated reverse proxy; update the precise Host/Origin allowlists together.
- Use a proper secret store, per-user quotas, model limits, durable project storage and audit events.
- Separate model permissions from cloud-account permissions. The present sidecar has no infrastructure execution API.
- Choose a Pulumi state backend and provider credentials independently of AtMem AI Architect's own hosting. Add real resource implementations, reviewable previews, explicit approval and staging evidence before any update path.

Product information and training on atmem.ai are separate from this local application. Publishing those pages does not host its interactive frontend or agent service. Application hosting requires a separate reviewed integration; the existing website also retains its owner-review and validated-main publication process.
