# 01 — Module Audit

*Revision 2 — updated after architecture review. Changes from v1: all proposed module names now use the `deployfleet_` namespace (not `fleet_`, which reads as native Odoo); `security_base`'s event bus (`security.event.log`) is now correctly identified and elevated as a core reusable asset; driver profile split out as its own module; `security_discipline` reframed as `deployfleet_driver_performance` rather than an HR-flavored "discipline" module; equipment split three ways (parts / tyres / assets) instead of two; mobile split three ways by user role instead of one monolithic API module. See [00 — Revision Log](README.md#revision-log).*

Complete inventory of the 45 custom modules in `DogFrce-Security-Services-Custom-Odoo-Modules` (Odoo 19 Community), classified for the DeployFleet fork. Sizes are approximate lines of code (Python / XML) at time of analysis, from the `custom_addons/` tree.

**Classification legend**

| Label | Meaning |
|-------|---------|
| **Keep unchanged** | Fork the module with a package rename only. No model, field, or logic changes. |
| **Keep + rename** | Rename module/models/fields to remove security-industry naming, but the logic and structure carry over almost verbatim. |
| **Keep + heavy refactor** | The engine/pipeline is reusable; the domain surface (fields, workflows, what triggers what) needs real redesign for trucking. |
| **Split** | Module is doing too much for a domain that will be central (not peripheral) in DeployFleet; break into 2+ modules along natural seams. |
| **Remove** | Client-specific, guard-industry-specific with no reusable shape, or a meta-module referencing removed modules. |

---

## Foundation layer

| Module | Size (py/xml) | Classification | Proposed name | Rationale |
|--------|---------------|-----------------|---------------|-----------|
| `security_base` | 480 / 1,778 | **Keep + heavy refactor, split** | `deployfleet_core` (identity, groups) + promote `deployfleet_event_bus` out of it | **Correction from v1:** this module contains more than guard identity and groups — `models/security_event_bus.py` implements a real, working event bus (`security.event.log`, with `register_event()` publish and `_dispatch_event()` fan-out), already consumed by `security_mobile_bridge` for push alerts on events like `attendance.missed`, `fleet.breakdown`, and `compliance.bypass`. This is the single most valuable piece of infrastructure in the codebase and was under-weighted in v1 of this audit. It should be pulled into its own module (`deployfleet_event_bus`) rather than staying bundled inside identity/groups, both because it's genuinely a separate concern and because every module that publishes or subscribes to events should depend on the bus directly, not transitively through the identity module. See [02-reuse-strategy.md](02-reuse-strategy.md) §1 for the reuse plan and [03-refactoring-roadmap.md](03-refactoring-roadmap.md) for the one real defect in it (hardcoded subscriber list). |
| *(new, split out of `security_base`)* | ~90 lines (extracted) | **Promote to first-class module** | `deployfleet_event_bus` | Depends only on `mail`. Every operational module (dispatch, trip execution, workshop, compliance) publishes events here; notification, mobile-push, AI, and CRM-sync bridges subscribe. Foundational — should exist before any operational module is built, not bolted on later as the user's review correctly emphasized. |
| `security_licensing` | 334 / 278 | **Keep + rename** | `deployfleet_licensing` | Product entitlement/license-key enforcement for the DeployFleet product itself. Zero domain coupling. |
| `security_theme` | 77 / 330 | **Keep + rename** | `deployfleet_theme` | White-label branding, login customization, PDF theming. Zero domain coupling. |
| `security_help` | 91 / 2,583 | **Keep + rename** | `deployfleet_help` | OWL help portal engine is generic; content needs rewriting for trucking workflows. |
| `security_tour` | 233 / 349 | **Keep + rename** | `deployfleet_tour` | Product tour engine is generic; tour scripts need rewriting. |
| `security_backup_vault` | 514 / 254 | **Keep unchanged** | `deployfleet_backup` | WAL PITR, filestore snapshotting, offsite backup, disk alerts — domain-agnostic infra. |
| `security_reconciliation_core` | 310 / 96 | **Keep + rename** | `deployfleet_reconciliation_core` | Governed cross-module sync/audit framework — generic, distinct from the event bus (this handles data reconciliation/conflict resolution; the event bus handles real-time notification fan-out). Rename only. |
| `security_notifications` | 311 / 213 | **Keep unchanged** | `deployfleet_notifications` | Generic internal alert model + daily cron pattern. Should become a natural subscriber of `deployfleet_event_bus` rather than only running its own crons — see [02-reuse-strategy.md](02-reuse-strategy.md). |

## People

| Module | Size (py/xml) | Classification | Proposed name | Rationale |
|--------|---------------|-----------------|---------------|-----------|
| `security_base` (guard profile fields on `hr.employee`) | *(fields split out, see above)* | **Split into its own module** | `deployfleet_driver` | Per review feedback: a driver is not "an employee with a few extra fields" the way a guard arguably was — license class, endorsements, truck-type qualifications, accident history, and a computed risk/fuel-efficiency profile are substantial enough to deserve a dedicated module rather than living inside the identity/core module. Depends on `deployfleet_core` + `hr`. |
| `security_payroll_core` | 2,181 / 2,497 | **Keep + rename** | `deployfleet_payroll` | Payroll pipeline is country-agnostic HR machinery. **Fix the documented coupling bug** where this depends on the Namibia pack directly — see [03-refactoring-roadmap.md](03-refactoring-roadmap.md). |
| `security_leave` | 540 / 356 | **Keep unchanged** | `deployfleet_leave` | Leave types/balances/requests — no domain coupling. |
| `security_l10n_zm` | 438 / 1,175 | **Keep unchanged** | `deployfleet_l10n_zm` | NAPSA, NHIMA, WCF, PAYE, ZM payslip — Zambia country data needed on day one. |
| `security_l10n_na` | 122 / 862 | **Keep unchanged, deprioritized** | `deployfleet_l10n_na` | Not needed for Zambia-first launch; kept dormant for regional expansion. |
| `security_loans` | 255 / 320 | **Keep unchanged** | `deployfleet_loans` | Employee loans + payslip deductions — generic. |
| `security_discipline` | 298 / 267 | **Keep + reframe, rename** | `deployfleet_driver_performance` | **Correction from v1:** per review, "discipline" is an HR-centric label that undersells what this data actually is for trucking — accidents, violations, harsh-braking/speeding events, fuel-abuse patterns, and late deliveries are performance and safety signals, not employee conduct write-ups. The underlying state machine (incident type → severity → reliability-score impact → optional payroll deduction) carries over unchanged; only the framing, field labels, and incident-type taxonomy change. |
| `security_discipline_payroll` | 154 / 0 | **Keep + rename** | `deployfleet_driver_performance_payroll_bridge` | Attendance/trip-execution ↔ performance ↔ payroll bridge. Generic bridge pattern; rename only. |
| *(new)* | — | **Net-new, low priority** | `deployfleet_training` | Per review: driver certification/refresher training (defensive driving, hazmat handling, first aid) has no direct DeployGuard analog but is a natural companion to the driver profile's license/qualification fields. Not in the MVP-12 — see [04-module-structure.md](04-module-structure.md). |

## Fleet assets

| Module | Size (py/xml) | Classification | Proposed name | Rationale |
|--------|---------------|-----------------|---------------|-----------|
| `security_fleet` | 1,009 / 1,505 | **Split** | `deployfleet_vehicle` + `deployfleet_route` + `deployfleet_trip` (operations layer, see below) + `deployfleet_fuel` + `deployfleet_inspection` | Seed of the entire product. Today it has `SecurityVehicle`, `SecurityShuttleRoute`/`RouteStop`, `SecurityShuttleRun`/`Passenger`, `SecurityVehicleFuelLog`, `SecurityVehicleInspection`, `SecurityVehicleServiceLog`, and a Fleet Dashboard OWL widget. `SecurityVehicleServiceLog` peels off into the new workshop module below. **`deployfleet_vehicle` should be built as a delegation layer over Odoo's native `fleet.vehicle`, not a standalone reinvention** — see [03-refactoring-roadmap.md](03-refactoring-roadmap.md) §A.1 for the resolved pattern. |
| *(new, seeded from `SecurityVehicleServiceLog` + `security_equipment`'s allocation/damage workflow)* | — | **New module** | `deployfleet_workshop` | Job cards: open → diagnose → repair (labor + parts) → approve → close. `security_equipment`'s allocation → damage → payroll-deduction state machine is the closest existing analog. |
| `security_equipment` | 923 / 1,513 | **Split three ways** | `deployfleet_parts` (categories, items, allocations, stock alerts) + `deployfleet_tyres` (net-new lifecycle) + `deployfleet_assets` (net-new) | **Correction from v1 (two-way split → three-way):** per review, transportation companies carry meaningful non-vehicle, non-tyre, non-parts assets — trailers, containers, GPS trackers, safety equipment, hand tools. Bundling those into "spare parts" would misrepresent them (a trailer isn't consumed the way a brake pad is) and bundling them into "vehicle" would overload that model. `deployfleet_assets` is a generic trackable-asset register (acquisition, assignment, condition, retirement) sitting alongside, not inside, parts and tyres. |
| `security_equipment_payroll` | 184 / 0 | **Keep + heavy refactor** | `deployfleet_workshop_payroll_bridge` | Unreturned-kit/damage deductions on termination, low-stock alerts. Pattern reusable. |
| `security_documents` | 282 / 332 | **Keep + heavy refactor** | `deployfleet_compliance_documents` | Document-type + expiry + verification pattern, generalized to a polymorphic link (driver *or* vehicle) instead of the guard-only `hr.employee` link it has today. |
| `security_fleet_ops` | 172 / 0 | **Keep + heavy refactor** | `deployfleet_fleet_ops_bridge` | Already a fleet↔operations↔attendance bridge, and — per the event-bus finding above — already publishes/subscribes to bus events (`fleet.breakdown` originates here). This is the most directly reusable bridge in the codebase; keep the event-driven shape, don't rebuild it as direct model calls. |
| *(new)* | — | **New module** | `deployfleet_maintenance` | Odometer/engine-hour/calendar-based preventive service scheduling. Reuses the recurring-reminder pattern from `security_documents` and the cron-alert pattern from `security_notifications`; publishes `deployfleet.maintenance.due` events on the bus. |
| *(new)* | — | **New module** | `deployfleet_breakdown` | Breakdown/incident logging, severity, resolution, root-cause. Reuses `security_discipline`'s incident-type + severity + resolution state machine (that module tracks *behavioral* incidents; this one tracks *mechanical* ones — same shape, different taxonomy) and publishes `deployfleet.vehicle.breakdown` events, consumed today (in the source) by the mobile bridge. |
| *(new)* | — | **New module** | `deployfleet_insurance` | Policy, premium, claims. Reuses the `deployfleet_compliance_documents` expiry engine, extended with a claims sub-model. |

## Operations — the heart of the product

| Module | Size (py/xml) | Classification | Proposed name | Rationale |
|--------|---------------|-----------------|---------------|-----------|
| `security_operations` | 2,835 / 2,702 | **Split** | `deployfleet_customer` (client/contract layer) + `deployfleet_dispatch` (scheduling layer, direct successor to roster batch/slot) | The `client → site → post → shift requirement → roster batch → roster slot` chain remodels into `customer → contract → depot/terminal` (barely changes) plus `dispatch batch → trip assignment` (changes completely). Split for the same reason as v1: independent versioning/testing of a stable layer vs. a heavily-redesigned one. |
| *(new — the single most important domain addition from review)* | — | **New module, not in v1 of this audit** | `deployfleet_shipment` | **This is the biggest correction in this revision.** v1 proposed `customer → contract → lane → route → trip` with no explicit cargo/load concept. Per review: "a trip without cargo is meaningless" — almost every trucking company thinks in shipments/loads first, trips second. `deployfleet_shipment` sits between `deployfleet_customer` and `deployfleet_trip`: a shipment carries the commercial cargo details (what, how much, pickup, drop-off, weight) and one or more trips fulfill it. See [07-domain-model-erd.md](07-domain-model-erd.md) for the full entity model. |
| `security_shift_planner` | 1,197 / 4,054 | **Keep + heavy refactor** | `deployfleet_dispatch` (scoring + board, merged with the split above) | Constraint-satisfaction scoring engine (grade/cert/rest-rule matching) reusable for driver↔vehicle↔trip assignment; the Roster Board OWL becomes the Dispatch Board. |
| `security_attendance` | 1,505 / 1,941 | **Keep + heavy refactor** | `deployfleet_trip_execution` | "Scheduled vs. actual" pattern maps to "planned trip vs. actual trip" (departure/arrival, odometer, delay reason). Already publishes bus events in the source (`attendance.missed`) — the trip-execution successor should publish the trip-domain equivalent (e.g. `deployfleet.trip.delayed`, `deployfleet.trip.departed`). |
| *(new)* | — | **New module** | `deployfleet_delivery` | Proof-of-delivery: signature, photo, GPS stamp, recipient details. No direct DeployGuard analog (guarding has no "delivery" concept) but structurally a terminal state on the trip/shipment lifecycle — see [07-domain-model-erd.md](07-domain-model-erd.md). |
| `security_route` *(modeled today as `SecurityShuttleRoute`/`RouteStop` inside `security_fleet`)* | *(counted under `security_fleet` above)* | **Split out** | `deployfleet_route` | Routes and route stops deserve their own module now that routing (not just a guard-shuttle convenience) is core to the product. |
| `security_compliance_roster` | 178 / 15 | **Keep + heavy refactor** | `deployfleet_compliance_dispatch` | Bridges document compliance with dispatch (block assignment if driver/vehicle document expired, with emergency-override + audit trail). Publishes `compliance.bypass` events in the source — keep that event-driven behavior. |
| `security_client_onboarding` | 418 / 221 | **Keep + heavy refactor** | `deployfleet_customer_onboarding` | 6-step wizard (contract → sites → shift requirements → billing plan → first roster batch) restructures to (contract → routes/lanes → rate card → billing plan → first shipment). |
| `security_operations_crm` | 208 / 22 | **Keep + heavy refactor** | `deployfleet_operations_crm` | Syncs operational KPIs to CRM opportunities; already an event-bus subscriber in the source (`security.operations.crm.bridge`). Swap KPIs for on-time %, breakdown rate, utilization. |

## Finance

| Module | Size (py/xml) | Classification | Proposed name | Rationale |
|--------|---------------|-----------------|---------------|-----------|
| `security_billing` | 1,742 / 1,798 | **Keep + heavy refactor** | `deployfleet_billing` | Contract/billing-plan/invoice pipeline reusable; rate basis moves to per-trip/tonnage/distance/lane. Billing Command Center and Document Designer OWL UIs directly reusable shells. |
| `security_accounting_controls` | 405 / 284 | **Keep unchanged** | `deployfleet_accounting_controls` | Payment tracking + ageing — generic AR logic. |
| `security_client_reports` | 1,242 / 1,058 | **Keep + heavy refactor** | `deployfleet_client_reports` | Client-facing reports become shipment/trip summaries. |
| `security_billing_account` | 132 / 41 | **Keep + rename** | `deployfleet_billing_account` | Bridge to standard `account.move`. |
| `security_billing_crm` | 102 / 47 | **Keep + rename** | `deployfleet_billing_crm` | CRM lead↔billing plan bridge. |
| `security_billing_sale` | 126 / 184 | **Keep + rename** | `deployfleet_billing_sale` | Sales-order↔billing plan bridge. |
| `security_reconciliation_billing_account` | 766 / 58 | **Keep + rename** | `deployfleet_reconciliation_billing_account` | Invoice/payment/credit-note reconciliation. |
| `security_zra_invoice` | 815 / 544 | **Keep + rename** | `deployfleet_zra_invoice` | Zambia ZRA Smart Invoice (VSDC) — legal requirement regardless of industry. |

## Reporting

| Module | Size (py/xml) | Classification | Proposed name | Rationale |
|--------|---------------|-----------------|---------------|-----------|
| `security_reporting` | 45 / 1,590 | **Keep + rename** | `deployfleet_reports` | Pivot/graph dashboard shell, no new models. Rebuild dashboards against new model names. |

## Mobile & portal

| Module | Size (py/xml) | Classification | Proposed name | Rationale |
|--------|---------------|-----------------|---------------|-----------|
| `security_mobile` | 3,116 / 22 | **Split three ways** | `deployfleet_mobile_driver` + `deployfleet_mobile_dispatcher` + `deployfleet_mobile_customer` | **Correction from v1:** one monolithic `security_mobile` served three roles (supervisor/manager/owner) through role-partitioned controller files but a single module and app. Per review, drivers, dispatchers, and customers have different enough usage patterns (a driver needs a trip-focused, mostly-offline-tolerant app; a dispatcher needs a real-time board; a customer needs a read-only tracking view) to warrant separate installable modules and, likely, separate lightweight app shells rather than one app with three logins. The `@require_group` + response-envelope pattern is shared infrastructure underneath all three — see [02-reuse-strategy.md](02-reuse-strategy.md). |
| `security_mobile_bridge` | 79 / 0 | **Keep + heavy refactor** | `deployfleet_mobile_push_bridge` | Event-bus-to-push-notification bridge. Already a bus subscriber in the source — reuse that shape, just repoint at the renamed event names. |
| `security_portal` | 171 / 314 | **Keep + heavy refactor** | `deployfleet_customer_portal` | Client portal becomes shipment status, active trips, POD, feedback. |

## AI

*Revision 3 — see [08-ai-architecture.md](08-ai-architecture.md) for the full design; this table now reflects a verified re-check of `security_ai_engine`'s actual model code (config/cache/log), not just its manifest summary. One module splits into four.*

| Module | Size (py/xml) | Classification | Proposed name | Rationale |
|--------|---------------|-----------------|---------------|-----------|
| `security_ai_engine` | 3,422 / 1,820 | **Keep + heavy refactor, split** | `deployfleet_ai_core` (provider router, config, cache, usage log, chat) + `deployfleet_ai_permissions` (new) + `deployfleet_ai_actions` (new) + `deployfleet_ai_agents` (agent personas as data) | **Correction from revision 2:** re-reading the actual model code (not just the manifest summary) shows the provider-router shape, per-feature toggles, response cache, and usage/cost logging are already substantially built — verified against [08-ai-architecture.md](08-ai-architecture.md) §0 line by line. What's genuinely missing is granular per-role AI permission scoping and an action-approval pipeline (AI that writes, not just reads) — neither exists in the source at all. The single `deployfleet_ai` module proposed in revision 2 is now four: `deployfleet_ai_core` (the verified-reusable 70%), `deployfleet_ai_permissions` and `deployfleet_ai_actions` (the genuinely new 30%, kept separate specifically so a customer can run AI analysis without AI write-actions), and `deployfleet_ai_agents` (the six-agent catalog as configuration data, not new code). |
| `security_ai_whatsapp_bridge` | 1,464 / 821 | **Keep + heavy refactor** | `deployfleet_ai_whatsapp` | WhatsApp check-in/breakdown-reporting/dispatcher-alert bridge, now also capable of triggering `deployfleet_ai_actions` for driver-reported breakdowns — see [08-ai-architecture.md](08-ai-architecture.md) §8. |

## Meta-installers, demo data & migration tooling

| Module | Size (py/xml) | Classification | Proposed name | Rationale |
|--------|---------------|-----------------|---------------|-----------|
| `security_suite` | 72 / 0 | **Remove, replace** | `deployfleet_suite` | Pure dependency list; rewritten once the final module list exists. |
| `security_demo_data`, `security_demo_data_zm` | 1,694 / 0, 1,253 / 0 | **Remove** | — | Guard/site/shift demo content for Namibia and Zambia. Replace with a fresh Zambia *trucking* demo dataset once models exist. |
| `security_demo_site`, `security_demo_zambia_site` | 518 / 1,052, 66 / 0 | **Remove, replace** | `deployfleet_demo_site` | Meta demo-environment modules referencing removed modules by name. |
| `security_dogforce_data` | **71,419** / 0 | **Remove — do not fork** | — | Real client company data. Not reusable architecture. See [06-risks-and-recommendations.md](06-risks-and-recommendations.md). |
| `security_dogforce_migration` | 432 / 180 | **Remove** | — | CSV import tooling scoped to migrating from DogForce's specific legacy system. |

---

## Summary counts

These are planning-level groupings, not an audited ledger — treat the final count as "roughly 50," not a number to reconcile to the digit:

| Classification | Count |
|---|---|
| Keep unchanged (package rename only) | 7 |
| Keep + rename (views/dashboards rebuilt, no logic change) | 8 |
| Keep + heavy refactor (engine reusable, domain surface redesigned) | 18 |
| Split — source module becomes 2+ output modules, at least one genuinely new | `security_base` → `deployfleet_core` + `deployfleet_event_bus`; `security_operations` → `deployfleet_customer` + `deployfleet_dispatch`; `security_fleet` → 4 (`deployfleet_vehicle`, `deployfleet_route`, `deployfleet_fuel`, `deployfleet_inspection`, plus `deployfleet_workshop` seeded from it); `security_equipment` → 3 (`deployfleet_parts`, `deployfleet_tyres`, `deployfleet_assets`); `security_ai_engine` → 4 (`deployfleet_ai_core`, `deployfleet_ai_permissions`, `deployfleet_ai_actions`, `deployfleet_ai_agents`) — 5 source modules producing roughly 16 output modules between them |
| Remove, replace with fresh module | 1 (`security_suite` → `deployfleet_suite`) |
| Remove, no replacement in scope | 6 |
| Net-new, no split lineage at all (no DeployGuard source module to point to) | 5: `deployfleet_shipment`, `deployfleet_delivery`, `deployfleet_maintenance`, `deployfleet_breakdown`, `deployfleet_insurance`, `deployfleet_training` |

Net result: **45 source modules → roughly 50 DeployFleet modules.** The biggest structural change across all three revisions is that five source modules (`security_base`, `security_operations`, `security_fleet`, `security_equipment`, `security_ai_engine`) — the ones doing the most work in DeployGuard — each become multiple, more focused DeployFleet modules, reflecting that fleet, dispatch, and AI-with-guardrails are the product's new center of gravity rather than supporting cast. See [04-module-structure.md](04-module-structure.md) for the finalized list and dependency graph, and [08-ai-architecture.md](08-ai-architecture.md) for why `security_ai_engine` split the way it did.
