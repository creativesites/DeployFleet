# 03 — Refactoring Roadmap

Two separate concerns live in this document: **(A)** the naming/model-identity strategy for the fork, because it's a prerequisite decision that touches every module, and **(B)** the technical debt inherited from DeployGuard, triaged into "fix during the fork" vs. "defer" vs. "drop, not applicable to trucking."

---

## A. Naming and model-identity strategy

### A.1 The collision DeployGuard didn't have to worry about

DeployGuard's custom models all live under a `security.*` name prefix (`security.roster.slot`, `security.payslip`, `security.vehicle`, …) with no risk of colliding with Odoo core, because Odoo core has no built-in "security guard" domain.

**DeployFleet does not have that luxury.** Odoo ships a native **Fleet** app with its own `fleet.vehicle`, `fleet.vehicle.model`, `fleet.vehicle.log.services`, `fleet.vehicle.odometer`, and `fleet.vehicle.log.fuel` models. If DeployFleet's custom modules define a new model literally named `fleet.vehicle`, that's not a stylistic clash — Odoo will refuse to load two independent modules both defining `fleet.vehicle` as a new model (as opposed to one `_inherit`-ing the other).

There are two architecturally sound paths, and this document recommends one but the choice should be confirmed before any code is written:

**Option 1 (recommended): Build on top of Odoo's native Fleet app.** `_inherit = 'fleet.vehicle'` and add trucking-specific fields (VIN, axle configuration, GVW rating, tyre position map) rather than reinventing a vehicle model. Odoo's Fleet app already gives us, for free: vehicle model/brand/category master data, fuel logs, odometer readings, service history, contract/cost tracking, and a maintained upstream UI. This is the "reuse everything generic" philosophy applied one layer deeper than the custom-module layer — DeployGuard's own `security_fleet` module partially reinvented what Odoo Fleet already provides (fuel logs, service logs), presumably because guard-transport shuttles were a minor feature and pulling in a whole extra Odoo app wasn't worth it. For DeployFleet, fleet management *is* the product, so the native app is worth depending on.

**Option 2: Standalone namespace, no dependency on Odoo Fleet.** Keep a self-contained model prefix (e.g., `dfleet.vehicle`) with zero dependency on Odoo's Fleet app, trading the free functionality above for full control and no coupling to an Odoo app whose roadmap we don't control.

**Recommendation:** Option 1, with the technical model prefix `dfleet.*` reserved for models that are *ours* and have no Odoo-core equivalent (trips, routes, dispatch, tyre lifecycle, job cards) — so `dfleet.trip`, `dfleet.route`, `dfleet.dispatch.slot`, `dfleet.tyre`, `dfleet.job.card` — while vehicle, fuel log, service log, and odometer records extend `fleet.*` core models via `_inherit`. This is flagged as an open decision in [06-risks-and-recommendations.md](06-risks-and-recommendations.md) because it changes the dependency graph and the shape of `fleet_vehicle_registry`/`fleet_fuel_management`/`fleet_workshop` — worth 30 minutes of discussion before module scaffolding starts.

### A.2 Model and module naming convention

| Layer | Convention | Example |
|---|---|---|
| Python package / addon folder name | `fleet_<domain>` (matches the source's `security_<domain>` convention, keeps continuity for anyone who worked on DeployGuard) | `fleet_operations`, `fleet_billing`, `fleet_mobile_api` |
| Odoo technical model name (net-new, no Odoo-core equivalent) | `dfleet.<entity>` | `dfleet.trip`, `dfleet.route`, `dfleet.dispatch.slot` |
| Odoo technical model name (extends Odoo core) | `_inherit` the core model, no new prefix | `_inherit = 'fleet.vehicle'`, `_inherit = 'hr.employee'` |
| Security group `xml_id` | `group_fleet_<role>` | `group_fleet_driver`, `group_fleet_dispatcher` |
| Module category | `Fleet Operations` (replaces `Security Operations`) | — |

### A.3 Why this is easier than it sounds — and where the real risk hides

Because DeployFleet is a **new repository with no live database to migrate**, there is no need for the in-place model-rename machinery Odoo normally requires (renaming a model in a *running* production database means data migration scripts, updating `ir.model.data` references, etc.). We are writing fresh modules against fresh model names from day one. The "refactor" in most of the audit table is therefore **redesign-and-rewrite against a clean schema**, not **rename-in-place** — which is the easier and safer version of this problem. Treat any instinct to mechanically search-and-replace `security.` → `dfleet.` across copied files as a trap: copying a `security.roster.slot` file and renaming it to `dfleet.trip.assignment` will carry over guard-shift field semantics (grade, post, certification) that don't belong on a trip-assignment record. Read the source model, understand *why* each field exists, and re-derive the field list for the new domain — don't rename-and-ship.

---

## B. Technical debt triage

Source: `KNOWN_ISSUES.md` in the DeployGuard repo, cross-checked against the actual codebase during this analysis.

### Fix during the fork (natural checkpoint — don't reproduce the bug in new code)

| Item | Why now, not later |
|---|---|
| Mobile controller field-name mismatches (e.g., a controller querying `batch_id` when the model field is `attendance_batch_id`) | We're rewriting every mobile controller against new models anyway (see [02-reuse-strategy.md](02-reuse-strategy.md) §5). There is no reason to introduce a fresh version of this class of bug when every query is being rewritten from scratch. Add a controller-level integration test per endpoint as it's written, not after. |
| Mobile role detection via username/name heuristics instead of actual Odoo groups | Same logic — `src/api/auth.ts` is being touched anyway for the new role set (driver/dispatcher/fleet-manager/owner). Fetch groups from a `/me` endpoint from the start. |
| `security_payroll_core` hard-depending on `security_l10n_na` even though it's supposed to be the country-neutral engine | This is the single most important debt item for DeployFleet specifically, because the product roadmap is explicitly multi-country ("local Zambia trucking, then regional logistics operators"). Launching with the same coupling bug means every future country pack silently depends on Zambia's pack loading first. Fix: `fleet_payroll_core` depends only on `fleet_base`/`hr`; country packs (`fleet_l10n_zm`, `fleet_l10n_na`, future packs) each depend on `fleet_payroll_core` independently and register their rule sets via data, not via a manifest dependency chain between country packs. |
| No CI, no linters, no mobile lockfile | Trivial to set up correctly on a fresh repo, expensive to retrofit later. Set up `ruff`/`pylint-odoo` + ESLint + a GitHub Actions workflow (Odoo `--test-enable` + mobile typecheck) as part of repo scaffolding, before the first business-logic module lands. Commit `mobile/package-lock.json` from the first commit that touches `mobile/`. |
| Root-level scratch files (`eq.xml`, `fl.xml` in the source repo) | Don't copy them. Not a fix, just a "don't carry forward." |
| Equipment module manifest metadata bugs (wrong author field, etc.) | Free to fix while writing fresh manifests. |

### Defer, but track explicitly (don't silently drop)

| Item | Recommended phase |
|---|---|
| Saturday/night premium multipliers exist on the rule set model but aren't applied in the compute step | Carries over as-is into `fleet_payroll_core` — fix when Zambia payroll goes to UAT, same timeline it would have had in DeployGuard. Not blocking for Phase 1–2. |
| Midnight/holiday shift split (a trip or shift spanning a boundary should split into two premium categories) | Same — relevant to driver payroll, not to the fleet/dispatch domain work happening first. Track for the payroll-hardening phase. |
| Accounting/GL bridge completeness (`account.move` sync) | `fleet_billing_account` bridge module already exists as a pattern; harden once `fleet_billing` itself is stable. Not a Phase 1–2 blocker. |
| Bank statement import / reconciliation automation | Backlog item in the source too — no reason to pull it forward. |
| Amount-in-words invoice text (currently simplified) | Cosmetic; fix opportunistically. |
| No auto-roster/auto-dispatch optimizer, rest/consecutive-day rules not yet enforced as hard constraints | These become *more* important for DeployFleet (driver hours-of-service compliance is a bigger regulatory and safety concern in trucking than shift rest in guarding) but are still correctly sequenced after the core dispatch object model exists. Track as a named Phase 3 item, not a Phase 1 nice-to-have — see [05-implementation-roadmap.md](05-implementation-roadmap.md). |
| Test coverage gaps (mobile HttpCase tests, operations model tests) | Set the coverage *bar* from day one on new modules (this is cheap); backfilling the exact gaps the source had is moot since the source modules aren't being copied verbatim. |
| Offline mobile queue | Genuinely hard (sync protocol, conflict resolution) — correctly deferred in the source, correctly deferred here. Flag as a Phase 4+ item, not forgotten. |
| FCM/Expo push notifications not wired end-to-end | Wire up as part of `fleet_mobile_bridge` — worth doing early since dispatch alerts (new trip assigned, breakdown reported) are more time-critical for a dispatcher than a document-expiry notice was for security ops. Bring forward relative to the source's priority, don't defer. |

### Drop — not applicable to trucking, don't spend time deciding what to do with it

| Item | Why it's simply gone |
|---|---|
| Grade `sequence`-field-as-implicit-rank ("higher sequence = lower grade, undocumented") | The whole grade/certification model is being redesigned for license classes and endorsements; this specific implicit-ordering bug has no analog to carry forward or fix — it disappears with the model it lived on. |
| Guard-specific certification/disqualification field semantics | Redesigned wholesale as driver qualification/license-class/medical-fitness fields — see [01-module-audit.md](01-module-audit.md), `security_base`. |
| `security_dogforce_data`, `security_dogforce_migration`, both demo-data modules | Not technical debt to fix — content to not fork at all. See [06-risks-and-recommendations.md](06-risks-and-recommendations.md). |

---

## C. Sequencing implication

Because `fleet_base` (identity) and the naming/model-identity decision in §A sit underneath every other module, **no other module work should start until those two are settled.** This is reflected as Phase 0 in [05-implementation-roadmap.md](05-implementation-roadmap.md).
