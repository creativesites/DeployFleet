# 05 — Phased Implementation Roadmap

*Revision 2 — replaces the original 7-phase sequence with the 5-phase order from architecture review (Operational Foundation → Cost Control → Compliance → Customer Platform → Intelligence), which is a clearer story to sell internally and to a first customer than the earlier phase split. Phase 0 (foundation decisions) is kept as an explicit prerequisite gate, since none of the 5 phases below should start before it's resolved. Module names updated to `deployfleet_*`. Revision 3 — Phase 0 now includes building `deployfleet_ai_core`'s foundation alongside the event bus, and Phase 5 is updated per the dedicated AI architecture in [08-ai-architecture.md](08-ai-architecture.md).*

## Phase 0 — Foundation decisions & repo scaffolding

**Goal:** resolve the decisions every other module depends on, so later phases aren't rework.

- Confirm the vehicle-delegation decision in [03-refactoring-roadmap.md](03-refactoring-roadmap.md) §A.2 (`deployfleet.vehicle` via `_inherits` over `fleet.vehicle`) — the highest-leverage decision in the whole plan.
- Confirm Odoo edition target (Community vs. Enterprise).
- Scaffold the repo: CI (Odoo `--test-enable`, mobile typecheck), linters, `mobile/package-lock.json` committed from the first mobile commit, Docker Compose dev stack.
- Build `deployfleet_core` (identity, shared mixins) and `deployfleet_security` (role groups + licensing).
- Build `deployfleet_event_bus` as its generalized, subscriber-registry form (not the source's hardcoded if-chain) — see [02-reuse-strategy.md](02-reuse-strategy.md) §0 and [03-refactoring-roadmap.md](03-refactoring-roadmap.md). Every module from Phase 1 onward should publish onto it from the start.
- Build `deployfleet_ai_core`'s foundation (provider router with DeepSeek added, config/feature-toggle model, caching, usage tracking) — per [08-ai-architecture.md](08-ai-architecture.md) §0 and §11, roughly 70% of this already exists in the DeployGuard source, so it's cheap to build now rather than wait for Phase 5. The genuinely new AI pieces (`deployfleet_ai_permissions`, `deployfleet_ai_actions`) still wait for their respective later phases — this is specifically about not re-deferring the *foundation* the way the event bus wasn't re-deferred.

**Exit criteria:** a running Odoo instance with `deployfleet_core`/`deployfleet_security`/`deployfleet_event_bus`/`deployfleet_ai_core` installed, one test company, CI green on an empty test suite, and the vehicle-delegation decision written down as an ADR.

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

## Phase 2 — Cost Control ✅ delivered

**Goal:** save money. The first phase where the product visibly pays for itself beyond "replacing a spreadsheet."

**Status: implemented.** All six core modules plus both recommended additions below are built, tested, lint-clean, and committed: `deployfleet_freight_calculator`, `deployfleet_load_expense`, `deployfleet_driver_advance`, `deployfleet_fuel`, `deployfleet_parts`, `deployfleet_tyres`, `deployfleet_workshop`, `deployfleet_maintenance`, `deployfleet_assets`, plus the `max_weight_kg`/`max_volume_m3`/`gross_vehicle_weight_kg`/`tare_weight_kg` patch to `deployfleet_vehicle` (bundled into one migration as recommended) and the weight-aware hard-disqualify this enabled in `deployfleet_dispatch`'s scoring engine.

**Modules:** `deployfleet_fuel`, `deployfleet_maintenance`, `deployfleet_tyres`, `deployfleet_parts`, `deployfleet_workshop`, `deployfleet_assets`.

- Fuel logs, consumption analytics, and the first real AI hook (Fleet Analyst agent, fuel-anomaly detection per [08-ai-architecture.md](08-ai-architecture.md) §6/§11) once there's enough trip/fuel data flowing from Phase 1 to make it useful — even a simple threshold rule is worth shipping before the predictive version lands in Phase 5.
- Parts before tyres before workshop, in that dependency order (parts are consumed by both tyre replacement and job cards).
- Preventive maintenance scheduling and workshop job cards, both riding on the same open→diagnose→repair→close state machine inherited from the source's equipment-damage pattern.
- Non-vehicle asset register (trailers, containers, tools, safety equipment) — independent of the vehicle/workshop chain, can be built in parallel.
- Add `max_weight_kg`/`max_volume_m3` to the already-shipped `deployfleet_vehicle`, per [12-ltl-freight-management-architecture.md](12-ltl-freight-management-architecture.md) §5 — a small, generically useful patch (weight-aware dispatch scoring) that doesn't need to wait for an LTL scheduling decision, even though the full LTL module itself is a later, separate call.

**Candidate addition, recommended for this phase**: `deployfleet_freight_calculator` (per [14-freight-calculator-engine.md](14-freight-calculator-engine.md)) — the calculation-rule engine plus calculators #1, #2, #5, #6, #7, #10 (profit, cost/km, break-even, fuel, trip time, tyre cost). Unlike everything else proposed in the freight-intelligence document set, it needs no historical trip/billing data and no AI, only `deployfleet_vehicle`/`deployfleet_route` (both shipped) plus company-configured parameters — it fits this phase's "product visibly pays for itself" goal directly and doubles as strong demo material for the incoming real customer. Bundle its `gross_vehicle_weight_kg`/`tare_weight_kg` vehicle-field addition (doc 14 §5) into the same migration as the `max_weight_kg`/`max_volume_m3` patch above rather than touching `deployfleet_vehicle` twice.

**Also recommended for this phase**: `deployfleet.load.expense` and `deployfleet.driver.advance` (per [15-load-sheet-architecture.md](15-load-sheet-architecture.md) §5–§7) — the actuals-tracking companion to `deployfleet_freight_calculator`'s estimates, and, per that document, the strongest standalone idea in the load-sheet proposal it reconciles. Same profile as doc 14: deterministic, no historical data or AI dependency. The advance model's payroll-deduction transition stays inert until `deployfleet_payroll` lands in Phase 3, same as `deployfleet_loans`.

**Exit criteria:** a job card can be opened from a maintenance-due alert, consume tracked parts, and close; fuel consumption per vehicle/route is visible and flags outliers.

---

## Phase 3 — Compliance

**Goal:** become mission-critical — the point where a customer can't easily go back to spreadsheets and paper trip sheets, because the platform is now where legal/safety liability is tracked and enforced, not just recorded.

**Modules:** `deployfleet_compliance`, `deployfleet_vehicle_compliance`, `deployfleet_dispatch_compliance`, `deployfleet_insurance`, `deployfleet_payroll` (with the country-pack decoupling fix implemented, not just planned), `deployfleet_l10n_zm`, `deployfleet_leave`, `deployfleet_loans`, `deployfleet_driver_performance`.

- Polymorphic document/expiry engine generalized correctly the first time — both driver documents (license, medical) and vehicle documents (registration, insurance, roadworthiness) build on the same base per [02-reuse-strategy.md](02-reuse-strategy.md) §1.
- Dispatch-blocking enforcement (`deployfleet_dispatch_compliance`) against expired documents, with the emergency-override + audit-trail pattern carried from `security_compliance_roster` — and driver rest-hour / consecutive-driving-day hard constraints added to `deployfleet_dispatch`'s scoring engine. Per [06-risks-and-recommendations.md](06-risks-and-recommendations.md) risk #3, this is core scope here, not a deferred nice-to-have, given the regulatory/safety stakes of trucking.
- Zambian payroll (NAPSA/NHIMA/WCF/PAYE) computed correctly from logged trips, loan/performance deductions applied.
- The Compliance Agent (read-only: expired documents, upcoming inspection/renewal alerts) goes live here too, per [08-ai-architecture.md](08-ai-architecture.md) §11 — this is analysis, not action; the agent can flag an expiring insurance policy, but `deployfleet_ai_actions`' approval pipeline (Phase 4) is what would let it draft or trigger a renewal action.

**Exit criteria:** a vehicle with expired insurance cannot be dispatched without a logged override; a driver assignment that violates rest-hour rules is flagged or blocked; a Zambian driver's payslip computes correctly.

---

## Phase 4 — Customer Platform

**Goal:** differentiate from spreadsheets, WhatsApp, and paper trip sheets — the customer-facing proof that this is a real operations platform, not just an internal tool.

**Modules:** `deployfleet_billing`, `deployfleet_accounting`, `deployfleet_zra`, `deployfleet_client_reports`, `deployfleet_customer_portal`, `deployfleet_mobile_dispatcher`, `deployfleet_mobile_customer`, `deployfleet_mobile_push_bridge`, `deployfleet_notifications` (fully wired as an event-bus subscriber), `deployfleet_ai_permissions`, `deployfleet_ai_actions`, `deployfleet_ai_whatsapp`.

- Rate cards per trip/tonnage/distance/lane; ZRA Smart Invoice wired to the renamed billing model — a legal requirement for the Zambia launch market, not optional.
- Customer portal: shipment status, active trips, proof-of-delivery — this is what makes DeployFleet visibly better than a WhatsApp group and a paper trip sheet.
- Dispatcher and customer mobile apps follow the driver app shipped in the MVP; push notifications wired end-to-end (dispatch alerts, breakdown reports) rather than left as the source's unwired device-token field.
- The AI approval pipeline (§5 of [08-ai-architecture.md](08-ai-architecture.md)) and per-role AI permission scoping (§9) ship here — this is genuinely new engineering, not a port, and it's what turns the read-only agents live since Phase 2–3 into action-capable ones (e.g., a WhatsApp-reported breakdown creating a real ticket). Treat the human-approval gate as non-negotiable scope, not something deferred under schedule pressure — see [08-ai-architecture.md](08-ai-architecture.md) §5.

**Exit criteria:** a completed trip generates an invoice automatically and submits successfully to ZRA VSDC in a test environment; a customer can see their shipment's live status; a dispatcher gets a push alert on a breakdown report; an AI-proposed action (e.g., a maintenance reminder) requires and receives explicit human approval before it writes anything, and that approval is visible in the audit log.

**Candidate addition, not yet scheduled**: `deployfleet_ltl_management` (per [12-ltl-freight-management-architecture.md](12-ltl-freight-management-architecture.md)) depends on `deployfleet_billing` landing here for its split-invoicing piece — the consolidation/multi-stop-trip pieces of that module have no such dependency and could land as early as Phase 2/3 if LTL demand shows up before Phase 4 does. Priority medium, per that document's own framing — schedule only once there's a real signal a customer needs LTL, not preemptively.

---

## Phase 5 — Intelligence

**Goal:** become the "smart logistics operating system" — differentiated *advanced* AI value, sequenced last because it needs Phases 1–4's real operational data to be useful rather than a demo running on seed data. Full design in [08-ai-architecture.md](08-ai-architecture.md); this phase is narrower than revision 2's version of it, because the AI *foundation* moved to Phase 0 and AI *operational analysis*/*automation* are now attached to Phases 2–4 below, per [08-ai-architecture.md](08-ai-architecture.md) §11's phase-mapping table.

**Modules:** the *advanced-intelligence* slice of `deployfleet_ai_agents` — predictive maintenance (ML-based failure forecasting, distinct from the rule-based scheduling `deployfleet_maintenance` already shipped in Phase 2), fuel/fraud anomaly detection, dispatch/route optimization, financial forecasting.

- These are enhancements layered onto agents whose *basic* read-only versions already went live earlier (Fleet Analyst and Maintenance Agent in Phase 2–3, per [08-ai-architecture.md](08-ai-architecture.md) §11) — Phase 5 is where they get genuinely predictive rather than just descriptive, once there's enough historical data across Phases 1–4 for a prediction to beat the rule-based baseline it's improving on.
- AI features should read from `deployfleet_event_bus` where practical (a stream of fuel, breakdown, and delivery events) rather than only batch-querying tables, so they benefit from the same real-time signal dispatch and notifications already use.

**Exit criteria:** at least one predictive (not just descriptive) AI feature is live against real (not seeded-only) operational data from a pilot customer, and demonstrably outperforming the rule-based baseline it augments.

---

### Where the rest of the AI architecture actually lands

Per [08-ai-architecture.md](08-ai-architecture.md) §11, the AI work is not all in this phase — most of it is threaded through the phases above:

| AI-track element | Actually lands in |
|---|---|
| `deployfleet_ai_core` foundation (provider router + DeepSeek, caching, usage tracking, basic chat) | **Phase 0**, not here |
| Fleet Analyst / Maintenance Agent read-only analysis, Compliance Agent alerts | **Phase 2–3** |
| `deployfleet_ai_permissions`, `deployfleet_ai_actions` (the approval pipeline), action-capable WhatsApp | **Phase 4** |
| Predictive maintenance, fuel/fraud anomaly detection, dispatch optimization, financial forecasting | **Phase 5** (this phase) |

---

## Beyond Phase 5 — regional expansion readiness

Not a numbered phase because it's not gated on Phase 5 completing — it's ongoing validation work that should start as early as Phase 0–1 and come due once a second market is actually being pursued:

- Activate `deployfleet_l10n_na` (dormant-but-ready per the Phase 3 decoupling work) as the first real test of "does adding a country actually just mean adding a data pack."
- GPS integration — deferred by the product vision, and correctly sequenced after trip/route models are stable, but the *integration contract* (what fields, what update frequency, what vendor/protocol) should be scoped early per [06-risks-and-recommendations.md](06-risks-and-recommendations.md), even if implementation waits, to avoid reworking `deployfleet_trip` later.
- Multi-company/multi-country hardening: record rules, billing, and payroll correctly scoped by company across a multi-country group.
- **Candidate Phase 6+, vision only, not yet scheduled**: [10-lead-intelligence-architecture.md](10-lead-intelligence-architecture.md) (AI-powered lead capture/sales automation), [11-dispatch-network-architecture.md](11-dispatch-network-architecture.md) (dispatch as a third-party/broker business model, distinct from the internal-fleet `deployfleet_dispatch` built in Phase 1), and [13-freight-intelligence-architecture.md](13-freight-intelligence-architecture.md) (rate/route/backhaul intelligence and an AI freight optimizer — the last of these specifically gated on `deployfleet_billing` and enough real trip history existing to make backhaul-probability predictions meaningful rather than a guess). All three are new commercial surface area or need real historical data this product doesn't have yet — evaluate only after Phases 1–5 are proven with the real customer already onboarding, per each document's own sequencing note.

---

## Cross-cutting, ongoing across all phases

- `deployfleet_suite` and demo data (`deployfleet_demo_data_zm`) are living documents — update at the end of each phase, not once at the very end.
- Keep CI green and `mobile/package-lock.json` current on every phase that touches the mobile app.
- New country pack, new deduction type, new mobile screen, new event type: follow the extension-point patterns catalogued in the source `ARCHITECTURE.md` §11 — inherited unchanged, good Odoo practice independent of the security-guard domain.
- Re-validate the domain model in [07-domain-model-erd.md](07-domain-model-erd.md) against real trucking-company workflows (spot loads, backhauls, owner-operator vs. company-owned trucks) before Phase 1 schema is treated as frozen — see [06-risks-and-recommendations.md](06-risks-and-recommendations.md) risk #4. This is cheap to do now and expensive to fix once Phases 2–4 are built on top of an unvalidated shipment/dispatch schema.
