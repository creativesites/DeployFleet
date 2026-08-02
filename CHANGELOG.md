# Changelog

## Phase 1 — Operational Foundation

Full design for the centerpiece module: [docs/architecture/09-dispatch-module-design.md](docs/architecture/09-dispatch-module-design.md), written before implementation, same discipline as the AI architecture in Phase 0.

**Added**, in dependency order:

- `deployfleet_driver` — driver profile on `hr.employee` (license class/number/expiry, endorsements, qualified vehicle types, experience, risk score). Deliberately skips the `deployfleet_hr` module from the original module structure doc — no content exists for it yet; see the module's README.
- `deployfleet_vehicle` — `deployfleet.vehicle` delegating Odoo's native `fleet.vehicle` via `_inherits`, per the resolved risk #2 decision. Operational `status`, `current_driver_id`, `vehicle_type_id`.
- `deployfleet_customer` — `deployfleet.contract` (optional on a shipment — spot loads have none) and `deployfleet.depot`.
- `deployfleet_route` — `deployfleet.route` and `deployfleet.route.stop`.
- `deployfleet_dispatch` — `deployfleet.shipment` and `deployfleet.dispatch.assignment`, with a weighted-heuristic scoring function (not a solver) that hard-disqualifies unavailable vehicles and vehicle-type mismatches, and requires an override reason to confirm a lower-scored candidate over a higher-scored one. Ships kanban-by-state views rather than a custom OWL drag-drop board — a deliberate Phase 1 scope call under real time pressure (a real company is about to use this), not an oversight; see the design doc §1/§5.
- `deployfleet_trip` — `deployfleet.trip`, created automatically via an event-bus subscription when a dispatch assignment is confirmed (not a direct module dependency, to keep the dependency graph one-way). Adds `current_trip_id` to `deployfleet.vehicle` via `_inherit`. `deployfleet.trip.shipment.line` — the shipment↔trip many-to-many join from the domain model, built from day one even though Phase 1's common case is one line per trip.
- `deployfleet_delivery` — `deployfleet.delivery`, proof of delivery keyed to (trip, shipment); creating one is the completion event (marks the shipment delivered, publishes `deployfleet.delivery.completed`).
- Also extended `deployfleet_core` with `deployfleet.vehicle.type` (shared master data — trailers/tankers/etc. — needed by both driver qualifications and vehicle records, so it lives in the foundation module rather than creating a spurious cross-dependency between driver and vehicle).

Every module ships a test suite; the dispatch and trip modules' tests specifically verify the scoring function's disqualification rules, the override-reason requirement, and the event-bus-driven trip creation.

**Deviations from `docs/architecture/04-module-structure.md`**, each documented in the affected module's README rather than silently diverging: `deployfleet_hr` skipped (no content yet), `deployfleet_route`'s dependency on `deployfleet_vehicle` dropped (nothing in the Phase 1 design needs it).

## Phase 0 — repo scaffolding and foundation modules (first implementation)

All 8 hard risks in [docs/architecture/06-risks-and-recommendations.md](docs/architecture/06-risks-and-recommendations.md) except #5 (real-world domain validation, still pending) were formally resolved and approved, unblocking implementation.

**Added:**

- Repo scaffolding: `.github/workflows/ci.yml` (Odoo `--test-enable` + ruff + pylint-odoo + a mobile-typecheck job that no-ops until `mobile/` exists), `pyproject.toml`/`.pylintrc` linter config, `deploy/docker-compose.yml`, `scripts/{docker-env,start,stop,run-tests}.sh`, `requirements.txt`, `.env.example`.
- `custom_addons/deployfleet_core` — module category, root app menu, `deployfleet.sequence.mixin` reference-code helper.
- `custom_addons/deployfleet_security` — role groups (`group_deployfleet_driver` → `dispatcher` → `manager` → `owner`, plus HR/Payroll Officer and System Auditor), `deployfleet.license`/`deployfleet.license.log` product entitlement model with a daily expiry-check cron.
- `custom_addons/deployfleet_event_bus` — `deployfleet.event.log` publish/dispatch model and `deployfleet.event.subscription` registry, resolving risk #4 (the source's hardcoded subscriber if-chain).
- `custom_addons/deployfleet_ai_core` — provider router (`deployfleet.ai.core.complete()`) with working DeepSeek/OpenAI (shared OpenAI-compatible adapter) and Claude adapters, Gemini/local reserved as not-yet-implemented; `deployfleet.ai.policy` (the per-company governance shape from risk #8); `deployfleet.ai.config`; `deployfleet.ai.feature` (data-driven toggles, not hardcoded booleans); split response/context cache; usage log + pre-call budget gate.
- Test suites for all four modules (unittest-style `TransactionCase`s), set as the coverage bar from the first module per [CLAUDE.md](CLAUDE.md) §9.

**Not yet done:** `deployfleet_ai_permissions`/`deployfleet_ai_actions` (Phase 4), and every operational module (driver, vehicle, dispatch, trip, ...) — Phase 1 onward per [docs/architecture/05-implementation-roadmap.md](docs/architecture/05-implementation-roadmap.md).

## Architecture planning — revision 3 (AI architecture)

- Added [docs/architecture/08-ai-architecture.md](docs/architecture/08-ai-architecture.md): provider abstraction (DeepSeek added as default alongside Claude/OpenAI/Gemini, cheap/reasoning model tiers), cost architecture (caching, usage tracking, budgets), a fixed-verb "Ask AI" UI pattern, a six-agent catalog, and a mandatory suggestion→permission-check→human-approval→execute→audit pipeline for any AI-initiated write.
- Verified, via a field-level re-check of `security_ai_engine`'s actual model code, that roughly 70% of the requested AI foundation (provider router, per-feature toggles, response caching, usage/cost logging) already exists in the DeployGuard source. Split the AI module accordingly: `deployfleet_ai_core` (verified-reusable) separated from `deployfleet_ai_permissions`/`deployfleet_ai_actions` (genuinely new).
- Updated [01-module-audit.md](docs/architecture/01-module-audit.md), [02-reuse-strategy.md](docs/architecture/02-reuse-strategy.md), [04-module-structure.md](docs/architecture/04-module-structure.md), and [05-implementation-roadmap.md](docs/architecture/05-implementation-roadmap.md) to reflect the AI module split and move the AI foundation to Phase 0.
- Added two hard risks to [06-risks-and-recommendations.md](docs/architecture/06-risks-and-recommendations.md): AI writes without human approval, and data-governance implications of routing business data through a third-party AI provider.

## Architecture planning — revision 2 (naming, event bus, domain model)

- Unified all module/model naming under the `deployfleet_*`/`deployfleet.*` namespace, replacing an earlier `fleet_*`/`dfleet.*` split, to avoid confusion with Odoo's native Fleet app.
- Resolved the vehicle-architecture question: `deployfleet.vehicle` uses delegation inheritance (`_inherits`) over Odoo's native `fleet.vehicle`.
- Discovered, via re-reading `security_base`'s actual model code, a working event bus (`security.event.log`) already present in the DeployGuard source. Promoted it to a first-class `deployfleet_event_bus` foundation module and flagged its one real defect (a hardcoded subscriber list) to fix during the port.
- Added Shipment/Load as a first-class entity between Customer and Trip.
- Regrouped modules: driver split from core identity into its own module; "discipline" reframed as `deployfleet_driver_performance`; equipment split three ways (parts/tyres/assets); mobile split three ways by role (driver/dispatcher/customer).
- Replaced an install-profile framing with a focused MVP-12 first release.
- Restructured the roadmap into 5 phases (Operational Foundation → Cost Control → Compliance → Customer Platform → Intelligence).
- Added [docs/architecture/07-domain-model-erd.md](docs/architecture/07-domain-model-erd.md): entities, relationships, and key workflows, with explicit notes on unvalidated judgment calls (spot loads, backhauls, owner-operator vehicles, consolidated cargo).

## Architecture planning — revision 1 (initial fork analysis)

- Analyzed the DeployGuard source (`creativesites/DogFrce-Security-Services-Custom-Odoo-Modules`, 45 custom modules) and produced the initial Phase 1 deliverable set: module audit, reuse strategy, refactoring roadmap, proposed module structure, phased implementation roadmap, and risks/recommendations.
- Flagged `security_dogforce_data` (71,419 lines of a real client's production data) as a hard exclusion — never to be forked in any form.

## Repository scaffolding

- Added [CLAUDE.md](CLAUDE.md) as the permanent operating guide: architecture pointers, naming conventions, AI architecture summary, UI/UX standards, mobile app structure, deployment safety rules, git commit standards, and the required development workflow.
- Added root-level entry-point docs (`ARCHITECTURE.md`, `MODULE_STRUCTURE.md`, `AI_ARCHITECTURE.md`, `DATABASE_DESIGN.md`, `MOBILE_ARCHITECTURE.md`, `DEPLOYMENT.md`) pointing into the detailed `docs/architecture/` analysis, plus this changelog.
