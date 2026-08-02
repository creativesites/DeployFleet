# 03 — Refactoring Roadmap

*Revision 2 — resolves the vehicle-architecture decision (delegation inheritance, not plain `_inherit`) per architecture review, unifies all naming under a single `deployfleet.*` prefix (dropping the earlier `dfleet.*`/`fleet_*` split), and adds the event-bus subscriber-registry fix identified once the existing bus was found (see [02-reuse-strategy.md](02-reuse-strategy.md) §0).*

Two separate concerns live in this document: **(A)** the naming/model-identity strategy for the fork, because it's a prerequisite decision that touches every module, and **(B)** the technical debt inherited from DeployGuard, triaged into "fix during the fork" vs. "defer" vs. "drop, not applicable to trucking."

---

## A. Naming and model-identity strategy

### A.1 The collision DeployGuard didn't have to worry about

DeployGuard's custom models all live under a `security.*` name prefix (`security.roster.slot`, `security.payslip`, `security.vehicle`, …) with no risk of colliding with Odoo core, because Odoo core has no built-in "security guard" domain.

**DeployFleet does not have that luxury.** Odoo ships a native **Fleet** app with its own `fleet.vehicle`, `fleet.vehicle.model`, `fleet.vehicle.log.services`, `fleet.vehicle.odometer`, and `fleet.vehicle.log.fuel` models. Reusing the bare word "fleet" as DeployFleet's own model/module namespace reads as if it *were* the native Odoo Fleet app, which is confusing for anyone maintaining the codebase later, on top of the literal model-name collision risk this document flagged in v1.

**Resolved decision (per architecture review): extend Odoo's native Fleet app, and reserve the `deployfleet.*` name prefix for everything DeployFleet owns.**

### A.2 The vehicle pattern: delegation inheritance, not plain field-bolt-on

v1 of this document recommended plain `_inherit = 'fleet.vehicle'` to add trucking-specific fields directly onto the core model. Architecture review proposed a cleaner variant, and this document now adopts it: a **companion model using Odoo's delegation inheritance (`_inherits`)**, not classical inheritance.

```python
class DeployfleetVehicle(models.Model):
    _name = "deployfleet.vehicle"
    _inherits = {"fleet.vehicle": "fleet_vehicle_id"}
    _description = "DeployFleet Vehicle Operational Profile"

    fleet_vehicle_id = fields.Many2one(
        "fleet.vehicle", required=True, ondelete="cascade",
        help="The underlying Odoo Fleet vehicle record — model, brand, VIN, "
             "license plate, and Fleet app's own fuel/service/odometer logs live here.",
    )
    status = fields.Selection(
        [("available", "Available"), ("assigned", "Assigned"),
         ("maintenance", "Maintenance"), ("breakdown", "Breakdown"), ("retired", "Retired")],
    )
    current_driver_id = fields.Many2one("deployfleet.driver")
    current_trip_id = fields.Many2one("deployfleet.trip")
    # compliance / maintenance-due fields are computed from related models,
    # not stored here — see 07-domain-model-erd.md
```

Why delegation instead of classical `_inherit`:

- **Every other DeployFleet module references `deployfleet.vehicle`, never `fleet.vehicle` directly.** Trips, dispatch, compliance documents, and the AI engine all point at the DeployFleet-owned record. `fleet.vehicle`'s own fields (make, model, VIN, license plate, and its native fuel/service/odometer logs) stay reachable through Odoo's automatic field delegation (`my_vehicle.license_plate` just works) without DeployFleet's models needing to know or care that they're delegated.
- **Upgrade safety.** If Odoo changes `fleet.vehicle` in a future core release, DeployFleet's own model (`deployfleet.vehicle`) isn't the thing that changed shape — only the delegation target did. Classical `_inherit` welds trucking-specific fields directly onto the core table; delegation keeps them in a table DeployFleet owns outright.
- **Matches the layered mental model from the review almost exactly**: Odoo core (`fleet.vehicle`: VIN, plate, model) sits underneath a DeployFleet operational layer (`deployfleet.vehicle`: status, current driver, current trip, compliance/maintenance rollups) — the two are joined, not merged.

The same pattern applies to `deployfleet.driver` over `hr.employee`, using classical `_inherit` there instead (an employee genuinely *is* one record with driver fields added, the way `security_base` already treated guards — there's no equivalent "do we want a separate owned table" question for HR records the way there is for a whole vehicle subsystem with its own fuel/service/odometer satellite tables).

### A.3 Model and module naming convention (unified)

| Layer | Convention | Example |
|---|---|---|
| Python package / addon folder name | `deployfleet_<domain>` | `deployfleet_dispatch`, `deployfleet_billing`, `deployfleet_mobile_driver` |
| Odoo technical model name (net-new, no Odoo-core equivalent) | `deployfleet.<entity>` | `deployfleet.trip`, `deployfleet.shipment`, `deployfleet.dispatch.assignment` |
| Odoo technical model name (delegates to Odoo core, e.g. vehicle) | `deployfleet.<entity>` with `_inherits` pointing at the core model | `deployfleet.vehicle` (`_inherits` `fleet.vehicle`) |
| Odoo technical model name (classical extension of Odoo core, e.g. employee) | `_inherit` the core model directly, no new model | `_inherit = "hr.employee"` for driver fields |
| Security group `xml_id` | `group_deployfleet_<role>` | `group_deployfleet_driver`, `group_deployfleet_dispatcher` |
| Module category | `DeployFleet Operations` | — |

This replaces the earlier split naming (`dfleet.*` for net-new models, bare `fleet_*` for module folders) with one consistent `deployfleet` word used everywhere — simpler to remember and impossible to mistake for the native Odoo Fleet app.

### A.4 Why this is easier than it sounds — and where the real risk hides

Because DeployFleet is a **new repository with no live database to migrate**, there is no need for the in-place model-rename machinery Odoo normally requires (renaming a model in a *running* production database means data migration scripts, updating `ir.model.data` references, etc.). We are writing fresh modules against fresh model names from day one. The "refactor" in most of the audit table is therefore **redesign-and-rewrite against a clean schema**, not **rename-in-place** — which is the easier and safer version of this problem. Treat any instinct to mechanically search-and-replace `security.` → `deployfleet.` across copied files as a trap: copying a `security.roster.slot` file and renaming it to `deployfleet.trip.assignment` will carry over guard-shift field semantics (grade, post, certification) that don't belong on a trip-assignment record. Read the source model, understand *why* each field exists, and re-derive the field list for the new domain — don't rename-and-ship.

---

## B. Technical debt triage

Source: `KNOWN_ISSUES.md` in the DeployGuard repo, cross-checked against the actual codebase during this analysis.

### Fix during the fork (natural checkpoint — don't reproduce the bug in new code)

| Item | Why now, not later |
|---|---|
| Event bus dispatcher hardcodes its subscriber list (`security_base/models/security_event_bus.py` — `_dispatch_event()` is a fixed if-chain naming five specific bridge models) | Discovered during architecture review — this is the one real defect in an otherwise excellent piece of reusable infrastructure (see [02-reuse-strategy.md](02-reuse-strategy.md) §0). Fix while porting: replace the hardcoded chain with a subscriber-registry data model, so `deployfleet_event_bus` never has compile-time knowledge of its downstream dependents. Small fix, but do it at the point of porting rather than copying the anti-pattern forward, since every later module (breakdown, maintenance, compliance, notifications) will register itself as a subscriber. |
| Mobile controller field-name mismatches (e.g., a controller querying `batch_id` when the model field is `attendance_batch_id`) | We're rewriting every mobile controller against new models anyway (see [02-reuse-strategy.md](02-reuse-strategy.md) §5), now split across `deployfleet_mobile_driver`/`_dispatcher`/`_customer`. No reason to introduce a fresh version of this class of bug when every query is being rewritten from scratch. Add a controller-level integration test per endpoint as it's written, not after. |
| Mobile role detection via username/name heuristics instead of actual Odoo groups | Same logic — `src/api/auth.ts` is being touched anyway for the new role set. Fetch groups from a `/me` endpoint from the start. |
| `security_payroll_core` hard-depending on `security_l10n_na` even though it's supposed to be the country-neutral engine | The single most important debt item for DeployFleet specifically, because the roadmap is explicitly multi-country. Fix: `deployfleet_payroll` depends only on `deployfleet_core`/`hr`; country packs (`deployfleet_l10n_zm`, `deployfleet_l10n_na`, future packs) each depend on `deployfleet_payroll` independently and register their rule sets via data, not via a manifest dependency chain between country packs. |
| No CI, no linters, no mobile lockfile | Trivial to set up correctly on a fresh repo, expensive to retrofit later. Set up `ruff`/`pylint-odoo` + ESLint + a GitHub Actions workflow (Odoo `--test-enable` + mobile typecheck) as part of repo scaffolding, before the first business-logic module lands. |
| Root-level scratch files (`eq.xml`, `fl.xml` in the source repo) | Don't copy them. |
| Equipment module manifest metadata bugs (wrong author field, etc.) | Free to fix while writing fresh manifests. |

### Defer, but track explicitly (don't silently drop)

| Item | Recommended phase |
|---|---|
| Saturday/night premium multipliers exist on the rule set model but aren't applied in the compute step | Carries over as-is into `deployfleet_payroll` — fix when Zambia payroll goes to UAT. Not blocking for the Operational Foundation or Cost Control phases. |
| Midnight/holiday shift split (a trip spanning a boundary should split into two premium categories) | Relevant to driver payroll, not to the dispatch domain work happening first. Track for the Compliance phase (payroll hardening). |
| Accounting/GL bridge completeness (`account.move` sync) | `deployfleet_billing_account` bridge module already exists as a pattern; harden once `deployfleet_billing` itself is stable. |
| Bank statement import / reconciliation automation | Backlog item in the source too — no reason to pull it forward. |
| Amount-in-words invoice text (currently simplified) | Cosmetic; fix opportunistically. |
| No auto-dispatch optimizer, rest/consecutive-day rules not yet enforced as hard constraints | More important for DeployFleet than the equivalent shift-rest rule was for DeployGuard (driver hours-of-service is a safety/regulatory concern, not just a labor-practice one) — see [06-risks-and-recommendations.md](06-risks-and-recommendations.md) risk #3. Elevated to the Compliance phase, not left as a P2 backlog item the way the source treated it. |
| Test coverage gaps (mobile HttpCase tests, operations model tests) | Set the coverage *bar* from day one on new modules; backfilling the source's exact gaps is moot since its modules aren't being copied verbatim. |
| Offline mobile queue | Genuinely hard (sync protocol, conflict resolution) — correctly deferred in the source. Revisit timing against the connectivity-risk question in [06-risks-and-recommendations.md](06-risks-and-recommendations.md) — may need to move earlier than originally planned if target routes have poor coverage. |
| FCM/Expo push notifications not wired end-to-end | Wire up as part of `deployfleet_mobile_push_bridge` — worth doing early since dispatch alerts (new trip assigned, breakdown reported) are more time-critical for a dispatcher than a document-expiry notice was for security ops. |

### Drop — not applicable to trucking, don't spend time deciding what to do with it

| Item | Why it's simply gone |
|---|---|
| Grade `sequence`-field-as-implicit-rank ("higher sequence = lower grade, undocumented") | The whole grade/certification model is being redesigned for license classes and endorsements; this specific implicit-ordering bug has no analog to carry forward. |
| Guard-specific certification/disqualification field semantics | Redesigned wholesale as driver qualification/license-class/medical-fitness fields on `deployfleet_driver`. |
| "Discipline" framing itself | Per architecture review, this isn't just a rename — the whole HR-conduct framing is replaced by a performance/safety framing (`deployfleet_driver_performance`); see [01-module-audit.md](01-module-audit.md). |
| `security_dogforce_data`, `security_dogforce_migration`, both demo-data modules | Not technical debt to fix — content to not fork at all. See [06-risks-and-recommendations.md](06-risks-and-recommendations.md). |

---

## C. Sequencing implication

Because `deployfleet_core` (identity), `deployfleet_event_bus`, and the vehicle-delegation decision in §A sit underneath every other module, **no other module work should start until those three are settled.** This is Phase 0 in [05-implementation-roadmap.md](05-implementation-roadmap.md).
