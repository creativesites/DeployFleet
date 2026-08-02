# 13 — Freight Intelligence Architecture (long-term vision, not current MVP scope)

**Status: vision, not committed scope.** Same framing as [10](10-lead-intelligence-architecture.md)/[11](11-dispatch-network-architecture.md): recorded for future planning, not to be implemented before the MVP proves out. Unlike [12-ltl-freight-management-architecture.md](12-ltl-freight-management-architecture.md) (candidate Phase 2/3), this genuinely needs to wait longer — most of what's valuable here (rate benchmarking, backhaul prediction, route/terrain intelligence) requires historical data DeployFleet doesn't have yet. Building it before there's real trip/rate history to learn from produces a demo, not a product — the same caution [08-ai-architecture.md](08-ai-architecture.md) §11 already applies to predictive maintenance and fuel-anomaly detection.

## 1. Before designing anything new: what this proposal duplicates vs. what's genuinely new

This proposal, read carefully against what's already documented and shipped, is about 60% a restatement of existing material and 40% genuinely new. Being precise about which is which matters more than transcribing the whole thing as if it were all new:

| Proposed module | What it actually is |
|---|---|
| `deployfleet_load_management` — the "Load" entity with structured origin/destination, cargo specifics, commercial rate fields | **An enrichment of the already-shipped `deployfleet.shipment`, not a new entity.** See §2 — this is the third time a proposal has re-described the same commercial-cargo-request concept under a new name (DeployGuard's roster→attendance chain, then "Freight Order" in [12](12-ltl-freight-management-architecture.md), now "Load"). Recommendation stands: one shipment entity, enriched, not a growing family of near-duplicate models. |
| `deployfleet_dispatch_marketplace` — carrier vs. broker business models, load board, available-trucks board | **Already fully documented in [11-dispatch-network-architecture.md](11-dispatch-network-architecture.md)** (Model A/B, `deployfleet.carrier`, `deployfleet_load_board`). This proposal's mockups (the "Profit Score" load-board card, the "Available Trucks" board with fuel level and estimated profit) are a useful concrete UI illustration of that document — folded into it (§7 there) rather than duplicated in a new document. |
| `deployfleet_dispatch_management` — dispatcher dashboard, assignment, trip creation | **Already `deployfleet_dispatch` + `deployfleet_trip`, shipped in Phase 1.** The "dispatcher dashboard" is the custom OWL board explicitly deferred past Phase 1 in [09-dispatch-module-design.md](09-dispatch-module-design.md) §1. |
| `deployfleet_rate_intelligence` | **Genuinely new** — §3 |
| `deployfleet_route_intelligence` | **Genuinely new** — §4 |
| `deployfleet_ai_freight_optimizer` | **Genuinely new capability, not new AI plumbing** — extends existing agents, §5–§6 |

The rest of this document only covers the genuinely new material.

## 2. The "Load" enrichment — extend `deployfleet.shipment`, don't replace it

Today's shipped model (`custom_addons/deployfleet_dispatch/models/deployfleet_shipment.py`): `customer_id`, `contract_id`, `cargo_description` (plain text), `weight_kg`, `pickup_depot_id`/`dropoff_depot_id`, `requested_pickup_date`, `required_vehicle_type_id`, `state`. The proposal wants materially richer cargo and commercial detail: structured origin/destination (country/province/city/GPS, not just a depot reference), pickup *windows* not just a single datetime, loading requirements and site restrictions, cargo classification (hazmat, temperature-controlled, dimensions, packaging), and commercial fields (offered rate, contract rate, spot rate, broker rate, historical average).

This is real, valuable enrichment — but it's a schema change to an already-shipped, tested, production-headed model, not greenfield design. Treat it as its own scoped effort when it's actually needed (a customer moving hazmat or temperature-controlled cargo, or one that needs GPS-precision pickup points beyond a named depot), not as part of this AI-focused document. When it happens: add fields to `deployfleet.shipment` directly (classical extension, the same pattern `deployfleet_driver` used on `hr.employee`), do not create a parallel `deployfleet.load` model that then needs reconciling with the shipment it's describing.

## 3. `deployfleet_rate_intelligence`

**Purpose:** the cost/profitability calculation the AI layer (§5) reasons over — this module is data and computation, the AI layer is judgment and recommendation on top of it.

| Model | Purpose |
|---|---|
| `deployfleet.rate.benchmark` | Historical average rate per lane (origin depot/region → destination depot/region), updated as real invoices/trips accumulate — the thing that lets the system say "market average for this lane is $4,200" instead of a guess |
| `deployfleet.cost.model` | Per-vehicle-type or per-company cost assumptions: fuel cost per km, driver cost per trip, maintenance allocation per km, insurance allocation per trip |

Core computation, the formula from the proposal, implemented directly rather than left as prose:

```
Trip Profit = Revenue − (Fuel + Tolls + Driver Cost + Maintenance Allocation + Insurance Allocation)
```

`Tolls` comes from `deployfleet_route_intelligence` (§4); everything else from `deployfleet.cost.model` and the shipment's offered rate. This computation is what the Finance Agent's rate/profitability recommendations (§5) call — the AI layer doesn't invent the arithmetic, it explains and contextualizes a number this module computes deterministically.

**Depends on:** `deployfleet_billing` (Phase 4) for real historical rate data to benchmark against — before that exists, `deployfleet.rate.benchmark` has nothing to learn from.

## 4. `deployfleet_route_intelligence`

**Purpose:** extends the already-shipped `deployfleet.route` with the trip-planning-relevant detail dispatch scoring and rate calculation need.

| Model | Purpose |
|---|---|
| Extension of `deployfleet.route` (`_inherit`, same non-invasive pattern used throughout this codebase) | `terrain_rating` (a simple difficulty score — paved highway vs. gravel/hill terrain), `border_crossing_ids` if applicable |
| `deployfleet.route.toll` | Per-country or per-segment toll cost on a route — the toll database the proposal describes |
| Weather — **explicitly not designed yet, correctly** | The proposal itself frames this as "future integration (weather APIs)." Agreed — this needs a third-party weather API decision (which provider, which countries covered) that's out of scope until the rest of this document is real. Do not build a bespoke weather model; integrate an API when this is prioritized. |

**Depends on:** `deployfleet_route` (shipped in Phase 1).

## 5. `deployfleet_ai_freight_optimizer` — capability additions to existing agents, not a new AI stack

Per the pattern established in [08-ai-architecture.md](08-ai-architecture.md) §6 and reaffirmed in every subsequent vision document: no new provider router, cache, permission model, or action-approval pipeline. Everything below is new *capability* (system prompts, data sources, recommendation logic) added to the **Dispatch Agent** and **Finance Agent** already in the catalog — not a seventh agent, and not new plumbing.

| Capability (from the proposal) | Agent | Reads from |
|---|---|---|
| Load scoring (profitability / market rate / backhaul probability / operational fit / risk, combined into an overall score) | Dispatch Agent + Finance Agent jointly | `deployfleet_rate_intelligence`, `deployfleet_route_intelligence`, trip/shipment history |
| Weight/capacity matching | Dispatch Agent | Already mostly solved deterministically, not by AI — see [12-ltl-freight-management-architecture.md](12-ltl-freight-management-architecture.md) §5's `max_weight_kg`/`max_volume_m3` fields and the existing hard-disqualify pattern in [09-dispatch-module-design.md](09-dispatch-module-design.md) §4. The AI layer explains *why* a match is good, it doesn't replace the hard disqualification rule that already exists. |
| Route/terrain/toll intelligence | Dispatch Agent | `deployfleet_route_intelligence` |
| **Backhaul intelligence** — the single most valuable capability in this whole proposal | Dispatch Agent | New: needs a `deployfleet.lane.backhaul.stat` model tracking, per lane, the historical probability of finding a return load and the average return rate, computed from real trip history. Cannot be built against seed data — needs months of real outbound/return trip records to be more accurate than a guess, which is exactly why this document is framed as "wait for real data," not "build now." |
| Market intelligence (current rate vs. historical average) | Finance Agent | `deployfleet.rate.benchmark` |
| Driver fit | Dispatch Agent | **Mostly already-shipped data** — `deployfleet_driver`'s `deployfleet_years_experience`, `deployfleet_qualified_vehicle_type_ids`, `deployfleet_risk_score`, `deployfleet_accident_count` (Phase 1) already carry most of what's needed; "previous routes on this lane" and "fatigue" need `deployfleet_driver_performance` (Phase 3) and trip history, not new AI plumbing |
| Vehicle fit / compliance (e.g., "truck unavailable — insurance expired") | Dispatch Agent | `deployfleet_compliance`/`deployfleet_vehicle_compliance` (Phase 3) — this is exactly [06-risks-and-recommendations.md](06-risks-and-recommendations.md) risk #3's compliance-blocking mechanism, already designed, not a new concept |
| **AI booking assistant** ("find me the best truck for this copper load leaving Kitwe next Monday") | Dispatch Agent | The existing "Ask AI" chat interface from [08-ai-architecture.md](08-ai-architecture.md) §4 — this is a UI/prompt-design exercise once the underlying scoring (all of the above) exists, not a new interaction paradigm |

**On DeepSeek specifically**: the proposal's own observation is correct and consistent with the resolved decision in [08-ai-architecture.md](08-ai-architecture.md) §2 — these workloads (classification, reasoning over structured data, recommendation, summarization) don't need the most expensive available model for every call. Route the routine load-scoring calls through the cheap tier and reserve the reasoning tier for the natural-language booking assistant and genuinely multi-factor recommendations, per the existing cheap/reasoning tier design — no new provider decision needed here.

## 6. The approval rule, once more, because this is the proposal's biggest liability surface

[06-risks-and-recommendations.md](06-risks-and-recommendations.md) risk #7 applies at full force: **"ACCEPT this load, expected profit $1,420" is a recommendation, never an autonomous booking.** A load-scoring AI that could also autonomously *commit* the company to a load — accepting a rate, promising a pickup window — is a direct financial commitment made without a human in the loop, the exact failure mode risk #7 exists to prevent. Every one of this document's recommendations (accept/reject a load, negotiate a rate, book a driver) surfaces through the existing `deployfleet_ai_actions` pipeline once that's built (Phase 4) — there is no proposed exception here, the same as every other agent in every other document.

## 7. Sequencing

Not numbered into the 5-phase roadmap, same as [10](10-lead-intelligence-architecture.md)/[11](11-dispatch-network-architecture.md) — this is candidate Phase 6+ work, and specifically gated on:

1. `deployfleet_billing` (Phase 4) existing, so `deployfleet.rate.benchmark` has real invoice history to learn from.
2. Enough real trip volume for `deployfleet.lane.backhaul.stat` to be predictive rather than a guess dressed up as a number — this is the single item in this document most likely to disappoint if built too early, since a confident-sounding 72% backhaul probability computed from five historical trips is worse than no prediction at all.
3. [11-dispatch-network-architecture.md](11-dispatch-network-architecture.md)'s carrier/marketplace model, if the business pursues Model B (third-party dispatch) — several of this document's scoring factors (available carrier trucks, not just owned ones) assume that exists.

Do not schedule this ahead of the operational core (Phases 1–5) proving out with the real customer already onboarding — the same standing instruction that applies to every vision document in this set.
