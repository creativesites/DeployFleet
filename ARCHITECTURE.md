# Architecture

This is a short entry point, not the full document. The detailed, maintained architecture analysis lives in [`docs/architecture/`](docs/architecture/README.md) — read that for anything beyond a one-paragraph orientation.

## One-paragraph summary

DeployFleet forks DeployGuard (an Odoo 19 Community platform for security-workforce management) and rebuilds its operational core around transportation and logistics. The reusable machinery — payroll, HR, billing pipeline, notification engine, reporting shell, mobile API pattern, a cross-module event bus, and an AI provider-abstraction framework — is kept and renamed under a `deployfleet.*` namespace. The operational domain model is not a rename: it remodels from DeployGuard's `client → site → post → shift → roster → attendance` chain into `customer → shipment → route → dispatch → trip → delivery`, detailed in [docs/architecture/07-domain-model-erd.md](docs/architecture/07-domain-model-erd.md).

## Where to actually read

| Question | Doc |
|---|---|
| What happens to each DeployGuard module? | [docs/architecture/01-module-audit.md](docs/architecture/01-module-audit.md) |
| What's reusable, and at what level? | [docs/architecture/02-reuse-strategy.md](docs/architecture/02-reuse-strategy.md) |
| Naming conventions and technical debt to fix during the fork | [docs/architecture/03-refactoring-roadmap.md](docs/architecture/03-refactoring-roadmap.md) |
| The target module list and dependency graph | [docs/architecture/04-module-structure.md](docs/architecture/04-module-structure.md) — see also [MODULE_STRUCTURE.md](MODULE_STRUCTURE.md) |
| Build sequencing | [docs/architecture/05-implementation-roadmap.md](docs/architecture/05-implementation-roadmap.md) |
| Risks and open decisions | [docs/architecture/06-risks-and-recommendations.md](docs/architecture/06-risks-and-recommendations.md) |
| The entity model and key workflows | [docs/architecture/07-domain-model-erd.md](docs/architecture/07-domain-model-erd.md) — see also [DATABASE_DESIGN.md](DATABASE_DESIGN.md) |
| The AI architecture | [docs/architecture/08-ai-architecture.md](docs/architecture/08-ai-architecture.md) — see also [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) |

See [CLAUDE.md](CLAUDE.md) for conventions, deployment safety rules, and the development workflow every session should follow.
