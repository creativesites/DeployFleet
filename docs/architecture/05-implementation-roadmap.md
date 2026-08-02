# 05 — Phased Implementation Roadmap

*Revision 2 — replaces the original 7-phase sequence with the 5-phase order from architecture review (Operational Foundation → Cost Control → Compliance → Customer Platform → Intelligence), which is a clearer story to sell internally and to a first customer than the earlier phase split. Phase 0 (foundation decisions) is kept as an explicit prerequisite gate, since none of the 5 phases below should start before it's resolved. Module names updated to `deployfleet_*`.*

## Phase 0 — Foundation decisions & repo scaffolding

**Goal:** resolve the decisions every other module depends on, so later phases aren't rework.

- Confirm the vehicle-delegation decision in [03-refactoring-roadmap.md](03-refactoring-roadmap.md) §A.2 (`deployfleet.vehicle` via `_inherits` over `fleet.vehicle`) — the highest-leverage decision in the whole plan.
- Confirm Odoo edition target (Community vs. Enterprise).
- Scaffold the repo: CI (Odoo `--test-enable`, mobile typecheck), linters, `mobile/package-lock.json` committed from the first mobile commit, Docker Compose dev stack.
- Build `deployfleet_core` (identity, shared mixins) and `deployfleet_security` (role groups + licensing).
- Build `deployfleet_event_bus` as its generalized, subscriber-registry form (not the source's hardcoded if-chain) — see [02-reuse-strategy.md](02-reuse-strategy.md) §0 and [03-refactoring-roadmap.md](03-refactoring-roadmap.md). Every module from Phase 1 onward should publish onto it from the start.

**Exit criteria:** a running Odoo instance with `deployfleet_core`/`deployfleet_security`/`deployfleet_event_bus` installed, one test company, CI green on an empty test suite, and the vehicle-delegation decision written down as an ADR.

---

## Phase 1 — Operational Foundation

**Goal:** a company can run daily operations. This is the demo that proves the fork thesis and matches the MVP-12 core from [04-module-structure.md](04-module-structure.md).

**Modules:** `deployfleet_hr`, `deployfleet_driver`, `deployfleet_vehicle`, `deployfleet_customer`, `deployfleet_route`, `deployfleet_dispatch` (shipment/load modeled inline per the MVP packaging note), `deployfleet_trip`, `deployfleet_delivery`.

- Client/contract/depot data model (`deployfleet_customer`) — direct descendant of `security_operations`'s client/site layer, least risky part of this phase.
- Shipment/load fields (what, how much, pickup, drop-off, weight) and dispatch (trip requirement → dispatch batch → trip assignment) — the core domain-remodel effort; budget real design time here. See [07-domain-model-erd.md](07-domain-model-erd.md) for the entity model this phase builds against.
- Dispatch Board OWL client — port the Roster Board's interaction model (drag-drop, constraint highlighting) against the new trip-assignment domain.
- `deployfleet_vehicle` via delegation over `fleet.vehicle`; routes/stops; trip records with planned-vs-actual tracking (direct descendant of `security_attendance`'s scheduled-vs-actual pattern); delivery/POD as the trip's terminal state.
- Every state transition (dispatch created, trip departed, delivery completed) publishes onto `deployfleet_event_bus`.

**Exit criteria:** a dispatcher creates a shipment, generates a trip requirement, assigns driver + vehicle via the Dispatch Board, the trip executes, and a proof-of-delivery is captured. Demoable end-to-end without cost-control, compliance, billing, or mobile yet.

---

## Phase 2 — Cost Control

**Goal:** save money. The first phase where the product visibly pays for itself beyond "replacing a spreadsheet."

**Modules:** `deployfleet_fuel`, `deployfleet_maintenance`, `deployfleet_tyres`, `deployfleet_parts`, `deployfleet_workshop`, `deployfleet_assets`.

- Fuel logs, consumption analytics, and the first real AI hook (fuel-anomaly detection) once there's enough trip/fuel data flowing from Phase 1 to make it useful — even a simple threshold rule is worth shipping before the full AI engine lands in Phase 5.
- Parts before tyres before workshop, in that dependency order (parts are consumed by both tyre replacement and job cards).
- Preventive maintenance scheduling and workshop job cards, both riding on the same open→diagnose→repair→close state machine inherited from the source's equipment-damage pattern.
- Non-vehicle asset register (trailers, containers, tools, safety equipment) — independent of the vehicle/workshop chain, can be built in parallel.

**Exit criteria:** a job card can be opened from a maintenance-due alert, consume tracked parts, and close; fuel consumption per vehicle/route is visible and flags outliers.

---

## Phase 3 — Compliance

**Goal:** become mission-critical — the point where a customer can't easily go back to spreadsheets and paper trip sheets, because the platform is now where legal/safety liability is tracked and enforced, not just recorded.

**Modules:** `deployfleet_compliance`, `deployfleet_vehicle_compliance`, `deployfleet_dispatch_compliance`, `deployfleet_insurance`, `deployfleet_payroll` (with the country-pack decoupling fix implemented, not just planned), `deployfleet_l10n_zm`, `deployfleet_leave`, `deployfleet_loans`, `deployfleet_driver_performance`.

- Polymorphic document/expiry engine generalized correctly the first time — both driver documents (license, medical) and vehicle documents (registration, insurance, roadworthiness) build on the same base per [02-reuse-strategy.md](02-reuse-strategy.md) §1.
- Dispatch-blocking enforcement (`deployfleet_dispatch_compliance`) against expired documents, with the emergency-override + audit-trail pattern carried from `security_compliance_roster` — and driver rest-hour / consecutive-driving-day hard constraints added to `deployfleet_dispatch`'s scoring engine. Per [06-risks-and-recommendations.md](06-risks-and-recommendations.md) risk #3, this is core scope here, not a deferred nice-to-have, given the regulatory/safety stakes of trucking.
- Zambian payroll (NAPSA/NHIMA/WCF/PAYE) computed correctly from logged trips, loan/performance deductions applied.

**Exit criteria:** a vehicle with expired insurance cannot be dispatched without a logged override; a driver assignment that violates rest-hour rules is flagged or blocked; a Zambian driver's payslip computes correctly.

---

## Phase 4 — Customer Platform

**Goal:** differentiate from spreadsheets, WhatsApp, and paper trip sheets — the customer-facing proof that this is a real operations platform, not just an internal tool.

**Modules:** `deployfleet_billing`, `deployfleet_accounting`, `deployfleet_zra`, `deployfleet_client_reports`, `deployfleet_customer_portal`, `deployfleet_mobile_dispatcher`, `deployfleet_mobile_customer`, `deployfleet_mobile_push_bridge`, `deployfleet_notifications` (fully wired as an event-bus subscriber).

- Rate cards per trip/tonnage/distance/lane; ZRA Smart Invoice wired to the renamed billing model — a legal requirement for the Zambia launch market, not optional.
- Customer portal: shipment status, active trips, proof-of-delivery — this is what makes DeployFleet visibly better than a WhatsApp group and a paper trip sheet.
- Dispatcher and customer mobile apps follow the driver app shipped in the MVP; push notifications wired end-to-end (dispatch alerts, breakdown reports) rather than left as the source's unwired device-token field.

**Exit criteria:** a completed trip generates an invoice automatically and submits successfully to ZRA VSDC in a test environment; a customer can see their shipment's live status; a dispatcher gets a push alert on a breakdown report.

---

## Phase 5 — Intelligence

**Goal:** become the "smart logistics operating system" — differentiated AI value, sequenced last because it needs Phases 1–4's real operational data to be useful rather than a demo running on seed data.

**Modules:** `deployfleet_ai`, `deployfleet_ai_whatsapp`.

- Port the provider-abstraction/config/cache/chat infrastructure verbatim; reframe the feature set per [02-reuse-strategy.md](02-reuse-strategy.md): fuel/fraud anomaly detection, predictive maintenance ("service likely required within 800km"), dispatch assistant (recommend truck X over truck Y with a stated reason), driver risk scoring, freight billing audit, payment-risk intelligence (late-paying customers), license/insurance-renewal nudges, driver performance review, payslip explanation, WhatsApp-based check-in and breakdown reporting.
- AI features should read from `deployfleet_event_bus` where practical (a stream of fuel, breakdown, and delivery events) rather than only batch-querying tables, so they benefit from the same real-time signal dispatch and notifications already use.

**Exit criteria:** at least 3 of the AI features are live against real (not seeded-only) operational data from a pilot customer.

---

## Beyond Phase 5 — regional expansion readiness

Not a numbered phase because it's not gated on Phase 5 completing — it's ongoing validation work that should start as early as Phase 0–1 and come due once a second market is actually being pursued:

- Activate `deployfleet_l10n_na` (dormant-but-ready per the Phase 3 decoupling work) as the first real test of "does adding a country actually just mean adding a data pack."
- GPS integration — deferred by the product vision, and correctly sequenced after trip/route models are stable, but the *integration contract* (what fields, what update frequency, what vendor/protocol) should be scoped early per [06-risks-and-recommendations.md](06-risks-and-recommendations.md), even if implementation waits, to avoid reworking `deployfleet_trip` later.
- Multi-company/multi-country hardening: record rules, billing, and payroll correctly scoped by company across a multi-country group.

---

## Cross-cutting, ongoing across all phases

- `deployfleet_suite` and demo data (`deployfleet_demo_data_zm`) are living documents — update at the end of each phase, not once at the very end.
- Keep CI green and `mobile/package-lock.json` current on every phase that touches the mobile app.
- New country pack, new deduction type, new mobile screen, new event type: follow the extension-point patterns catalogued in the source `ARCHITECTURE.md` §11 — inherited unchanged, good Odoo practice independent of the security-guard domain.
- Re-validate the domain model in [07-domain-model-erd.md](07-domain-model-erd.md) against real trucking-company workflows (spot loads, backhauls, owner-operator vs. company-owned trucks) before Phase 1 schema is treated as frozen — see [06-risks-and-recommendations.md](06-risks-and-recommendations.md) risk #4. This is cheap to do now and expensive to fix once Phases 2–4 are built on top of an unvalidated shipment/dispatch schema.
