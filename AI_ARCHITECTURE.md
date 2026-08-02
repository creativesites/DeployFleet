# AI Architecture

Short entry point — the maintained, detailed version is [docs/architecture/08-ai-architecture.md](docs/architecture/08-ai-architecture.md). Read that before writing any AI-related code.

## Governing principle

> DeployFleet is an operations platform where AI assists humans, automates repetitive work, detects problems early, and provides intelligence — but every AI capability is modular, permission-controlled, measurable, and optional.

## Summary

- **Provider abstraction**: `deployfleet_ai_core` routes every AI call through one interface. No business module talks to a provider directly. Providers: DeepSeek (default), OpenAI, Claude — with a cheap/reasoning model tier selectable per feature.
- **Cost control**: response + context caching, per-call usage/cost logging (`deployfleet.ai.usage`), and per-company token/cost budgets.
- **A verified starting point, not a from-scratch build**: a field-level check of DeployGuard's existing AI engine found the provider router, per-feature toggles, caching, and usage logging already ~70% built. What's genuinely new: granular per-role AI permissions and the entire action-approval pipeline.
- **Six agents, one engine**: Fleet Analyst, Dispatch, Maintenance, Finance, Compliance, Customer — implemented as configuration (system prompt, allowed actions, data scope) inside `deployfleet_ai_agents`, not six separate modules.
- **Any AI-initiated write is gated**, no exceptions in v1: suggestion → permission check → human approval → execute → audit log. This is a hard requirement, verified in code review — see [docs/architecture/06-risks-and-recommendations.md](docs/architecture/06-risks-and-recommendations.md) risk #7.
- **Data governance is a per-feature setting, not a global assumption**: payroll/financial features need the ability to opt out of external AI providers independent of the rest of the platform's AI features. See risk #8 in the same doc.

## Module split

`deployfleet_ai_core` (router, config, cache, usage log, chat) · `deployfleet_ai_permissions` (new: per-role scoping, budgets) · `deployfleet_ai_actions` (new: the approval pipeline) · `deployfleet_ai_agents` (the six-agent catalog, as data) · `deployfleet_ai_whatsapp` (WhatsApp bridge, action-capable via `deployfleet_ai_actions`).

## Roadmap placement

The AI *foundation* builds in Phase 0 (cheap, since most of it already exists in the source — same logic that promoted the event bus that early). Read-only agent analysis lands in Phase 2–3 as real operational data starts flowing. The action-approval pipeline is Phase 4. Predictive/advanced AI features (forecasting, not just describing) are Phase 5. Full mapping: [docs/architecture/08-ai-architecture.md](docs/architecture/08-ai-architecture.md) §11.
