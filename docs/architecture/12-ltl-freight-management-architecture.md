# 12 — LTL & Freight Management Architecture

**Status: designed, not yet implemented. Candidate Phase 2/3 module, priority medium** — per the proposal this document is based on, this is nearer-term than the vision docs in [10](10-lead-intelligence-architecture.md)/[11](11-dispatch-network-architecture.md), but still not committed scope until it's explicitly scheduled. Do not start implementation before this is confirmed against Phase 1's real-world usage — the reasoning in §2 below is exactly the kind of judgment call [06-risks-and-recommendations.md](06-risks-and-recommendations.md) risk #5 warned would need real dispatch conversations, not just design-doc reasoning.

**Binding architectural principle, stated in the proposal and adopted as-is**: LTL is an optional execution mode, not the foundation. The foundation supports freight movement generally; FTL and LTL are two ways of filling a trip, not two different products. A small trucking company that only ever runs FTL should never see LTL menus, and should pay no complexity cost for a capability it doesn't use.

## 1. Configuration toggle

A company-level settings toggle, following the same pattern as `deployfleet_security`'s license settings integration (`res.config.settings` extension, already shipped):

```
Logistics Services
[x] Full Truckload
[x] Less Than Truckload
[ ] Freight Brokerage       (see docs/architecture/11-dispatch-network-architecture.md)
[ ] Warehouse Operations    (not yet designed anywhere)
```

Disabling LTL hides the consolidation board, LTL-specific menus, and LTL billing splits — it does not remove data or block a company from re-enabling it later. Implemented as a `deployfleet.logistics.service.config` model (one record per company), checked by menu `groups`/`invisible` conditions the same way `deployfleet_ai_core`'s feature toggles gate AI features.

## 2. Reconciling this proposal against what Phase 1 already shipped — read this before designing new models

The proposal's general chain is:

```
Customer → Freight Order → Shipment → Load Assignment → Trip → Vehicle
```

Phase 1 already shipped:

```
Customer → deployfleet.shipment → deployfleet.dispatch.assignment → deployfleet.trip → deployfleet.delivery
```

These are not two different layers that both need to exist — **`deployfleet.shipment` already is the proposal's "Freight Order"**: one customer, one cargo description, one pickup/dropoff, created before any truck is involved. Introducing a separate "Freight Order" model above it would duplicate an already-shipped, tested, committed model for no benefit. **Recommendation: keep `deployfleet.shipment` as the single commercial-request entity; do not rename it or split it.**

Where real, useful new design is needed is between shipment and trip — the proposal's "Load Assignment" concept — and here Phase 1's schema is a genuine mix of "already handles this" and "does not yet handle this":

| Capability the proposal needs | Already shipped in Phase 1? | Detail |
|---|---|---|
| A trip can carry multiple shipments (consolidated cargo) | **Yes, the data shape already exists** | `deployfleet.trip.shipment.line` is a many-to-many join between trip and shipment, built in Phase 1 specifically anticipating this — see [07-domain-model-erd.md](07-domain-model-erd.md) §3: *"a single trip can carry multiple shipments (consolidated/mixed cargo for different customers)."* This was designed in before LTL was ever discussed. |
| Each shipment sharing a trip tracks its own status independently | **Yes, already shipped** | `deployfleet.shipment.state` is per-shipment, and `deployfleet.delivery` is keyed to (trip, shipment) specifically so "a multi-drop trip carrying several shipments produces one delivery per drop, each with its own POD" (already in the Phase 1 model's docstring). |
| Billing should be per-shipment, not per-truck/trip | **Architecturally already set up for this** | `deployfleet_billing` (Phase 4, not yet built) was always going to bill against `deployfleet.shipment`/`deployfleet.contract`, never against `deployfleet.vehicle` or `deployfleet.trip` directly — see [04-module-structure.md](04-module-structure.md). Splitting one trip's revenue across three customers' shipments is the natural shape once billing exists, not a retrofit. |
| **Building a consolidated load *before* committing to a specific truck** — i.e., a dispatcher picks 3 compatible shipments, watches running capacity utilization, *then* assigns a vehicle | **No — genuine gap** | `deployfleet.dispatch.assignment.shipment_id` is a single `Many2one` (one assignment ↔ one shipment). There is no model today representing "these N shipments are being planned together, before a truck is chosen." |
| **A trip created from a consolidated load, instead of one trip per confirmed assignment** | **No — genuine gap** | `deployfleet_trip._handle_bus_event()` creates a brand-new trip every time *any* `deployfleet.dispatch.assigned` event fires — it never checks whether a compatible trip already exists to attach to. Today, confirming three separate assignments produces three separate trips, not one consolidated trip with three shipment lines, even though the trip model itself could hold all three. |
| **Multi-stop trip sequencing** (pickup A → pickup B → deliver A → deliver B, in a specific order) | **No — genuine gap** | `deployfleet.route.stop` exists, but it describes a named, reusable route's geographic waypoints — it has no concept of *which shipment* is picked up or dropped at a stop, or of a trip-specific stop sequence that varies per consolidated load. A new `deployfleet.trip.stop` model is needed (see §4). |
| **Vehicle capacity (weight/volume/pallets) to check against allocated load** | **No — genuine gap** | `deployfleet.vehicle` has no capacity fields at all today. |

**This is the real design work `deployfleet_ltl_management` does — not reinventing the shipment→trip chain, but filling these five specific gaps.**

## 3. New entity: `deployfleet.consolidated.load`

The proposal's "Load Assignment," given a name that doesn't collide with the existing `deployfleet.dispatch.assignment`:

| Field | Purpose |
|---|---|
| `vehicle_id` | The truck being loaded (once chosen — nullable while still in planning) |
| `driver_id` | Same |
| `route_id` | Optional, same as `deployfleet.dispatch.assignment` |
| `shipment_ids` | Many2many to `deployfleet.shipment` — the shipments being consolidated |
| `allocated_weight_kg` / `allocated_volume_m3` | Computed sum across `shipment_ids` |
| `state` | `planning` → `confirmed` → `dispatched` |

`action_confirm()` on a consolidated load is what actually creates (or attaches to) the `deployfleet.trip` and `deployfleet.trip.shipment.line` records — reusing those Phase 1 models exactly as they are, per §2's finding that the trip-side data shape was already correct.

**FTL stays a thin special case, not a separate code path**: an FTL shipment is a `deployfleet.consolidated.load` with exactly one shipment in `shipment_ids`. The existing `deployfleet.dispatch.assignment` (Phase 1's scoring-based single-shipment assignment) continues to serve FTL exactly as it does today — `deployfleet_ltl_management` does not touch or replace it. A company with LTL disabled never sees `deployfleet.consolidated.load` at all; it keeps using `deployfleet.dispatch.assignment` exactly as shipped.

## 4. Multi-stop trips: `deployfleet.trip.stop`

| Field | Purpose |
|---|---|
| `trip_id` | Required |
| `sequence` | Stop order |
| `depot_id` | Where (reuses `deployfleet.depot`, same as `deployfleet.route.stop`) |
| `stop_type` | `pickup` / `delivery` |
| `shipment_id` | Which shipment this stop is for |

```
Trip stops for a 3-shipment consolidated load:
  1. Lusaka Depot         (start)
  2. Pickup — ABC Hardware
  3. Pickup — XYZ Mining
  4. Deliver — ABC Hardware (Ndola)
  5. Deliver — XYZ Mining (Kitwe)
  6. Copperbelt Depot      (end)
```

An FTL trip simply has two stops (pickup, delivery) or none at all if `pickup_depot_id`/`dropoff_depot_id` on the shipment are sufficient — `deployfleet.trip.stop` is additive, not a required field for every trip.

## 5. Capacity — partly a generic vehicle concern, not only an LTL one

The proposal frames capacity tracking as an LTL feature. On reflection, **weight capacity is useful for FTL too** — Phase 1's dispatch scoring function ([09-dispatch-module-design.md](09-dispatch-module-design.md) §4) currently has no way to check whether a shipment's weight exceeds a candidate vehicle's limit at all. Recommendation, splitting this cleanly:

- **`deployfleet_vehicle` (already shipped) gets two new generic fields** in a small follow-up patch: `max_weight_kg`, `max_volume_m3`. Useful immediately for FTL scoring (a hard-disqualify if `shipment.weight_kg > vehicle.max_weight_kg`, extending the existing disqualify mechanism in `_score_candidate`), not gated behind the LTL toggle.
- **`deployfleet_ltl_management` adds the allocation/utilization tracking** on top — `deployfleet.consolidated.load.allocated_weight_kg` computed against the chosen vehicle's `max_weight_kg`, pallets/packages as LTL-specific refinements the generic vehicle fields don't need.

This is a better module boundary than the original proposal's — it means Phase 1's dispatch scoring gets a real improvement (weight-aware disqualification) years before any customer needs LTL, instead of that fix being locked behind a feature most early customers won't use yet.

**Forward reference**: [14-freight-calculator-engine.md](14-freight-calculator-engine.md) §5 extends this same vehicle-fields patch with `gross_vehicle_weight_kg`/`tare_weight_kg` for its Weight & Payload Calculator — bundle both additions into one migration rather than touching `deployfleet_vehicle` twice.

## 6. AI features — agent capabilities, not new AI plumbing

Per the established pattern ([08-ai-architecture.md](08-ai-architecture.md) §6, reaffirmed in [10](10-lead-intelligence-architecture.md)/[11](11-dispatch-network-architecture.md)): no new provider router, cache, or permission model. These are capabilities added to existing agents.

| Capability | Agent | Approval requirement |
|---|---|---|
| "Optimize available shipments" → suggest a consolidated load with utilization % and fuel-saving estimate | Dispatch Agent | Recommendation only, no gate — *creating* the consolidated load from the suggestion is a write, and goes through the same human-confirms step `deployfleet.consolidated.load.action_confirm()` already requires of a dispatcher regardless of whether AI or a human proposed the grouping |
| Pricing suggestion (market estimate vs. minimum profitable rate) | Finance Agent | Recommendation only — no AI-set price is ever sent to a customer without a human confirming it, same rule as every other agent, no exception for pricing |
| Delay prediction ("Trip 203 likely delayed — reasons: driver route history, weather, border congestion") | Dispatch Agent | Recommendation only, naturally — a prediction isn't a write |

## 7. Module

| Module | Depends | Purpose |
|---|---|---|
| `deployfleet_ltl_management` | `deployfleet_dispatch`, `deployfleet_trip`, `deployfleet_vehicle`, `deployfleet_billing` (Phase 4) | `deployfleet.consolidated.load`, `deployfleet.trip.stop`, the consolidation board, LTL-specific billing splits, the logistics-services config toggle |

Correcting two names from the original proposal against what's actually been built: the dependency is `deployfleet_vehicle` (shipped in Phase 1), not `deployfleet_vehicle_registry` (an earlier-revision name from [04-module-structure.md](04-module-structure.md) that was superseded before implementation — see that document's revision history). There is no `deployfleet_freight_management` module to depend on, because the "general freight movement foundation" the proposal describes is exactly what `deployfleet_dispatch` + `deployfleet_trip` already are, per §2 — inventing a module for the foundation the product already has would just be a rename with no new content, the same anti-pattern flagged in [01-module-audit.md](01-module-audit.md) for `deployfleet_hr`.

## 8. Future evolution — this is the same idea as an already-written document

The proposal's "later this can expand into `deployfleet_freight_network`, with external carriers, a freight marketplace, broker mode, public load board, carrier bidding" **is not a third vision to track — it's [11-dispatch-network-architecture.md](11-dispatch-network-architecture.md)**, written up already. Consolidating multiple customers' shipments onto a company's own truck (this document) and matching a shipment to an external carrier's truck (document 11) are adjacent ideas, but LTL consolidation doesn't require external carriers to exist first, and shouldn't be gated on that larger, more speculative vision landing.

## 9. Roadmap placement

Per the proposal's own framing: **candidate Phase 2/3 module, priority medium** — not every trucking company needs LTL, but for those that do it's a real competitive advantage. Concretely:

- Depends on `deployfleet_billing` (Phase 4) for the split-invoicing piece in §2, so full LTL billing can't land before Phase 4 regardless of when the consolidation/trip-planning pieces (§3–§4) are built.
- The vehicle capacity fields in §5 have no such dependency — they can land as a small Phase 2 (Cost Control) addition to the already-shipped `deployfleet_vehicle`, independent of the rest of this module, and should not wait for an LTL scheduling decision.
- Do not schedule `deployfleet_ltl_management` itself until there's a real signal (from the customer already onboarding, or the next one) that LTL is actually needed — this document exists so the design is ready when that signal arrives, not to argue the signal exists yet.
