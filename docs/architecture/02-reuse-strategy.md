# 02 — Reuse Strategy

What we carry forward, and at what level (concept / pattern / code). Organized by the categories requested in Phase 1: business logic, UI components, security groups, reports, APIs, mobile functionality.

The guiding test throughout: **is this reusable because it's generic machinery, or does it only look reusable because we haven't yet noticed the security-industry assumption baked into it?** Several items below note where that assumption is buried.

---

## 1. Reusable business logic

| Engine | Source module | Reuse level | Notes |
|--------|---------------|--------------|-------|
| Constraint-satisfaction scoring | `security_shift_planner` | **Pattern + most code** | Scores guard↔slot fit (grade, cert, rest-rule, exclusion). The scoring *framework* (candidate generation → constraint filter → weighted score → ranked suggestions) is reusable verbatim for driver↔vehicle↔trip assignment. The specific constraints (grade comparison, certification match) get swapped for license-class match, vehicle-type match, and driver rest-hour rules — which, for trucking, are a bigger deal than for guarding (most jurisdictions regulate consecutive driving hours). |
| Document expiry & verification engine | `security_documents` | **Pattern + ~70% code** | Type + expiry-date + verification-status + renewal-reminder pattern. Needs to go from a guard-only (`hr.employee`) link to a polymorphic link (driver *or* vehicle), since DeployFleet needs the same expiry machinery for two entity types where DeployGuard only needed one. |
| Payroll computation pipeline | `security_payroll_core` + `security_l10n_zm`/`security_l10n_na` | **Code, near-verbatim** | Period → payslip → hour categorization → statutory deduction → cross-module deduction pull → PDF. Zero industry coupling in the computation logic itself — this is just "how do you run payroll for hourly/shift workers in Zambia," which applies equally to drivers. Statutory rules (NAPSA/NHIMA/WCF/PAYE) are Zambia-country data, not guard-specific — needed as-is. |
| Deduction-injection architecture | `security_loans`, `security_discipline`, `security_equipment` (extending `security.payslip`) | **Pattern, fully reusable** | Each module extends the payslip model and hooks into `action_compute_from_sources()` to inject its own deduction lines. This plug-in-style extension point is the right shape for driver loans, driver discipline, and unreturned-kit/vehicle-damage deductions — no redesign needed, just re-attach the same hooks to renamed models. |
| Billing plan → invoice pipeline | `security_billing` | **Pattern + partial code** | Contract terms → generation rule → invoice lines → VAT → amount-in-words. Rate basis changes (per-shift/post → per-trip/per-tonnage/per-distance/per-lane) but the pipeline shape (plan defines *how* to bill, a generator turns operational records into invoice lines) is reusable. |
| Governed cross-module reconciliation/audit framework | `security_reconciliation_core` | **Code, verbatim** | Generic sync/audit bus with no domain coupling — reuse as-is. |
| AI provider facade | `security_ai_engine` (config/cache/chat/engine models) | **Code, near-verbatim** | Multi-provider abstraction (Claude/OpenAI/Gemini), caching, chat session/message models, and the assistant chat panel are pure infrastructure. Only the 10 *feature* implementations (anomaly detection, risk profiling, etc.) need reframing — the plumbing underneath does not. |
| ZRA Smart Invoice (VSDC) integration | `security_zra_invoice` | **Code, near-verbatim** | Zambia's e-invoicing mandate doesn't care what industry issued the invoice. Needed as-is for any Zambian company; just re-point at the renamed billing invoice model. |
| Notification/cron alerting engine | `security_notifications` | **Code, verbatim; new triggers** | Generic internal-notification model with daily crons. Reuse the model and cron *pattern*; add new cron triggers for maintenance-due and license/insurance expiry (today it only watches document expiry and overdue invoices). |
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
| `group_security_guard` | `group_fleet_driver` |
| `group_security_supervisor` | `group_fleet_dispatcher` |
| `group_security_manager` | `group_fleet_manager` |
| `group_security_owner` | `group_fleet_owner` |
| `group_security_hr_payroll_officer` | `group_fleet_hr_payroll_officer` |
| `group_security_system_auditor` | `group_fleet_system_auditor` |

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

The `security_mobile` controller architecture is the strongest asset to reuse verbatim as *infrastructure*:

- Session-cookie auth via `/web/session/authenticate` (standard Odoo JSON-RPC) — keep exactly.
- `@require_group()` decorator pattern for endpoint authorization against Odoo security groups — keep exactly, re-point at the new group names.
- Response envelope `{ "success": true, "data": {...} }` / `{ "success": false, "error": "..." }` — keep exactly; this is a good, simple contract and changing it buys nothing.
- Role-partitioned controller files (`guard.py`, `supervisor.py`, `manager.py`, `owner.py`, `notifications.py`) — keep this file-per-role organization; rename to `driver.py`, `dispatcher.py`, `fleet_manager.py`, `owner.py`.
- Endpoint *domains* (what data each query returns) need a full rewrite — they currently query attendance/roster models that won't exist in DeployFleet's schema.

**Do not port forward as-is:** the documented field-name mismatches in the current mobile controllers (`batch_id` vs. the model's actual `attendance_batch_id`, `overtime_note` vs. `overtime_approval_note`) — see [03-refactoring-roadmap.md](03-refactoring-roadmap.md). Rewriting the controllers against new models is the natural point to not reproduce these bugs.

## 6. Reusable mobile functionality

The Expo/React Native app (`mobile/`) is architected as a genuinely thin client, which is exactly right and should not change:

| Layer | Reuse level | Notes |
|-------|--------------|-------|
| Expo Router file-based routing with role route-groups (`(auth)`, `(role)/...`) | **Pattern, verbatim** | `(supervisor)`/`(manager)`/`(owner)` → `(driver)`/`(dispatcher)`/`(fleet-manager)`/`(owner)` |
| `src/api/client.ts` (Axios instance, session injection, auth-expiry handling) | **Code, verbatim** | No domain coupling at all |
| `src/api/auth.ts` (login/logout) | **Code, verbatim, but fix role detection** | Today infers role from username/name heuristics — a documented bug. Fix as part of the fork by fetching actual Odoo groups via a `/me`-style endpoint, not by carrying the heuristic forward. |
| `src/stores/` (Zustand: `authStore`, `appStore`) | **Pattern, verbatim** | Session/UI state layer has no domain coupling |
| `src/theme/` (RN Paper dark theme tokens) | **Code, verbatim or re-skinned via `deployfleet_theme` tokens** | |
| `src/components/` (`GuardCard`, `KpiMetric`, `SiteKpiCard`, `StatusBadge`, `CheckInButton`) | **Mixed** | `KpiMetric`, `StatusBadge`, `CheckInButton` are generic UI atoms — reuse verbatim. `GuardCard`/`SiteKpiCard` are domain-shaped — become `DriverCard`/`VehicleCard` and `RouteKpiCard`, rebuilt against new fields but following the same component contract. |

**Known mobile gaps to close *during* the fork rather than carry forward** (all documented in the source `KNOWN_ISSUES.md`): PIN quick re-auth (field exists, no endpoint), FCM/Expo push not wired (device-token field exists, unused), no offline queue, hardcoded `localhost` in the API client. None of these are hard blockers to reuse — they're a to-do list to execute once, in the new repo, rather than a debt to inherit twice.
