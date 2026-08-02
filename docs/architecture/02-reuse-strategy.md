# 02 — Reuse Strategy

*Revision 2 — adds §0 (the event-driven core, a correction to v1 which missed that this already exists in the source) and reframes the AI feature list and mobile/API sections around the 3-way mobile split and `deployfleet_*` naming from the architecture review. Revision 3 — the AI provider facade row now points to the dedicated [08-ai-architecture.md](08-ai-architecture.md), written after a verified re-check of the source's actual AI model code found roughly 70% of the requested AI architecture already built. See [01-module-audit.md](01-module-audit.md) revision notes.*

What we carry forward, and at what level (concept / pattern / code). Organized by the categories requested in Phase 1: business logic, UI components, security groups, reports, APIs, mobile functionality — plus a new §0 for the event-driven core, since it turned out to be the highest-leverage reusable asset in the codebase and deserves top billing rather than being buried in a business-logic table row.

The guiding test throughout: **is this reusable because it's generic machinery, or does it only look reusable because we haven't yet noticed the security-industry assumption baked into it?** Several items below note where that assumption is buried.

---

## 0. The event-driven core — the highest-leverage reusable asset in the codebase

v1 of this document didn't call this out as its own section — it was easy to miss, since it isn't mentioned in the source's own `ARCHITECTURE.md` (which claims "no shared service layer, no event bus" — that description is stale; the event bus was evidently added after that document was last updated). It lives in `security_base/models/security_event_bus.py` and is real, working infrastructure:

- **`security.event.log`** — a model that is simultaneously the event bus *and* its own audit log: `register_event(name, source_model, source_id, payload)` creates a record and immediately calls `_dispatch_event()`, which fans the event out to subscriber models and marks itself `processed` or `failed`.
- **Already has real publishers**: `security_attendance` fires `attendance.missed`; `security_fleet_ops` fires `fleet.breakdown` (and a delay event); `security_compliance_roster` fires `compliance.bypass`; `security_equipment_payroll` and `security_portal` also publish.
- **Already has real subscribers**: `security_mobile_bridge._handle_bus_event()` turns `attendance.missed` / `fleet.breakdown` / `compliance.bypass` directly into Expo push notifications to the right role (supervisors, managers, owners respectively). `security_operations_crm`, `security_discipline_payroll`, `security_fleet_ops`, and `security_equipment_payroll` also implement `_handle_bus_event()` as bridge subscribers.

**Reuse level: code, near-verbatim, with one structural fix.** The one real defect: `_dispatch_event()` hardcodes a fixed if-chain of five specific downstream model names (`if "security.operations.crm.bridge" in self.env: ...`). This means the *core* module (`security_base`) has compile-time knowledge of every *downstream* bridge module that will ever subscribe to it — backwards from how Odoo dependencies should flow, and it means adding a sixth subscriber means editing core again. Fix during the fork: replace the hardcoded chain with a subscriber-registry (a simple `deployfleet.event.subscription` data model mapping an event-name pattern to a model + method, loaded via each subscribing module's own data files) so `deployfleet_event_bus` never needs to change when a new bridge module is added. This is a small, mechanical fix — a few hours of work — but worth doing explicitly rather than copying the hardcoded chain forward. See [03-refactoring-roadmap.md](03-refactoring-roadmap.md).

**Why this matters more for DeployFleet than it did for DeployGuard:** the review correctly identified that transportation generates a much denser stream of operationally significant events (trip departed, vehicle broke down, document expired, delivery completed, dispatch reassigned) than guard shift management does, and that GPS integration (explicitly a later phase) becomes far easier to wire in later if trip/vehicle state changes are already flowing through a bus rather than being read out of tables on demand. Promote `deployfleet_event_bus` to a Phase 0 module — every operational module from Phase 1 onward should be built to publish onto it from day one, not retrofitted later.

## 1. Reusable business logic

| Engine | Source module | Reuse level | Notes |
|--------|---------------|--------------|-------|
| Constraint-satisfaction scoring | `security_shift_planner` | **Pattern + most code** | Scores guard↔slot fit (grade, cert, rest-rule, exclusion). The scoring *framework* (candidate generation → constraint filter → weighted score → ranked suggestions) is reusable verbatim for driver↔vehicle↔trip assignment. The specific constraints (grade comparison, certification match) get swapped for license-class match, vehicle-type match, and driver rest-hour rules — which, for trucking, are a bigger deal than for guarding (most jurisdictions regulate consecutive driving hours). |
| Document expiry & verification engine | `security_documents` | **Pattern + ~70% code** | Type + expiry-date + verification-status + renewal-reminder pattern. Needs to go from a guard-only (`hr.employee`) link to a polymorphic link (driver *or* vehicle), since DeployFleet needs the same expiry machinery for two entity types where DeployGuard only needed one. |
| Payroll computation pipeline | `security_payroll_core` + `security_l10n_zm`/`security_l10n_na` | **Code, near-verbatim** | Period → payslip → hour categorization → statutory deduction → cross-module deduction pull → PDF. Zero industry coupling in the computation logic itself — this is just "how do you run payroll for hourly/shift workers in Zambia," which applies equally to drivers. Statutory rules (NAPSA/NHIMA/WCF/PAYE) are Zambia-country data, not guard-specific — needed as-is. |
| Deduction-injection architecture | `security_loans`, `security_discipline`, `security_equipment` (extending `security.payslip`) | **Pattern, fully reusable** | Each module extends the payslip model and hooks into `action_compute_from_sources()` to inject its own deduction lines. This plug-in-style extension point is the right shape for driver loans, driver discipline, and unreturned-kit/vehicle-damage deductions — no redesign needed, just re-attach the same hooks to renamed models. |
| Billing plan → invoice pipeline | `security_billing` | **Pattern + partial code** | Contract terms → generation rule → invoice lines → VAT → amount-in-words. Rate basis changes (per-shift/post → per-trip/per-tonnage/per-distance/per-lane) but the pipeline shape (plan defines *how* to bill, a generator turns operational records into invoice lines) is reusable. |
| Governed cross-module reconciliation/audit framework | `security_reconciliation_core` | **Code, verbatim** | Generic sync/audit bus with no domain coupling — reuse as-is. |
| AI provider facade | `security_ai_engine` (config/cache/chat/engine models) | **Code, near-verbatim for ~70% of it; genuinely new for the rest** | **Superseded by the dedicated [08-ai-architecture.md](08-ai-architecture.md), written after a field-by-field re-check of `security_ai_engine`'s actual model code (not just its manifest summary) against the architecture review's AI design principles.** Confirmed already built and reusable near-verbatim: the provider router (`active_provider`/`fallback_provider` selection, single `complete()` entry point), per-feature on/off toggles, response caching (`security.ai.cache`, hash + TTL + hit-count), and usage/cost logging (`security.ai.log`, tokens/cost/duration/cache-hit per call). Confirmed genuinely absent from the source and requiring new engineering: granular per-role AI permission scoping (today every user has identical AI access) and any action-capable AI with an approval pipeline (every existing feature reads and explains; none write). DeepSeek is added as a new default provider alongside Claude/OpenAI/Gemini, with a cheap/reasoning model tier per feature — see [08-ai-architecture.md](08-ai-architecture.md) §2. Feature reframing (fuel anomaly detection, predictive maintenance, dispatch assistant, driver risk scoring, payment-risk intelligence, etc.) is detailed there too, restructured into six named agents rather than ten flat feature flags. |
| ZRA Smart Invoice (VSDC) integration | `security_zra_invoice` | **Code, near-verbatim** | Zambia's e-invoicing mandate doesn't care what industry issued the invoice. Needed as-is for any Zambian company; just re-point at the renamed billing invoice model. |
| Notification/cron alerting engine | `security_notifications` | **Code, verbatim; new triggers** | Generic internal-notification model with daily crons. Reuse the model and cron *pattern*; add new cron triggers for maintenance-due and license/insurance expiry (today it only watches document expiry and overdue invoices). Should also register itself as a `deployfleet_event_bus` subscriber (see §0) so time-critical events — breakdown, compliance bypass — surface as in-app notifications immediately rather than waiting for the next daily cron. |
| License/entitlement enforcement | `security_licensing` | **Code, verbatim** | This is DeployFleet's *own* product licensing, not guard licensing — no change needed. |

## 2. Reusable UI components (OWL)

| Component | Source module | Reuse level | Becomes |
|-----------|---------------|--------------|---------|
| Roster Board (drag-drop, constraint-aware) | `security_shift_planner` | Shell + interaction model reusable, data columns redesigned | Dispatch Board — drag driver/vehicle onto a trip slot |
| Fleet Dashboard (already exists as an `AbstractModel` + OWL widget) | `security_fleet` | **Directly reusable — this is already the right shape** | Core Fleet Ops Dashboard |
| Billing Command Center (executive dashboard, AR aging cards) | `security_billing` | Shell + KPI-card layout reusable, data source redesigned | Fleet Billing Command Center |
| Interactive Document/Payslip Designer (drag-drop block reordering, style presets, DOMParser-based secure preview) | `security_billing`, `security_payroll_core` | **Pattern fully reusable** as a generic "printable document designer" | Reused as-is for payslips; same shell can power a Trip Manifest designer or Job Card designer later |
| Help Portal (searchable, country-aware, debounced search) | `security_help` | **Code, verbatim** | DeployFleet Help Centre — only content changes |
| Client Portal dashboard | `security_portal` | Shell reusable, KPIs redesigned | Customer Portal — shipment status, active trips, POD |

## 3. Reusable security groups & permissions

The role-hierarchy *pattern* in `security_base/security/security_groups.xml` — a base group, chained `implied_ids` building Supervisor → Manager → Owner, plus parallel HR/Payroll Officer and read-only System Auditor groups — transfers directly:

| DeployGuard group | DeployFleet equivalent |
|---|---|
| `group_security_guard` | `group_deployfleet_driver` |
| `group_security_supervisor` | `group_deployfleet_dispatcher` |
| `group_security_manager` | `group_deployfleet_manager` |
| `group_security_owner` | `group_deployfleet_owner` |
| `group_security_hr_payroll_officer` | `group_deployfleet_hr_payroll_officer` |
| `group_security_system_auditor` | `group_deployfleet_system_auditor` |

Structure to keep: `res.groups.privilege` categorization, `implied_ids` chaining (so a Fleet Manager automatically has Dispatcher access), and per-module `ir.model.access.csv` + sparing use of `ir.rule` for record-level rules. This is good Odoo practice already in the source and should not be redesigned, only relabeled.

## 4. Reusable reports (QWeb PDF)

| Report | Source module | Reuse level |
|--------|---------------|--------------|
| Payslip (NA + ZM variants) | `security_payroll_core`, `security_l10n_zm` | Verbatim — swap letterhead/branding via `deployfleet_theme` |
| Invoice + invoice-aging report | `security_billing` | Structure reusable, line-item content redesigned (trip/route/tonnage instead of shift/post) |
| Client service report | `security_client_reports` | Structure reusable, content becomes shipment/trip summary |
| Loan statement | `security_loans` | Verbatim |
| ZRA invoice, NAPSA/NHIMA/WCF/PAYE statutory reports | `security_zra_invoice`, `security_l10n_zm` | Verbatim — legal/statutory formats, industry-agnostic |
| Equipment allocation report | `security_equipment` | Structure reusable for spare-parts issuance report |

**Net-new reports with no direct analog:** trip manifest / waybill, vehicle inspection report, job card, fuel reconciliation report, tyre lifecycle report, proof-of-delivery (POD) document. These should be built using the reusable Document Designer shell (see UI table above), not from scratch.

## 5. Reusable APIs

The `security_mobile` controller architecture is the strongest asset to reuse verbatim as *infrastructure*, even though — per architecture review — it now splits into three installable modules (`deployfleet_mobile_driver`, `deployfleet_mobile_dispatcher`, `deployfleet_mobile_customer`) instead of remaining one:

- Session-cookie auth via `/web/session/authenticate` (standard Odoo JSON-RPC) — keep exactly, shared across all three.
- `@require_group()` decorator pattern for endpoint authorization against Odoo security groups — keep exactly, re-point at the new group names (`group_deployfleet_driver`, `group_deployfleet_dispatcher`, etc.).
- Response envelope `{ "success": true, "data": {...} }` / `{ "success": false, "error": "..." }` — keep exactly; this is a good, simple contract and changing it buys nothing.
- Role-partitioned controller files (`guard.py`, `supervisor.py`, `manager.py`, `owner.py`, `notifications.py`) — the *file-per-role* organization was already right; it now becomes *module-per-role* to match the 3-way split: `deployfleet_mobile_driver/controllers/`, `deployfleet_mobile_dispatcher/controllers/`, `deployfleet_mobile_customer/controllers/`, each depending on a shared base (`deployfleet_mobile_api` or folded into `deployfleet_base`) that carries the auth/envelope/decorator plumbing all three need.
- Endpoint *domains* (what data each query returns) need a full rewrite — they currently query attendance/roster models that won't exist in DeployFleet's schema.

**Do not port forward as-is:** the documented field-name mismatches in the current mobile controllers (`batch_id` vs. the model's actual `attendance_batch_id`, `overtime_note` vs. `overtime_approval_note`) — see [03-refactoring-roadmap.md](03-refactoring-roadmap.md). Rewriting the controllers against new models is the natural point to not reproduce these bugs.

## 6. Reusable mobile functionality

The Expo/React Native app (`mobile/`) is architected as a genuinely thin client, which is exactly right and should not change. Per architecture review, the single app with three role-routed sections is likely better split into purpose-built shells (a driver app can tolerate — even expect — intermittent connectivity and a trip-focused UI; a dispatcher needs a real-time board better suited to a tablet/desktop-class experience; a customer-facing tracking view is nearly read-only). Whether that becomes three separate Expo apps or three route groups within one app sharing a common shell is an implementation-time call, not an architecture-time one — either way, the underlying layers below are shared:

| Layer | Reuse level | Notes |
|-------|--------------|-------|
| Expo Router file-based routing with role route-groups (`(auth)`, `(role)/...`) | **Pattern, verbatim** | `(supervisor)`/`(manager)`/`(owner)` → `(driver)`/`(dispatcher)`/`(customer)` |
| `src/api/client.ts` (Axios instance, session injection, auth-expiry handling) | **Code, verbatim** | No domain coupling at all — shared across driver/dispatcher/customer clients regardless of how they're packaged |
| `src/api/auth.ts` (login/logout) | **Code, verbatim, but fix role detection** | Today infers role from username/name heuristics — a documented bug. Fix as part of the fork by fetching actual Odoo groups via a `/me`-style endpoint, not by carrying the heuristic forward. |
| `src/stores/` (Zustand: `authStore`, `appStore`) | **Pattern, verbatim** | Session/UI state layer has no domain coupling |
| `src/theme/` (RN Paper dark theme tokens) | **Code, verbatim or re-skinned via `deployfleet_theme` tokens** | |
| `src/components/` (`GuardCard`, `KpiMetric`, `SiteKpiCard`, `StatusBadge`, `CheckInButton`) | **Mixed** | `KpiMetric`, `StatusBadge`, `CheckInButton` are generic UI atoms — reuse verbatim across all three clients. `GuardCard`/`SiteKpiCard` are domain-shaped — become `DriverCard`/`VehicleCard`/`ShipmentCard` and `RouteKpiCard`, rebuilt against new fields but following the same component contract. |

**Known mobile gaps to close *during* the fork rather than carry forward** (all documented in the source `KNOWN_ISSUES.md`): PIN quick re-auth (field exists, no endpoint), FCM/Expo push not wired (device-token field exists, unused), no offline queue, hardcoded `localhost` in the API client. None of these are hard blockers to reuse — they're a to-do list to execute once, in the new repo, rather than a debt to inherit twice.
