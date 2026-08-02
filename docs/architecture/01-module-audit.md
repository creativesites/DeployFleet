# 01 — Module Audit

Complete inventory of the 45 custom modules in `DogFrce-Security-Services-Custom-Odoo-Modules` (Odoo 19 Community), classified for the DeployFleet fork. Sizes are approximate lines of code (Python / XML) at time of analysis (2026-08-02), from the `custom_addons/` tree.

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
| `security_base` | 480 / 1,778 | **Keep + heavy refactor** | `fleet_base` | Core identity layer. `hr.employee` extension for guard grades/certifications/languages/reliability score → becomes driver profile (license class, endorsements, defensive-driving certs, HOS-eligibility flags). Security groups (Guard→Supervisor→Manager→Owner + HR/Payroll + Auditor) are a directly reusable *pattern*; relabel to Driver→Dispatcher→Fleet Manager→Owner. This is the module every other module depends on, so it should be finalized first. |
| `security_licensing` | 334 / 278 | **Keep + rename** | `deployfleet_licensing` | Product entitlement/license-key enforcement for the DeployFleet product itself. Zero domain coupling — pure SaaS/on-prem licensing infrastructure. |
| `security_theme` | 77 / 330 | **Keep + rename** | `deployfleet_theme` | White-label branding, login customization, PDF theming. Zero domain coupling. |
| `security_help` | 91 / 2,583 | **Keep + rename** | `deployfleet_help` | OWL help portal engine (country-aware, full-text search) is generic; only the *content* (articles) needs rewriting for trucking workflows. |
| `security_tour` | 233 / 349 | **Keep + rename** | `deployfleet_tour` | Product tour/onboarding engine is generic; tour *scripts* need rewriting for the new UI flows. |
| `security_backup_vault` | 514 / 254 | **Keep unchanged** | `deployfleet_backup_vault` | WAL PITR, filestore snapshotting, Cloudflare R2 offsite backup, disk alerts — completely domain-agnostic infra. |
| `security_reconciliation_core` | 310 / 96 | **Keep + rename** | `fleet_reconciliation_core` | Governed cross-module sync/audit framework — genuinely generic. Depends only on `security_base`/`mail`. Rename for consistency, no logic change. |

## Operations & scheduling core

| Module | Size (py/xml) | Classification | Proposed name | Rationale |
|--------|---------------|-----------------|---------------|-----------|
| `security_operations` | 2,835 / 2,702 | **Split** (largest single model file in the codebase) | `fleet_operations` (contracts, sites/depots, demand planning) + `fleet_dispatch` (roster batch/slot → trip schedule/dispatch board) | Models `client → site → post → shift requirement → roster batch → roster slot` remodel to `client → contract/lane → depot/terminal → trip requirement → dispatch batch → trip assignment`. This is the single biggest domain-remodel effort in the whole fork — see [04-module-structure.md](04-module-structure.md). Splitting keeps the contract/site layer (which barely changes) separate from the scheduling layer (which changes completely), so the two can be versioned and tested independently. |
| `security_shift_planner` | 1,197 / 4,054 (largest XML — the Roster Board OWL client) | **Keep + heavy refactor** | `fleet_dispatch_planner` | Constraint-satisfaction scoring engine (grade/cert/rest-rule matching) is directly reusable for driver↔vehicle↔trip assignment scoring; rest-rule logic maps well onto Hours-of-Service-style driver rest/consecutive-day rules, which trucking regulators care about even more than security guarding does. The Roster Board OWL UI becomes the Dispatch Board. |
| `security_attendance` | 1,505 / 1,941 | **Keep + heavy refactor** | `fleet_trip_execution` | "Scheduled vs. actual" pattern (posting sheet → attendance record) maps to "planned trip vs. actual trip" (planned route/time → actual departure/arrival, odometer, delay reason). The computed-metrics approach (worked hours, late minutes, missing checkout) is structurally identical to (trip duration, late departure, missing odometer-in). |
| `security_compliance_roster` | 178 / 15 | **Keep + heavy refactor** | `fleet_compliance_dispatch` | Bridges document compliance with shift assignment (block assignment if guard's document expired, with emergency-override + audit trail). Directly reusable pattern: block trip dispatch if driver's license/medical or vehicle's insurance/roadworthiness has expired. This bridge pattern is *more* valuable in trucking, where a dispatch against an unlicensed driver or unlicensed vehicle is a regulatory and insurance liability. |
| `security_client_onboarding` | 418 / 221 | **Keep + heavy refactor** | `fleet_client_onboarding` | 6-step wizard (contract → sites → shift requirements → billing plan → first roster batch) restructures to (contract → routes/lanes → rate card → billing plan → first trip schedule). Wizard *shape* reusable, step *content* is not. |
| `security_operations_crm` | 208 / 22 | **Keep + heavy refactor** | `fleet_operations_crm` | Syncs operational KPIs (compliance, incidents, breaches) to CRM opportunities. Pattern reusable; swap KPIs for fleet-relevant ones (on-time %, breakdown rate, utilization). |

## Fleet, maintenance & assets — the new center of gravity

| Module | Size (py/xml) | Classification | Proposed name | Rationale |
|--------|---------------|-----------------|---------------|-----------|
| `security_fleet` | 1,009 / 1,505 | **Split** | `fleet_vehicle_registry` + `fleet_route_planning` + `fleet_trip_management` + `fleet_fuel_management` + `fleet_inspection` | This module is the seed of the entire DeployFleet product. Today it already has `SecurityVehicle`, `SecurityShuttleRoute`/`RouteStop`, `SecurityShuttleRun`/`Passenger`, `SecurityVehicleFuelLog`, `SecurityVehicleInspection`, `SecurityVehicleServiceLog`, and a Fleet Dashboard OWL widget. In DeployGuard this was a side module supporting guard transport; in DeployFleet, vehicles/routes/trips/fuel/inspections *are* the product, and each deserves independent lifecycle, security groups, and tests rather than one 1,000-line model file. `SecurityVehicleServiceLog` peels off into the new workshop module below rather than staying here. |
| *(new, seeded from `SecurityVehicleServiceLog` + `security_equipment`'s allocation/damage workflow)* | — | **Split out as new module** | `fleet_workshop` | Job cards, labor + parts tracking, approval workflow. `security_equipment`'s allocation → damage → payroll-deduction state machine is the closest existing analog for a job-card open → diagnose → repair → close workflow, even though the field content is entirely different. |
| `security_equipment` | 923 / 1,513 | **Split** | `fleet_spare_parts` (categories, items, allocations, stock alerts) + `fleet_tyre_lifecycle` (net-new, seeded from the allocation/damage pattern) | Uniform/radio/firearm allocation-and-damage-deduction pattern is structurally identical to spare-parts issuance to a job card. Tyres get their own module because tyre lifecycle (tread depth readings, position on vehicle, rotation history, retreading, scrap) is a genuinely distinct state machine that the vision calls out explicitly — it should not be another "equipment type" bolted onto a generic asset model. |
| `security_equipment_payroll` | 184 / 0 | **Keep + heavy refactor** | `fleet_workshop_payroll_bridge` | Bridges unreturned-kit deductions with final paycheck, and triggers low-stock alerts. Pattern reusable: unreturned tools/damaged-vehicle deductions on driver termination, low-stock spare-parts alerts. |
| `security_documents` | 282 / 332 | **Keep + heavy refactor** | `fleet_compliance_documents` | Document-type + expiry + verification-workflow pattern is close to 1:1 reusable for driver documents (license, medical, defensive-driving cert) *and* vehicle documents (registration, insurance, roadworthiness, permits, fitness certificate) — likely needs a generic `res_model`/`res_id` polymorphic link instead of the guard-only `hr.employee` link it has today, since DeployFleet needs the same expiry engine on two different entity types. |
| `security_fleet_ops` | 172 / 0 | **Keep + heavy refactor** | `fleet_operations_bridge` | Already a fleet↔operations↔attendance bridge module in DeployGuard (shuttle runs, vehicle status alerts, supervisor patrol logs). This is the most directly-reusable bridge in the entire codebase — the *concept* (vehicle events feeding into ops/attendance) is exactly DeployFleet's core loop, just needs the guard-patrol-log piece replaced with driver/dispatcher event logging. |
| *(new)* | — | **New module** | `fleet_preventive_maintenance` | Odometer/engine-hour/calendar-based service scheduling. No direct DeployGuard analog, but reuses the recurring-reminder engine pattern from `security_documents` (expiry tracking) and the cron-alert pattern from `security_notifications`. |
| *(new)* | — | **New module** | `fleet_breakdown_management` | Incident logging, severity, resolution tracking, root-cause. Reuses `security_discipline`'s incident-type + severity + resolution workflow shape (that module tracks *behavioral* incidents; the state machine — log → classify → resolve → close — transfers directly to *mechanical* incidents). |
| *(new)* | — | **New module** | `fleet_insurance_tracking` | Policy, premium, claims. Reuses `security_documents`' expiry-tracking engine, extended with a claims sub-model. |

## HR & payroll — genuinely generic, minimal change

| Module | Size (py/xml) | Classification | Proposed name | Rationale |
|--------|---------------|-----------------|---------------|-----------|
| `security_payroll_core` | 2,181 / 2,497 | **Keep + rename** | `fleet_payroll_core` | Payroll pipeline (period → payslip → hour categorization → statutory deductions → cross-module deduction pull → PDF) is country-agnostic HR machinery with zero security-industry coupling in its computation logic. Rename only. **Do** fix the documented architectural debt where this module hard-depends on `security_l10n_na` (see [03-refactoring-roadmap.md](03-refactoring-roadmap.md)) — do not carry that coupling into a product whose first market is Zambia, not Namibia. |
| `security_l10n_zm` | 438 / 1,175 | **Keep unchanged** | `fleet_l10n_zm` | NAPSA, NHIMA, WCF levy, PAYE brackets, ZM payslip — this is Zambia country data DeployFleet needs on day one regardless of industry. Rename package only. |
| `security_l10n_na` | 122 / 862 | **Keep unchanged, deprioritized** | `fleet_l10n_na` | Not needed for the Zambia-first launch, but zero reason to discard a working localization pack when Namibia is an explicit "expand to regional operators" target later. Keep dormant. |
| `security_leave` | 540 / 356 | **Keep unchanged** | `fleet_leave` | Leave types/balances/requests — no security-industry coupling. Rename only. |
| `security_loans` | 255 / 320 | **Keep unchanged** | `fleet_loans` | Employee loans + payslip deduction lines — generic. Rename only. |
| `security_discipline` | 298 / 267 | **Keep + rename** | `fleet_discipline` | Behavioral incidents + reliability score impact + payroll deduction. Generic HR discipline engine; keep as-is for driver conduct (separate from `fleet_breakdown_management`, which is mechanical, not behavioral). |
| `security_discipline_payroll` | 154 / 0 | **Keep + rename** | `fleet_discipline_payroll_bridge` | Attendance↔discipline↔payroll bridge (reliability index, progressive discipline, automated penalties). Generic HR bridge; rename only. |

## Billing, contracts & finance

| Module | Size (py/xml) | Classification | Proposed name | Rationale |
|--------|---------------|-----------------|---------------|-----------|
| `security_billing` | 1,742 / 1,798 | **Keep + heavy refactor** | `fleet_billing` | Contract/billing-plan/invoice pipeline is reusable machinery; rate basis changes from per-shift/per-post to per-trip/per-tonnage/per-distance/per-lane. Billing Command Center and Document Designer OWL UIs are directly reusable shells. |
| `security_accounting_controls` | 405 / 284 | **Keep unchanged** | `fleet_accounting_controls` | Payment tracking + ageing — generic AR logic, no domain coupling. Rename only. |
| `security_client_reports` | 1,242 / 1,058 | **Keep + heavy refactor** | `fleet_client_reports` | Client-facing service/attendance reports become client-facing shipment/trip reports. Aggregation pattern reusable; report content is not. |
| `security_billing_account` | 132 / 41 | **Keep + rename** | `fleet_billing_account` | Bridge to standard `account.move`. Logic generic once `security.billing.invoice` is renamed. |
| `security_billing_crm` | 102 / 47 | **Keep + rename** | `fleet_billing_crm` | CRM lead↔billing plan bridge — generic. |
| `security_billing_sale` | 126 / 184 | **Keep + rename** | `fleet_billing_sale` | Sales-order↔billing plan bridge — generic. |
| `security_reconciliation_billing_account` | 766 / 58 | **Keep + rename** | `fleet_reconciliation_billing_account` | Invoice/payment/credit-note reconciliation with Odoo Accounting. Generic once renamed. |
| `security_zra_invoice` | 815 / 544 | **Keep + rename** | `fleet_zra_invoice` | Zambia ZRA Smart Invoice (VSDC) e-invoicing — a legal requirement for Zambian invoicing regardless of industry. Needed as-is for launch market; just re-point at `fleet.billing.invoice`. |

## Reporting & notifications

| Module | Size (py/xml) | Classification | Proposed name | Rationale |
|--------|---------------|-----------------|---------------|-----------|
| `security_reporting` | 45 / 1,590 | **Keep + rename** | `fleet_reporting` | Pivot/graph dashboard shell with no new models. Rebuild dashboards against new model names; the pivot/graph view *definitions* are a reusable template. |
| `security_notifications` | 311 / 213 | **Keep unchanged** | `fleet_notifications` | Generic internal alert model + daily cron pattern (today: document expiry, overdue invoices). Add crons for maintenance-due and license/insurance expiry — same engine, new triggers. |

## Mobile, portal & AI

| Module | Size (py/xml) | Classification | Proposed name | Rationale |
|--------|---------------|-----------------|---------------|-----------|
| `security_mobile` | 3,116 / 22 | **Keep + heavy refactor** | `fleet_mobile_api` | REST JSON controller pattern (role-gated via `@require_group`, `{success, data/error}` envelope) is directly reusable. Role split (supervisor/manager/owner → driver/dispatcher/fleet-manager/owner) and every endpoint's query domain need rewriting for the new operational model. **Fix known field-name bugs during this rewrite** (see [03-refactoring-roadmap.md](03-refactoring-roadmap.md)) rather than porting them forward. |
| `security_mobile_bridge` | 79 / 0 | **Keep + heavy refactor** | `fleet_mobile_bridge` | Event-bus-to-push-notification bridge (Expo). Wire up the currently-unused device-token/push path as part of this fork rather than carrying the gap forward. |
| `security_portal` | 171 / 314 | **Keep + heavy refactor** | `fleet_customer_portal` | Client portal dashboard (posting stats, active rosters, feedback) becomes shipment status, active trips, POD (proof of delivery), and customer feedback. |
| `security_ai_engine` | 3,422 / 1,820 | **Keep + heavy refactor** | `fleet_ai_engine` | Multi-provider AI facade (provider abstraction, config, cache, chat session/message models) is 100% reusable infrastructure. The 10 built-in features need reframing: anomaly detection → fuel/fraud anomaly detection, risk profiling → driver risk scoring, billing audit → freight billing audit, roster optimizer → dispatch optimizer, shift-fill → trip-fill, incident advisor → breakdown/accident advisor, document-renewal → license/insurance-renewal nudges, performance review, payslip explanation (unchanged). |
| `security_ai_whatsapp_bridge` | 1,464 / 821 | **Keep + heavy refactor** | `fleet_ai_whatsapp_bridge` | WhatsApp webhook → roster matching → AWOL logging → incident generation becomes WhatsApp → trip check-in → breakdown reporting → dispatcher alert. Pattern reusable; message intents need rewriting. |

## Meta-installers, demo data & migration tooling

| Module | Size (py/xml) | Classification | Proposed name | Rationale |
|--------|---------------|-----------------|---------------|-----------|
| `security_suite` | 72 / 0 | **Remove, replace** | `deployfleet_suite` (new module, written fresh once the module list is final) | Pure dependency list referencing all 34 security modules by name. Cannot be "kept" — has to be rewritten once the final module list exists. Zero logic to carry forward. |
| `security_demo_data` | 1,694 / 0 | **Remove** | — | Post-install hook seeding guard/site/shift demo records for Namibia. Entirely guard-industry content; a Zambia trucking demo dataset is a new deliverable, not a refactor. |
| `security_demo_data_zm` | 1,253 / 0 | **Remove** | — | Same as above for Zambia guard demo data. Replace with new Zambia *trucking* demo data (fleet, routes, drivers, trips) written from scratch once models exist. |
| `security_demo_site` | 518 / 1,052 | **Remove, replace** | `deployfleet_demo_site` (new) | Demo login panel/account management referencing `security_theme`/`security_suite`. Rebuild thin wrapper once those are renamed. |
| `security_demo_zambia_site` | 66 / 0 | **Remove, replace** | — | Meta-module listing all 39 security modules for the Alibaba Cloud Zambia demo deployment. Rewrite once the DeployFleet module list is final — no content to carry over besides the *idea* of "one meta-module per demo environment." |
| `security_dogforce_data` | **71,419** / 0 | **Remove — do not fork** | — | Loads a real client's actual company data from XLSX via a post-init hook. This is client-specific production data, not reusable architecture, and should not exist in a new commercial product's codebase in any form — including as a reference implementation. See [06-risks-and-recommendations.md](06-risks-and-recommendations.md). |
| `security_dogforce_migration` | 432 / 180 | **Remove** | — | CSV import tooling scoped specifically to migrating guards/clients/leave/loans *from DogForce's legacy system*. If DeployFleet later needs a generic data-import wizard, design one against the new models — this module's field mappings are meaningless outside DogForce's specific migration. |

---

## Summary counts

| Classification | Count | Modules |
|---|---|---|
| Keep unchanged (package rename only, zero logic change) | 7 | `security_backup_vault`, `security_l10n_zm`, `security_l10n_na`, `security_leave`, `security_loans`, `security_accounting_controls`, `security_notifications` |
| Keep + rename (views/dashboards rebuilt against renamed models, no logic change) | 8 | `security_licensing`, `security_theme`, `security_help`, `security_tour`, `security_discipline`, `security_discipline_payroll`, `security_reconciliation_core`, `security_reporting` |
| Keep + heavy refactor (engine reusable, domain surface redesigned) | 20 | `security_base`, `security_shift_planner`, `security_attendance`, `security_compliance_roster`, `security_client_onboarding`, `security_operations_crm`, `security_fleet_ops`, `security_equipment_payroll`, `security_documents`, `security_billing`, `security_client_reports`, `security_billing_account`, `security_billing_crm`, `security_billing_sale`, `security_reconciliation_billing_account`, `security_zra_invoice`, `security_mobile`, `security_mobile_bridge`, `security_portal`, `security_ai_engine`, `security_ai_whatsapp_bridge` |
| Split | 3 → 8 new modules | `security_operations` → 2, `security_fleet` → 4 (incl. new `fleet_workshop`), `security_equipment` → 2 |
| Remove, replace with fresh module | 1 | `security_suite` → `deployfleet_suite` (rewritten once module list is final) |
| Remove, no replacement in scope | 6 | `security_demo_data`, `security_demo_data_zm`, `security_demo_site`, `security_demo_zambia_site`, `security_dogforce_data`, `security_dogforce_migration` |
| Net-new (no DeployGuard source, seeded from analogous patterns) | 3 | `fleet_preventive_maintenance`, `fleet_breakdown_management`, `fleet_insurance_tracking` |

Note the refactor count (20) is one row longer than the audit table above because `security_ai_whatsapp_bridge` belongs there — this table is the authoritative count; treat the narrative tables above it as the reasoning, this one as the tally.

Net result: **45 source modules → roughly 43 DeployFleet modules** (7 removed outright or rewritten from zero, 8 new modules from splits, 3 entirely new). See [04-module-structure.md](04-module-structure.md) for the finalized list and dependency graph.
