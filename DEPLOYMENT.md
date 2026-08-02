# Deployment

**Current status: no DeployFleet deployment work has happened yet.** This document records the rules that govern deployment once it starts, and the pre-flight steps required before the first one — it is not a record of anything already done to the demo server.

## Demo server

| | |
|---|---|
| Host | `199.192.23.46` |
| User | `root` |
| Credentials | **Not stored in this repository, and never should be.** See "Credential handling" below. |

## The hard rule: this server already runs other people's production systems

The demo server hosts, at minimum:

1. An **existing production Odoo instance**.
2. An **existing staging Odoo instance**.

Both predate DeployFleet and must never be disrupted by DeployFleet's deployment. This is not a "try not to" — treat any action that could plausibly affect either as requiring explicit confirmation before running it, the same bar this project applies to any destructive or hard-to-reverse action.

**DeployFleet gets, unconditionally:**

- Its own PostgreSQL database — never the existing production or staging database, never a shared database with a different schema prefix.
- Its own filestore.
- Its own Docker Compose stack, isolated from whatever compose project(s) the existing instances run under.
- Its own port allocation, confirmed not to collide with ports already in use.

## Required pre-flight inventory — has not been done yet

Before provisioning anything for DeployFleet on this server, inventory what's already there:

- `docker ps -a` — running and stopped containers, their names, and which compose project (if any) they belong to.
- Active listening ports (`ss -tlnp` or equivalent) — confirm DeployFleet's chosen ports are actually free.
- Existing PostgreSQL databases (`psql -l` inside whatever Postgres container/instance is running) — confirm naming so DeployFleet's database name can't collide.
- Existing Docker volumes (`docker volume ls`) — same reasoning, for filestores.
- Reverse proxy configuration (nginx/Traefik/Caddy — whichever is in use) — confirm how the existing instances are routed, so DeployFleet's own routing addition doesn't shadow or conflict with an existing `server_name`/host rule.

Record the results of this inventory in this file (or a linked doc) once it's done, so the next session doesn't have to re-derive it from scratch.

## Credential handling

- **Never commit a credential to this repository** — not in this file, not in a `.env.example` with a real value left in by mistake, not in a deployment script "temporarily." Use environment variables, a secrets manager, or SSH-key-based auth instead of passwords wherever the tooling allows it.
- If a credential is ever pasted into a chat, an issue, or a doc by accident, the right response is to treat it as compromised and get it rotated — not just to delete the message or file it was pasted into. Chat and issue history can persist and be searched long after the message is "deleted" from view.
- This file intentionally does not restate the server's password, even though it has been shared in this project's chat history at least once. Treat that exposure as a reason to rotate it, not as a reference to copy from later.

## Deployment architecture (once Phase 0–1 implementation exists)

```
Demo server (199.192.23.46)
├── Existing production Odoo  ── untouched, different compose project
├── Existing staging Odoo     ── untouched, different compose project
└── DeployFleet stack (new)
    ├── postgres (dedicated container, dedicated volume, dedicated DB name)
    ├── odoo (dedicated container, dedicated port, mounts DeployFleet's custom_addons)
    └── reverse-proxy entry (added alongside existing entries, never replacing one)
```

Mirror the source DeployGuard project's local dev pattern (`deploy/docker-compose.yml`, config generated from `.env` by a start script) for consistency, adjusted for whatever Odoo version DeployFleet targets — see the open Odoo-edition question in [docs/architecture/06-risks-and-recommendations.md](docs/architecture/06-risks-and-recommendations.md).

## CI/CD

Not yet configured — scoped as a Phase 0 task in [docs/architecture/05-implementation-roadmap.md](docs/architecture/05-implementation-roadmap.md): GitHub Actions running Odoo's `--test-enable` test suite and a mobile typecheck on every PR, linting (`ruff`/`pylint-odoo`, ESLint) gating merges. Manual promotion to staging, then production after UAT, matching the source project's documented approach until there's a reason to do otherwise.

## Rollback

Not yet designed in detail — track this as part of Phase 0/1 deployment scaffolding, not something to improvise during the first real incident. At minimum: code rollback via git, database restore from a scheduled dump (see `deployfleet_backup`, [docs/architecture/01-module-audit.md](docs/architecture/01-module-audit.md)), and a documented "how do we know which of the three stacks on this server an alert is about" runbook, given three Odoo instances will share one physical host.
