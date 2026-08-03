# CLAUDE.md — DeployFleet Operating Guide

This is the permanent operating guide for every development session on DeployFleet. Read it before touching code. It is a living document — update it whenever a convention, architecture decision, or workflow rule changes, in the same session that changes it.

**Current phase: Experience Architecture implementation.** All 43 backend modules (Phase 0–5 plus the demo-data module) are functionally complete, tested, and deployed. Frontend work now proceeds against [docs/architecture/16-experience-architecture.md](docs/architecture/16-experience-architecture.md) through [19-animation-guidelines.md](docs/architecture/19-animation-guidelines.md)'s phased rollout, starting with the shared `deployfleet_ui` design-system/component-library module (Phase A). The real trucking-operator domain-model validation flagged in [docs/architecture/06-risks-and-recommendations.md](docs/architecture/06-risks-and-recommendations.md) and [07-domain-model-erd.md](docs/architecture/07-domain-model-erd.md) remains open and should still happen — it is not a gate on frontend work, which builds on the domain model as it stands today.

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
| [16-experience-architecture.md](docs/architecture/16-experience-architecture.md) | The full UX/frontend strategy — gates all future frontend work the same way this doc gates AI work. Written after functional completion of all 43 modules; audits DeployFleet's current 100%-stock-Odoo UI, grounds DeployGuard OWL-pattern reuse in an actual source read, sets a deliberate Tesla/Stripe/Linear visual personality distinct from DeployGuard's military-ops register, and gives area-by-area redesign direction (Dispatch Board and the Copilot Console are the flagged top priorities) |
| [17-design-system.md](docs/architecture/17-design-system.md) | The token-level design system beneath doc 16 — color (incl. the AI-content violet convention, dark mode), spacing, typography, elevation/glass, iconography, accessibility |
| [18-component-library.md](docs/architecture/18-component-library.md) | The `deployfleet_ui` OWL component catalog — atoms, composites, layout shells, and the signature "wow" widget set, each with its concrete DeployFleet-model data source |
| [19-animation-guidelines.md](docs/architecture/19-animation-guidelines.md) | The motion system — timing/easing scale and a per-interaction spec table, so animation reads as one language, not five guesses |

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

**The authoritative elaboration of this section is the four-document Experience Architecture set: [16-experience-architecture.md](docs/architecture/16-experience-architecture.md) (strategy), [17-design-system.md](docs/architecture/17-design-system.md) (tokens), [18-component-library.md](docs/architecture/18-component-library.md) (the `deployfleet_ui` component catalog), and [19-animation-guidelines.md](docs/architecture/19-animation-guidelines.md) (motion)** — check any dashboard/board/workspace design or build against all four before starting, the same discipline §4 already requires against the AI architecture doc. The bullets below are the short-form summary; the real analysis (current-state audit, DeployGuard pattern-reuse grounding, per-area redesign direction, the design-system tokens, the component catalog, the animation spec, and a phased rollout recommendation) lives there.

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

**Done:** the Phase 1 architecture analysis (`docs/architecture/01` through `15`), this operating guide, the supporting root-level docs listed in §2, and formal sign-off resolving 7 of the 8 hard risks in [06-risks-and-recommendations.md](docs/architecture/06-risks-and-recommendations.md). **Phase 0** (`deployfleet_core`, `deployfleet_security`, `deployfleet_event_bus`, `deployfleet_ai_core`), **Phase 1 — Operational Foundation** (`deployfleet_driver`, `deployfleet_vehicle`, `deployfleet_customer`, `deployfleet_route`, `deployfleet_dispatch`, `deployfleet_trip`, `deployfleet_delivery`), **Phase 2 — Cost Control** (`deployfleet_freight_calculator`, `deployfleet_load_expense`, `deployfleet_driver_advance`, `deployfleet_fuel`, `deployfleet_parts`, `deployfleet_tyres`, `deployfleet_workshop`, `deployfleet_maintenance`, `deployfleet_assets`), **Phase 3 — Compliance** (`deployfleet_compliance`, `deployfleet_vehicle_compliance`, `deployfleet_dispatch_compliance`, `deployfleet_insurance`, `deployfleet_payroll`, `deployfleet_l10n_zm`, `deployfleet_leave`, `deployfleet_loans`, `deployfleet_driver_performance`), **Phase 4 — Customer Platform** (`deployfleet_billing`, `deployfleet_accounting`, `deployfleet_zra`, `deployfleet_client_reports`, `deployfleet_customer_portal`, `deployfleet_notifications`, `deployfleet_mobile_dispatcher`, `deployfleet_mobile_customer`, `deployfleet_mobile_push_bridge`, `deployfleet_ai_permissions`, `deployfleet_ai_actions`, `deployfleet_ai_whatsapp`), and **Phase 5 — Intelligence** (`deployfleet_ai_agents`: the six-agent catalog plus predictive maintenance, statistical fuel-anomaly detection, historically-weighted dispatch scoring, and financial forecasting) are all implemented, tested, lint-clean, and committed — 42 modules total, plus a 43rd demo/tooling module, `deployfleet_demo_zm`, a `post_init_hook`-driven full-system demo dataset for a fictional Zambian trucking company, "CreativeSites Logistics" — company/currency setup, depots, customers/contracts, vehicles (incl. one breakdown, one expired-insurance), drivers, routes, insurance/compliance documents, maintenance/workshop/parts/tyres/assets, fuel logs with a deliberate anomaly, shipments run through the full dispatch → trip → delivery → invoice pipeline (incl. one via the compliance-override path), HR extras (leave/advances/loans/performance/payslips), AI action requests across pipeline states, and pre-populated Phase 5 predictions — built via each model's normal `create()`/`action_*()` methods, never calling the AI provider router, leaving ZRA config untouched, and registering no push device tokens so install makes no outbound network calls.

Phase 4/5 notes worth carrying forward, not re-discovering later: `deployfleet_zra`'s endpoint paths/field names come from a community Postman collection, not ZRA's own spec PDF (which 503'd while building it) — verify against ZRA's actual sandbox before any real submission, and get someone who knows ZRA's VAT category rules to review the default VAT category code. `deployfleet_ai_whatsapp`'s webhook does not yet verify Meta's `X-Hub-Signature-256` signature — not hardened against spoofed requests until that's closed. `deployfleet_ai_agents`' predictive models use real closed-form statistics (linear regression, z-scores) calibrated on whatever seed/demo data exists, not the real pilot-customer history its own Phase 5 exit criteria call for — treat current outputs as illustrative, not validated. All three are flagged in their own module READMEs, not just here.

**A live demo is deployed and running** on the shared demo server at `http://199.192.23.46:4169/`, alongside — not disrupting — that server's pre-existing production and staging Odoo instances, per the isolated stack in [DEPLOYMENT.md](DEPLOYMENT.md). All 43 modules — Phase 0 through Phase 5 plus `deployfleet_demo_zm` — are installed on the demo database, with the full "CreativeSites Logistics" demo dataset generated. DeepSeek is configured as the active AI provider via the Odoo backend (`deployfleet.ai.config`), not via any file in this repository.

The demo server runs an Odoo 19 nightly snapshot (`19.0-20260723`), not a stable release — this has already caused several version-drift bugs during install (`res.groups.category_id` removed in favor of `privilege_id`; the base settings view's `div.settings` xpath anchor changed; `product.product`'s `invoice_policy` field turned out to belong to the `sale` module, not core `product`, which is unrelated to version drift but was caught the same way; `res.users.groups_id` renamed to `group_ids` and the corresponding `res.groups.users` renamed to `user_ids`). Pinning to a stable Odoo 19 release once one is cut remains an open recommendation, not yet decided. Also learned the hard way this session: a `<record id="base.user_admin">` in any non-`base` module's data file is silently skipped forever, since that xmlid's `noupdate="1"` is set by `base` itself — use a `<function>` call instead whenever a module needs to write to a record it doesn't own the xmlid for.

**Real, previously-undiscovered gap found while generating demo data, not just a demo issue:** no DeployFleet module ever provisions a chart of accounts for a company. A fresh company (no country fiscal localization installed — `deployfleet_l10n_zm` is payroll-tax rules only, not a CoA) has zero `account.account` records, so `deployfleet_accounting`'s `_create_account_move()` used to fail on literally the first invoice any company ever confirmed (`account_move_line_check_accountable_required_fields`, NULL `account_id`). Given a stopgap in `deployfleet_invoice.py`: `_create_account_move()` now lazily creates one dedicated income account and one dedicated receivable account (idempotent by code) and assigns them before posting, instead of requiring Odoo's full accounting-onboarding wizard to have run first. This unblocks first-invoice posting for any company, demo or real, but it does **not** resolve the actual chart-of-accounts/localization strategy question below — that's still open and shouldn't be treated as closed by this stopgap.

**Still genuinely open, and not to be silently closed just because implementation has progressed well past Phase 0:**

- Hard risk #5: the domain model in [07-domain-model-erd.md](docs/architecture/07-domain-model-erd.md) has still not been validated against a real trucking operator's actual dispatch workflow. Implementation has run ahead of this discovery pass — a known, explicitly-flagged gap, not a silently-dropped one.
- The remaining open questions in [06-risks-and-recommendations.md](docs/architecture/06-risks-and-recommendations.md): Odoo edition (Community vs. Enterprise — this also blocks a clean answer to [15-load-sheet-architecture.md](docs/architecture/15-load-sheet-architecture.md) §9's custom-fields question), confirmed launch-market scope, team size/timeline against the 5-phase roadmap, and the concrete default AI token/cost budget numbers for the MVP release.
- The root SSH password used to deploy the demo was pasted into this project's session history during setup — rotate it regardless of whether the deploy scripts ever actually reached the server with it.
- CI's `mobile-typecheck` job has been failing on every run since Phase 0 for reasons that don't trace to this repo's content (near-instant failures with no runner ever assigned, per GitHub's own job metadata) — flagged, not yet root-caused. The separate, definite `lint` job failure (pylint couldn't resolve `import odoo` with no ignored-modules configured) has been fixed and confirmed locally.

**Experience Architecture implementation has begun.** `deployfleet_ui` (module 44) is a new shared, dependency-free-of-business-logic OWL library — no business module should ever hand-roll a button, card, or badge again, per [18-component-library.md](docs/architecture/18-component-library.md)'s governance rule. This is Phase A / Slice 1 of doc 16 §11's rollout: the design-system tokens from [17-design-system.md](docs/architecture/17-design-system.md) as real SCSS custom properties (color incl. the AI-content violet convention and dark mode, spacing, typography, elevation/glass per Command/Workspace layer) and the motion tokens/keyframes from [19-animation-guidelines.md](docs/architecture/19-animation-guidelines.md), plus a first tranche of foundational OWL components (Button, Card, Avatar, StatusBadge, StatusPill, AiBadge) and one composite (MetricCard) — not doc 18's full catalog yet. A debug-only "UI Component Showcase" client action (`base.group_no_one`) renders every component and variant as a living reference.

**Important caveat, unlike every backend module before it:** this module's JS/OWL/SCSS has been verified for syntax validity only (XML well-formedness, genuine JS syntax checking via `node --check` against a `.mjs` copy — a plain `.js` copy silently no-ops the check when the file starts with an `import` statement, a real gotcha hit and worked around this session) and structural correctness against standard Odoo 17–19 OWL conventions. **None of it has been verified by actually rendering it in a running Odoo web client** — this development environment has no browser or live Odoo instance to load one in, unlike the Python modules, which were all validated by installing on the live demo server and reading the resulting log. The Component Showcase screen exists specifically so a human can do that check on first install. Expect this to be the first module in the project where the install log alone isn't sufficient sign-off — actually opening the showcase screen and looking at it matters here in a way it didn't for the backend-only modules.

**Proposed next step:** install `deployfleet_ui` on the demo server and open the Component Showcase screen (Settings → Technical must be enabled, i.e. debug mode on) to visually confirm the tokens and components render and behave as designed — report back anything that looks wrong so it can be fixed before Phase B (the Launcher, Domain Mega Menus, and Command Palette) builds on top of it. The real trucking-operator domain-model validation (hard risk #5) and the other open items below remain worth doing but are no longer the single next step now that frontend implementation is underway.
