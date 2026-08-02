# CLAUDE.md — DeployFleet Operating Guide

This is the permanent operating guide for every development session on DeployFleet. Read it before touching code. It is a living document — update it whenever a convention, architecture decision, or workflow rule changes, in the same session that changes it.

**Current phase: architecture planning, not implementation.** No Odoo module code exists in this repository yet. Do not begin mass implementation until the open architectural questions in [docs/architecture/06-risks-and-recommendations.md](docs/architecture/06-risks-and-recommendations.md) are answered and the domain model in [docs/architecture/07-domain-model-erd.md](docs/architecture/07-domain-model-erd.md) has ideally been checked against a real trucking company's workflow.

---

## 1. What DeployFleet is

DeployFleet is an AI-powered logistics operating system for transportation and logistics companies, built by forking and transforming DeployGuard (`creativesites/DogFrce-Security-Services-Custom-Odoo-Modules`), a mature Odoo 19 Community platform originally built for private security companies. Initial market: local trucking companies in Zambia, expanding to regional Southern African logistics operators.

**This is not a generic ERP customization.** It is a commercial, multi-tenant-capable product with its own module namespace, its own AI architecture, its own mobile apps, and its own marketing site — DeployGuard is the donor codebase, not a dependency DeployFleet stays coupled to.

### Governing philosophy

> Reuse everything that is generic. Refactor everything that is industry-specific. Remove only what cannot reasonably be reused.

Concretely:

- **Reuse as-is or with light rework:** authentication, Odoo ACL/security-group patterns, workflow/state-machine conventions, the notification engine, reporting/dashboard shells, the mobile REST API pattern, the AI provider-abstraction framework, billing pipeline machinery, payroll/localization engine, documentation tooling, enterprise UI conventions.
- **Redesign the domain vocabulary, not just rename it:** guard → driver, post/site → depot/terminal, shift → trip, roster → dispatch, patrol → route, security incident → breakdown/driver-performance incident. See [docs/architecture/01-module-audit.md](docs/architecture/01-module-audit.md) for the full module-by-module classification and [docs/architecture/07-domain-model-erd.md](docs/architecture/07-domain-model-erd.md) for why this is a genuine remodel (`customer → shipment → route → dispatch → trip → delivery`), not a find-and-replace.
- **Never fork:** `security_dogforce_data` or anything containing DogForce's real production/client data. See [docs/architecture/06-risks-and-recommendations.md](docs/architecture/06-risks-and-recommendations.md) risk #1 — this is a hard rule, not a style preference.

---

## 2. Architecture documentation — read before writing code

The full Phase 1 architecture analysis lives in `docs/architecture/`, indexed at [docs/architecture/README.md](docs/architecture/README.md). It is the source of truth; this file organizes and summarizes it, it does not replace it.

| Doc | Covers |
|---|---|
| [01-module-audit.md](docs/architecture/01-module-audit.md) | Every DeployGuard module, classified keep/rename/refactor/split/remove |
| [02-reuse-strategy.md](docs/architecture/02-reuse-strategy.md) | Reusable business logic (incl. the event bus), UI, security groups, reports, APIs, mobile code |
| [03-refactoring-roadmap.md](docs/architecture/03-refactoring-roadmap.md) | Naming/model-identity strategy (the `deployfleet.*` namespace, vehicle delegation pattern) and technical debt triage |
| [04-module-structure.md](docs/architecture/04-module-structure.md) | The ~50-module target structure, dependency graph, MVP-12 first release |
| [05-implementation-roadmap.md](docs/architecture/05-implementation-roadmap.md) | The 5-phase build sequence (Operational Foundation → Cost Control → Compliance → Customer Platform → Intelligence), Phase 0 prerequisites |
| [06-risks-and-recommendations.md](docs/architecture/06-risks-and-recommendations.md) | Hard risks, moderate risks, open questions requiring explicit sign-off |
| [07-domain-model-erd.md](docs/architecture/07-domain-model-erd.md) | Entity model, relationships, key workflows — the schema Phase 1 builds against |
| [08-ai-architecture.md](docs/architecture/08-ai-architecture.md) | AI provider strategy, cost/permission architecture, agent catalog, mandatory action-approval pipeline |

Root-level summary docs (`ARCHITECTURE.md`, `MODULE_STRUCTURE.md`, `AI_ARCHITECTURE.md`, `DATABASE_DESIGN.md`, `MOBILE_ARCHITECTURE.md`, `DEPLOYMENT.md`, `CHANGELOG.md`) exist as short entry points that point into the detailed docs above — keep them short; put real analysis in `docs/architecture/`, not duplicated at root.

**Before making any change that touches module structure, naming, or the domain model, check whether it's already decided in these docs.** If it contradicts something decided there, raise it explicitly rather than silently diverging — these documents are the record of decisions already made, including *why*, and silent drift between them and the code is exactly the kind of debt this project is trying not to inherit from DeployGuard.

---

## 3. Naming conventions (binding, not a suggestion)

| Layer | Convention | Example |
|---|---|---|
| Python package / addon folder | `deployfleet_<domain>` | `deployfleet_dispatch`, `deployfleet_ai_core` |
| Odoo technical model name (net-new) | `deployfleet.<entity>` | `deployfleet.trip`, `deployfleet.shipment` |
| Odoo technical model name (delegates Odoo core, e.g. vehicle) | `deployfleet.<entity>` with `_inherits` | `deployfleet.vehicle` (`_inherits` `fleet.vehicle`) |
| Odoo technical model name (classical extension, e.g. employee) | `_inherit` the core model directly | `_inherit = "hr.employee"` for driver fields |
| Security group `xml_id` | `group_deployfleet_<role>` | `group_deployfleet_driver`, `group_deployfleet_dispatcher` |

**Never use a bare `fleet_` or `fleet.` prefix for anything DeployFleet owns.** Odoo ships a native Fleet app with `fleet.vehicle` and related models — see [03-refactoring-roadmap.md](docs/architecture/03-refactoring-roadmap.md) §A. `deployfleet.vehicle` uses delegation inheritance (`_inherits`) over `fleet.vehicle`, not a standalone reinvention and not a plain field-bolt-on `_inherit` — this is a resolved decision, not an open one; don't re-litigate it per module.

---

## 4. AI architecture — the short version

Full design in [08-ai-architecture.md](docs/architecture/08-ai-architecture.md). The governing principle, binding on every AI feature:

> DeployFleet is an operations platform where AI assists humans, automates repetitive work, detects problems early, and provides intelligence — but every AI capability is modular, permission-controlled, measurable, and optional.

Non-negotiable rules, not aspirations:

- **Every AI capability is independently switchable** — global on/off, plus per-agent/per-feature toggles. No AI feature ships without a way to turn it off.
- **No business module talks to an AI provider directly.** Every call goes through `deployfleet_ai_core`'s router. Provider list: DeepSeek (default), OpenAI, Claude, with a cheap/reasoning model tier per feature. Adding or swapping a provider must never require touching a business module.
- **Any AI-initiated write is gated**: suggestion → permission check → human approval → execute → audit log. There is no "auto-execute" path in v1. This is flagged as hard risk #7 in [06-risks-and-recommendations.md](docs/architecture/06-risks-and-recommendations.md) — verify it in code review, don't just trust the design doc.
- **Every AI call is logged and cost-tracked** (`deployfleet.ai.usage`) — tokens, cost, cache hits, per company. Don't ship a feature that calls a provider without this.
- **Data-sensitivity matters**: payroll/financial data needs a per-feature opt-out from external AI providers, not just a global switch — see [06-risks-and-recommendations.md](docs/architecture/06-risks-and-recommendations.md) risk #8.

Before writing new AI code, check [08-ai-architecture.md](docs/architecture/08-ai-architecture.md) §0 — a surprising amount of this (provider routing, caching, per-feature toggles, usage logging) is already ~70% built in the DeployGuard source (`security_ai_engine`) and needs porting/extending, not building from zero.

---

## 5. UI/UX standards

- **Mobile-first.** Primary users are drivers, dispatchers, and fleet managers/supervisors working from phones and tablets, not desks. Design and test for phone and tablet viewports first, desktop second.
- **Modern glassmorphic, enterprise-clean aesthetic — not default Odoo chrome.** Avoid shipping stock Odoo list/form views where a purpose-built interface materially improves the workflow (dispatch board, vehicle cards, trip timelines, analytics widgets).
- **OWL components are the default for anything user-facing and non-trivial.** Prioritize custom OWL components for dashboards, the dispatch board, vehicle/trip cards, AI assistant panels, analytics widgets, notifications, and mobile-adjacent web workflows. Reach for standard Odoo views for genuinely standard CRUD screens (config settings, simple master-data lists) where a custom interface wouldn't add value — don't rebuild everything in OWL reflexively; use judgment consistent with "avoid excessive standard Odoo views where a custom OWL interface provides a better experience," not "never use a standard view."

### Mobile applications — three, not one

Per [04-module-structure.md](docs/architecture/04-module-structure.md), mobile splits by role rather than staying one app with three logins:

| App | Primary users | Core workflows |
|---|---|---|
| Driver | Drivers | Assigned trips, navigation, pre/post-trip inspections, proof of delivery, breakdown reporting, document access, dispatcher communication |
| Dispatcher | Dispatchers, fleet managers | Live operations view, trip monitoring, alerts, approvals |
| Customer | Shippers/customers | Shipment tracking, delivery status, documents |

Full detail: [MOBILE_ARCHITECTURE.md](MOBILE_ARCHITECTURE.md).

### Marketing website — separate from Odoo entirely

DeployFleet's marketing site is **not** an Odoo module and does not live in this repository's Odoo addon tree. Stack: **Next.js, deployed on Vercel.** Scope: SaaS landing page, product/feature pages, documentation, demo-request and pricing/onboarding flows. Treat it as an independent project with its own repo or a clearly separated top-level directory — never let it become a dependency of the Odoo backend or vice versa.

---

## 6. Deployment safety rules

Full detail: [DEPLOYMENT.md](DEPLOYMENT.md). The short version, because getting this wrong is a production incident on someone else's live system:

- A demo server exists and **already hosts a live production Odoo instance and a staging instance that must never be disrupted.** DeployFleet gets its own database, its own filestore, its own Docker stack, and its own port allocation — full stop.
- **Before any deployment action against that server**, inventory what's already running: containers, active ports, databases, volumes, reverse-proxy config. This inventory has not been done yet as of this writing — it's a required first step of actual deployment work, not something to skip because "it's probably fine."
- **Never commit credentials, ever, to any file in this repository** — not in CLAUDE.md, not in a `.env.example` with a real value slipped in, not in a script "just for now." If a credential is ever pasted into a chat or a doc by mistake, treat it as compromised and get it rotated — don't just delete the file and move on.

---

## 7. Git commit standards

Conventional-commits style, required for every commit:

```
type(scope): description
```

Examples: `feat(dispatch): add trip assignment workflow`, `feat(ai): add DeepSeek provider adapter`, `refactor(vehicle): redesign vehicle lifecycle model`, `docs(architecture): update module structure`, `fix(mobile): resolve offline sync issue`.

**Never** commit with messages like `update`, `changes`, `fix stuff`, `testing`. If you can't summarize the change in a `type(scope): description` line, the change is probably too large or too unfocused for one commit.

---

## 8. Development workflow — every session

1. Read this file (`CLAUDE.md`) end to end if it's been more than a few sessions since the last read.
2. Review `docs/architecture/` for anything relevant to the task at hand — don't assume you remember the current decisions.
3. Check `git status` and recent log before making changes.
4. Understand the existing module(s) you're touching before extending them.
5. Make minimal, focused changes — this project explicitly avoids "while I'm in here" scope creep (see the source DeployGuard's own guidance against unnecessary rewrites, which DeployFleet inherits as a value, not just a codebase).
6. Update documentation in the same session as the code change it describes, not "later."
7. Run tests before considering a change done.
8. Commit with a conventional-commits message. Clean `git status` at session end — no dangling untracked files that should have been committed or ignored.

---

## 9. Quality bar

DeployFleet is a commercial SaaS product, not a one-off customer customization. Every module should be held to:

- Clean, maintainable architecture — the module boundaries in [04-module-structure.md](docs/architecture/04-module-structure.md) exist to keep this true, not just to look tidy on a diagram.
- Multi-company and multi-country support as a design constraint from the start, not retrofitted — see the payroll/country-pack decoupling fix in [03-refactoring-roadmap.md](docs/architecture/03-refactoring-roadmap.md), which exists specifically because the source codebase got this wrong once already.
- Secure, auditable permissions — both Odoo's own ACL/record-rule model and, where AI is involved, the AI-specific permission layer in [08-ai-architecture.md](docs/architecture/08-ai-architecture.md) §9.
- Documented APIs (mobile REST endpoints, AI action contracts).
- Automated tests — set the coverage bar from the first module, don't defer it the way the source codebase's `KNOWN_ISSUES.md` shows DeployGuard did for mobile controller tests.
- Production deployment readiness — CI green, no hardcoded credentials, no dependence on manual server-side steps that aren't documented in `DEPLOYMENT.md`.

---

## 10. Current status and next step

**Done:** the Phase 1 architecture analysis (`docs/architecture/01` through `08`), this operating guide, the supporting root-level docs listed in §2, and formal sign-off resolving 7 of the 8 hard risks in [06-risks-and-recommendations.md](docs/architecture/06-risks-and-recommendations.md) (see that doc's "Hard risks" section — each now carries a binding decision, not just a recommendation). **Phase 0 implementation is in progress**: repo/CI scaffolding plus the `deployfleet_core`, `deployfleet_security`, `deployfleet_event_bus`, and `deployfleet_ai_core` foundation modules, built against those resolved decisions.

**Still genuinely open, and not to be silently closed just because implementation has started:**

- Hard risk #5: the domain model in [07-domain-model-erd.md](docs/architecture/07-domain-model-erd.md) has not yet been validated against a real trucking operator's actual dispatch workflow. Implementation should not get far ahead of this — see the discovery requirements in that risk entry.
- The remaining open questions in [06-risks-and-recommendations.md](docs/architecture/06-risks-and-recommendations.md): Odoo edition (Community vs. Enterprise), confirmed launch-market scope, team size/timeline against the 5-phase roadmap, and the concrete default AI token/cost budget numbers for the MVP release.
- A pre-flight inventory of the demo server (`199.192.23.46`) — containers, ports, databases, volumes, reverse proxy — has not been performed. Do this before provisioning DeployFleet's own Docker stack there, not as an afterthought. See [DEPLOYMENT.md](DEPLOYMENT.md).

**Proposed next step after Phase 0 lands:** Phase 1 (Operational Foundation) from [05-implementation-roadmap.md](docs/architecture/05-implementation-roadmap.md) — `deployfleet_driver`, `deployfleet_vehicle`, `deployfleet_customer`, `deployfleet_route`, `deployfleet_dispatch`, `deployfleet_trip`, `deployfleet_delivery` — ideally not started until hard risk #5's discovery pass has at least begun.
