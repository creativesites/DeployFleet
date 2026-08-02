# 11 — Dispatch Network Architecture (long-term vision, not current MVP scope)

**Status: vision, not committed scope.** Same framing as [10-lead-intelligence-architecture.md](10-lead-intelligence-architecture.md): this document exists for the record and future planning, and nothing in it should be implemented before the MVP (fleet foundation, drivers, trips, dispatch board, maintenance, billing, AI core) is proven with a real customer.

**This is a different, bigger idea than the `deployfleet_dispatch` module already built in Phase 1** — worth being precise about, since the naming overlaps. [09-dispatch-module-design.md](09-dispatch-module-design.md) and the shipped `deployfleet_dispatch` module handle **internal fleet dispatch**: a company's own trucks and employed drivers, matched to its own shipments. This document is about **dispatch as a business model in itself** — a company (or a mode of operating within a company) that does not own trucks, but finds loads and assigns them to trucks it doesn't own, for a commission. That's a materially different domain, not a bigger version of the same one.

## 1. Two dispatch models

| | Model A: Internal Fleet Dispatch | Model B: Third-Party Dispatch |
|---|---|---|
| Who owns the trucks | The company itself | External carriers/truck owners |
| What `deployfleet_dispatch` (Phase 1) already does | ✅ This, fully | Not this |
| Revenue | Freight revenue directly | Commission on load value |
| New entity needed | None — `deployfleet.vehicle`/`hr.employee` already model this | `deployfleet.carrier` (see §3) |

DeployFleet should support both, and a company operating in Model B still benefits from everything already built (shipments, routes, trips, deliveries, the event bus, AI core) — Model B is additive, not a fork of the existing dispatch module.

## 2. Why this connects directly to an already-flagged open question

[07-domain-model-erd.md](07-domain-model-erd.md) §3 flagged, as an explicit unmodeled gap: *"Owner-operator vs. company-owned vehicle is not yet modeled... If the target market has a meaningful mix of owner-operator trucks (common in regional logistics), this schema needs an `ownership_type` field and probably a different billing/payroll treatment."* This document is exactly the scenario where that gap stops being a hypothetical and becomes load-bearing: a dispatch-network business is *entirely* owner-operator/external-carrier trucks. If DeployFleet's second or third customer runs Model B, `deployfleet.vehicle`'s current assumption (a company-owned truck, a `hr.employee` driver on payroll) needs the ownership-type extension that document already anticipated, not a redesign from scratch.

## 3. Proposed entities (additive to the existing domain model)

| Entity | Purpose | Relationship to existing model |
|---|---|---|
| `deployfleet.carrier` | An external truck-owning business or independent owner-operator | New — a carrier's vehicles are NOT `deployfleet.vehicle` records owned by the dispatching company; they're the carrier's own assets, referenced not owned |
| `deployfleet.carrier.vehicle` | A vehicle the carrier makes available, with capacity/type/documents | Parallel to `deployfleet.vehicle`, not a subtype of it — a dispatch company doesn't manage a carrier's maintenance schedule the way it manages its own fleet |
| `deployfleet.dispatch.request` | A customer's raw need before it's matched to a specific carrier | Sits above `deployfleet.shipment` in the funnel — a request becomes a shipment once a carrier is found, similar in spirit to a CRM opportunity becoming a confirmed order |
| `deployfleet.commission.rule` | How the dispatcher's cut is calculated per request/customer/carrier | New — see §5 |

The existing `deployfleet.shipment` → `deployfleet.dispatch.assignment` → `deployfleet.trip` → `deployfleet.delivery` chain still applies once a carrier and their vehicle/driver are matched — the difference is *who* fills the vehicle_id/driver_id-equivalent slots, not the workflow shape.

## 4. Illustrative workflow

```
Customer: "40 tonnes maize, Lusaka -> Ndola, 15 August"
        |
        v
deployfleet.dispatch.request created
        |
        v
Dispatcher searches available carrier vehicles
(location, capacity, rating, availability — same scoring-function
 shape as docs/architecture/09-dispatch-module-design.md §4, extended
 to carrier vehicles instead of only owned ones)
        |
        v
Assign: Carrier's Truck A + Driver James -> deployfleet.shipment + trip created
```

## 5. Financial model — commission, not just freight revenue

A dispatch-network business needs three-way money, not two-way:

```
Load value:            $5,000  (customer invoice)
Dispatcher commission:   10%
                        ------
Carrier payment:        $4,500
Dispatcher revenue:       $500
```

This extends `deployfleet_billing` (per [04-module-structure.md](04-module-structure.md)) rather than replacing it — the customer-facing invoice is the same `deployfleet.billing.invoice` machinery; what's new is a carrier-payment side and a commission-calculation rule, tracked in `deployfleet_dispatch_commissions`.

## 6. Broker/marketplace mode — furthest-out, not near-term

`deployfleet_load_board`: customers post a need ("truck needed, Lusaka → Kitwe, 30 tons copper"), available carriers respond. This is a two-sided marketplace, which is a fundamentally different product surface (matching, trust/rating, possibly payment escrow) from anything else in this document set — flagged explicitly as the piece to defer longest, and to treat as its own discovery-and-validation exercise (same rigor as [06-risks-and-recommendations.md](06-risks-and-recommendations.md) risk #5 demanded for the core domain model) rather than build speculatively.

## 7. Proposed modules

| Module | Purpose |
|---|---|
| `deployfleet_dispatch_core` | `deployfleet.dispatch.request`, extended scoring against carrier vehicles as well as owned ones |
| `deployfleet_dispatch_board` | The dispatcher-facing UI — likely where the custom OWL board deferred in [09-dispatch-module-design.md](09-dispatch-module-design.md) §1 finally gets built, once both internal and carrier dispatch justify the investment |
| `deployfleet_dispatch_ai` | The Dispatch Agent's network-aware capabilities — see §8 |
| `deployfleet_carrier_management` | Carrier onboarding, agreements, ratings, documents/insurance/compliance (reuses `deployfleet_compliance`'s expiry-tracking engine, per [02-reuse-strategy.md](02-reuse-strategy.md) §1, applied to a carrier's vehicles instead of only owned ones) |
| `deployfleet_load_board` | The marketplace mode — furthest out, per §6 |
| `deployfleet_dispatch_commissions` | The three-way financial split in §5 |

## 8. The Dispatch Agent — extending, not duplicating, the existing catalog

[08-ai-architecture.md](08-ai-architecture.md) §6 already defines a Dispatch Agent for internal fleet assignment. This vision extends its capabilities for the network case rather than defining a second agent:

| Capability | Approval requirement |
|---|---|
| Recommend a truck/carrier assignment, with stated reasoning (distance, fuel cost, driver history, profit margin) | None — read-only recommendation |
| "Optimize tomorrow's dispatch schedule" (e.g., flag an assignment creating empty return-leg mileage) | None — recommendation |
| Create a trip, change a driver, cancel a dispatch | **Requires human approval**, via `deployfleet_ai_actions`, same rule as every other agent — no exception for the dispatch-network context, consistent with [06-risks-and-recommendations.md](06-risks-and-recommendations.md) risk #7 |

## 9. Sequencing

Not numbered into the 5-phase roadmap for the same reason as [10-lead-intelligence-architecture.md](10-lead-intelligence-architecture.md): this is additive commercial scope for a different kind of customer (a dispatch/brokerage business, not a fleet-owning trucking company), not a deepening of the operational core the current MVP customer needs first. If pursued, sequence `deployfleet_dispatch_core`/`deployfleet_carrier_management` (the data model and workflow) well before `deployfleet_dispatch_ai` (needs real assignment history to be worth building) and treat `deployfleet_load_board` as a separate future decision, not a natural next step from the rest.
