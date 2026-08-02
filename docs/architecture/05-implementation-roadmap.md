# 05 — Phased Implementation Roadmap

Sequenced so that every phase produces something demoable and nothing later depends on an unstable earlier decision. **No phase below should start until the architecture in [04-module-structure.md](04-module-structure.md) is agreed** — this roadmap assumes that agreement has happened.

## Phase 0 — Foundation decisions & repo scaffolding

**Goal:** resolve the decisions that every other module depends on, so later phases aren't rework.

- Confirm the vehicle-model decision from [03-refactoring-roadmap.md](03-refactoring-roadmap.md) §A.1 (extend Odoo core `fleet.vehicle` vs. standalone `dfleet.vehicle`) — this is the single highest-leverage decision in the whole plan; get it wrong and `fleet_vehicle_registry`, `fleet_fuel_management`, and `fleet_workshop` all need rework later.
- Confirm Odoo edition target (Community vs. Enterprise) — affects whether `fleet_billing_account`'s GL bridge is core-scope or optional, and whether native Fleet app features assumed in Phase 0 are actually available at the Community tier (verify — some Fleet app niceties are Enterprise-only).
- Scaffold the repo: CI (GitHub Actions — Odoo `--test-enable`, mobile typecheck), linters (`ruff`/`pylint-odoo`, ESLint), `mobile/package-lock.json` committed from the first mobile-touching commit, Docker Compose dev stack (mirroring the source's `deploy/docker-compose.yml`, updated to whatever Odoo version is targeted).
- Build `fleet_base`: driver profile fields, license classes, qualifications, role groups (`group_fleet_driver` → `..._dispatcher` → `..._manager` → `..._owner`, plus HR/Payroll Officer and Auditor).
- Build minimal `deployfleet_licensing` and `deployfleet_theme` (even a stub) — every later module's manifest and login screen benefits from these existing early, and they carry over from the source with the least risk.

**Exit criteria:** a running Odoo instance with `fleet_base` installed, one test company, one test driver record, CI green on an empty test suite, and the vehicle-model decision written down as an ADR (Architecture Decision Record — the source repo's `docs/adr/` pattern is worth carrying forward for exactly this kind of decision).

## Phase 1 — Core Dispatch MVP

**Goal:** the walking skeleton. A dispatcher can plan a route, assign a driver and vehicle to a trip, and see it through to a logged actual trip. This is the demo that proves the fork thesis — "the fleet module was already 80% of a real product."

**Modules:** `fleet_operations`, `fleet_dispatch`, `fleet_dispatch_planner`, `fleet_vehicle_registry`, `fleet_route_planning`, `fleet_trip_management`, `fleet_trip_execution`.

- Client/contract/depot data model (`fleet_operations`) — direct descendant of `security_operations`'s client/site layer, least risky part of the whole Phase 1 remodel.
- Trip requirement → dispatch batch → trip assignment (`fleet_dispatch`) — the core remodel effort flagged in the audit; budget real design time here, this is not a rename.
- Dispatch Board OWL client (`fleet_dispatch_planner`) — port the Roster Board's interaction model (drag-drop, constraint highlighting) against the new trip-assignment domain.
- Vehicle registry extending `fleet.vehicle` (or standalone, per the Phase 0 decision), routes/stops, trip records with planned-vs-actual tracking (`fleet_trip_execution` — direct descendant of `security_attendance`'s scheduled-vs-actual pattern).

**Exit criteria:** dispatcher creates a route, generates a trip requirement, assigns driver + vehicle via the Dispatch Board, trip executes, actual departure/arrival/odometer logged. Demoable end-to-end without payroll, billing, or mobile yet.

## Phase 2 — Workshop, maintenance & compliance

**Goal:** the differentiated "operations platform" features the vision calls out by name — this is where DeployFleet stops looking like "DeployGuard with different labels" and starts looking like a trucking product.

**Modules:** `fleet_fuel_management`, `fleet_inspection`, `fleet_spare_parts`, `fleet_tyre_lifecycle`, `fleet_workshop`, `fleet_preventive_maintenance`, `fleet_breakdown_management`, `fleet_compliance_documents`, `fleet_compliance_dispatch`, `fleet_insurance_tracking`.

- Document/expiry engine (`fleet_compliance_documents`) generalized to the polymorphic driver-or-vehicle link described in [02-reuse-strategy.md](02-reuse-strategy.md) §1 — build this once, correctly, since both driver documents (license, medical) and vehicle documents (registration, insurance, roadworthiness) need it.
- Spare parts + tyre lifecycle + workshop job cards, in that dependency order (parts before workshop, since job cards consume parts).
- Preventive maintenance scheduling and breakdown management, both riding on the workshop job-card workflow.
- Compliance-dispatch bridge — block trip assignment against expired driver/vehicle documents, with the emergency-override + audit-trail pattern carried from `security_compliance_roster`.

**Exit criteria:** a vehicle with an expired inspection or insurance document cannot be dispatched without a logged override; a job card can be opened from a breakdown report, consume spare parts, and close; a preventive-maintenance reminder fires from odometer or calendar triggers.

## Phase 3 — HR & payroll (driver workforce)

**Goal:** drivers get paid correctly, and the multi-country payroll decoupling from [03-refactoring-roadmap.md](03-refactoring-roadmap.md) is implemented, not just planned.

**Modules:** `fleet_payroll_core` (with the `fleet_l10n_zm` dependency inversion fixed — see below), `fleet_l10n_zm`, `fleet_leave`, `fleet_loans`, `fleet_discipline`, `fleet_discipline_payroll_bridge`.

- Build `fleet_payroll_core` depending only on `fleet_operations`/`fleet_leave`/`hr` — verify at manifest-review time that no country pack is a dependency.
- `fleet_l10n_zm` ships Zambia statutory rules (NAPSA/NHIMA/WCF/PAYE) as data, not code, consistent with the source's "configuration over code" pattern.
- This phase is also where driver rest-hour / consecutive-driving-day hard constraints get added to `fleet_dispatch_planner` (deferred from Phase 1, tracked explicitly per [03-refactoring-roadmap.md](03-refactoring-roadmap.md) — these are a bigger deal in trucking than the equivalent guard-shift rest rules were in DeployGuard, so don't let this slip past Phase 3).

**Exit criteria:** a Zambian driver's payslip computes correctly from logged trips, with loan/discipline deductions applied; the Dispatch Board refuses (or flags) an assignment that violates rest-hour rules.

## Phase 4 — Billing & finance

**Goal:** the company gets paid.

**Modules:** `fleet_billing`, `fleet_accounting_controls`, `fleet_client_reports`, `fleet_zra_invoice`, `fleet_billing_account`, `fleet_billing_crm`, `fleet_billing_sale`, `fleet_reconciliation_core`, `fleet_reconciliation_billing_account`.

- Rate cards per trip/tonnage/distance/lane, replacing per-shift/per-post billing plans.
- ZRA Smart Invoice wired to the renamed billing invoice model — needed for legal compliance in the Zambia launch market, not optional.
- Standard Odoo CRM/Sales/Accounting bridges, following the source's `auto_install` bridge pattern.

**Exit criteria:** a completed trip generates an invoice line automatically; a Zambian invoice submits successfully to ZRA VSDC in a sandbox/test environment.

## Phase 5 — Mobile app & customer portal

**Goal:** field usability — the product stops being a back-office tool only.

**Modules:** `fleet_mobile_api`, `fleet_mobile_bridge`, `fleet_customer_portal`, plus the Expo mobile app rebuild.

- Rebuild mobile controllers role-by-role (driver, dispatcher, fleet manager, owner), fixing the field-name and role-detection debt items as they're rewritten (per [03-refactoring-roadmap.md](03-refactoring-roadmap.md) — don't reproduce them).
- Wire push notifications end-to-end (bring forward from the source's "planned but not implemented" list — dispatch alerts are more time-critical for this product than the source's use case).
- Customer portal: shipment status, active trips, proof-of-delivery.

**Exit criteria:** a driver can see and acknowledge an assigned trip on the mobile app; a dispatcher gets a push alert on a breakdown report; a customer can see their shipment's live status on the portal.

## Phase 6 — AI & automation

**Goal:** the differentiated intelligence layer, once there's enough real operational data flowing through Phases 1–5 for it to be useful (AI features on empty data are a demo, not a product).

**Modules:** `fleet_ai_engine`, `fleet_ai_whatsapp_bridge`.

- Port the provider-abstraction/config/cache/chat infrastructure verbatim.
- Reframe the 10 features per [02-reuse-strategy.md](02-reuse-strategy.md): fuel/fraud anomaly detection, driver risk scoring, freight billing audit, dispatch optimizer, trip-fill suggestions, breakdown/accident advisor, license/insurance-renewal nudges, performance review, payslip explanation, WhatsApp-based driver check-in and breakdown reporting.

**Exit criteria:** at least 3 of the 10 AI features are live against real (not seeded-only) operational data from a pilot customer.

## Phase 7 — Regional expansion readiness

**Goal:** prove the "expand to regional logistics operators" thesis without another rewrite.

- Activate `fleet_l10n_na` (already dormant-but-ready per the decoupling done in Phase 3) as the first test of "does adding a country actually just mean adding a data pack."
- GPS integration (explicitly deferred to this phase in the vision — correctly sequenced last, since it's an integration point that depends on trip/route models being stable).
- Multi-company hardening: verify record rules, billing, and payroll correctly scope by company across a multi-country group.

**Exit criteria:** a second country's payroll pack installs and runs correctly with zero changes to `fleet_payroll_core`; a pilot customer's GPS feed populates `fleet_trip_execution` actuals automatically instead of manual entry.

---

## Cross-cutting, ongoing across all phases

- `deployfleet_suite` and demo data (`deployfleet_demo_data_zm`) are living documents — update the meta-installer's dependency list and demo dataset at the end of each phase, not once at the very end.
- Every phase that touches the mobile app should update `mobile/package-lock.json` and keep CI green — this is cheap now, expensive to retrofit (per the source's own documented debt).
- Every new country pack, new deduction type, or new mobile screen should follow the extension-point patterns catalogued in the source `ARCHITECTURE.md` §11 (new country = new `l10n` pack depending on core; new deduction = model + `_inherit` on payslip; new mobile screen = controller + API module + Expo route) — these patterns are inherited unchanged and are good Odoo practice, not something specific to the security domain.
