# 14 — Freight Calculator Engine

**Status: designed, candidate near-term implementation — not vision-only, unlike [10](10-lead-intelligence-architecture.md)/[11](11-dispatch-network-architecture.md)/[13](13-freight-intelligence-architecture.md).** This is a materially different proposal from those three: it needs no historical trip data, no second business model, and no AI to have standalone value — it's mostly deterministic arithmetic over company-configurable assumptions. Recommend treating it as the earliest-buildable of everything proposed so far. See §8 for the specific placement recommendation.

## 1. Purpose

Before accepting, pricing, dispatching, or negotiating a load, quickly answer: what does this actually cost, and is it profitable? Per the proposal's own framing, this is also the strongest demo asset discussed in this document set — "before you accept any load, DeployFleet tells you whether you're making money" is a sharper sales pitch than "we manage your fleet," and it's deliverable without waiting on AI, historical data, or a second business model to exist first.

## 2. This is not a fourth new cost concept — it's the concrete version of something already sketched abstractly

[13-freight-intelligence-architecture.md](13-freight-intelligence-architecture.md) §3 already proposed a `deployfleet.cost.model` and the formula `Trip Profit = Revenue − (Fuel + Tolls + Driver Cost + Maintenance Allocation + Insurance Allocation)`, described in one paragraph as input to an AI layer. This proposal is the full, immediately-buildable specification of exactly that engine, plus depreciation (a real cost the earlier sketch missed) and several standalone calculators beyond the core profit formula.

**Recommendation: this module supersedes doc 13 §3's `deployfleet.cost.model` sketch.** `deployfleet_rate_intelligence` (doc 13) keeps its own job — historical market-rate benchmarking (`deployfleet.rate.benchmark`) — but stops needing its own cost model; it consumes this module's calculation engine instead of defining a second one. Doc 13 is amended accordingly (see its revision note). This is exactly the kind of consolidation this document set exists to catch — two documents quietly maintaining overlapping formulas would drift out of sync the first time one gets updated and the other doesn't.

## 3. The core architectural decision: a rule engine, not hardcoded formulas — and this is the right call

The proposal's own instinct here is correct and worth implementing exactly as suggested, not simplified away: hardcoding "fuel cost = (distance / consumption) × price" directly in Python means every company's different fuel assumptions, driver-pay model (daily wage vs. trip allowance vs. percentage), and maintenance-reserve rate requires a code change. A rule engine makes these company-configurable data instead.

```python
class DeployfleetCalculationRule(models.Model):
    _name = "deployfleet.calculation.rule"
    _description = "DeployFleet Freight Calculation Rule"

    key = fields.Char(required=True, help="Stable identifier, e.g. 'fuel_cost', 'depreciation_cost'.")
    name = fields.Char(required=True)
    formula = fields.Char(
        required=True,
        help="Expression over named variables, e.g. '(distance_km / consumption_l_per_100km * 100) * diesel_price_per_l'.",
    )
    variable_ids = fields.One2many("deployfleet.calculation.variable", "rule_id")
```

**Security note, not optional**: a company-editable formula string is user-controlled input that the system evaluates at runtime — this must never go through a bare Python `eval()`. Odoo ships exactly the right tool for this: `odoo.tools.safe_eval`, a restricted evaluator that disallows imports, attribute access to dunder methods, and arbitrary code execution, used throughout Odoo core for user-editable expressions (domains, server actions, automated rules). `deployfleet_freight_calculator` evaluates every formula through `safe_eval` with an explicit, whitelisted variable dictionary — never through `eval()` or `exec()`. This is the same class of mistake as the `eval()` usage caught and removed from this codebase's own test suite during Phase 1 lint cleanup — worth stating explicitly here so it isn't reintroduced at runtime, which would be a materially worse version of the same issue.

Company-specific *values* (not formulas) live separately:

```python
class DeployfleetCalculationParameter(models.Model):
    _name = "deployfleet.calculation.parameter"
    _description = "DeployFleet Calculation Parameter Value"

    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    key = fields.Char(required=True, help="e.g. 'diesel_price_per_l', 'maintenance_cost_per_km'.")
    value = fields.Float(required=True)
    vehicle_type_id = fields.Many2one(
        "deployfleet.vehicle.type",
        help="Optional — some parameters (fuel consumption) vary by vehicle type; leave blank for a company-wide default.",
    )
```

This split (formula in `deployfleet.calculation.rule`, values in `deployfleet.calculation.parameter`) is what makes "each company can customize fuel assumptions, driver costs, maintenance rates, profit margins" (the proposal's own requirement) work without touching code — an admin edits parameter values, a rule's formula stays stable and reviewed once.

## 4. The eleven calculators — what's core, what's a later refinement

| # | Calculator | Built on the rule engine directly? | Notes |
|---|---|---|---|
| 1 | **Load Profit Calculator** | Yes — this *is* the rule engine's primary use | Revenue minus fuel, driver cost, maintenance, tolls, insurance allocation, depreciation. Depreciation is a genuinely important addition the proposal is right to flag — small operators forget it and underprice as a result. |
| 2 | **Cost Per Km Calculator** | Yes | Fixed cost/km (loan + insurance + driver ÷ expected monthly km) plus variable cost/km (fuel + maintenance) — same parameter set as #1, aggregated differently. |
| 3 | **Rate Calculator** ("what should I charge?") | Partially | The cost side is the rule engine; the "competitive"/"premium" tiers want a market-rate reference, which is [13-freight-intelligence-architecture.md](13-freight-intelligence-architecture.md)'s `deployfleet.rate.benchmark` — **for v1, before real market data exists, a manually-configured markup percentage per tier is enough**; wire in real benchmarking once doc 13's historical data actually exists, per that document's own sequencing. |
| 4 | **Empty Miles Calculator** | Partially | The empty-return cost is the rule engine (distance × cost/km); the *return-load probability* is doc 13's backhaul intelligence, which explicitly needs real trip history to be meaningful. **For v1, the dispatcher enters an estimated probability manually** — the calculator still does the arithmetic and gives a clear recommendation ("don't accept unless rate increases by $X"), it just doesn't yet predict the probability itself. |
| 5 | **Break-even Calculator** | Yes | Same fixed-cost parameters as #2, inverted to solve for minimum monthly revenue/trip count. |
| 6 | **Fuel Calculator** | Yes | The simplest, most immediately useful — likely the first one built. |
| 7 | **Trip Time Calculator** | Yes, plus new assumptions | Needs average-speed, border-delay, and rest-period parameters. The rest-period assumption should reuse whatever driver rest-hour rule ends up enforced in Phase 3's compliance work ([06-risks-and-recommendations.md](06-risks-and-recommendations.md) risk #3) — one rest-rule definition, not two that could disagree. |
| 8 | **Weight & Payload Calculator** | Needs new vehicle fields | Requires gross vehicle weight and tare (empty) weight on `deployfleet.vehicle` — neither exists today. See §5. |
| 9 | **Container Calculator** | Standalone, lower priority | Intermodal/container-specific (20ft/40ft/high-cube, chassis compatibility) — a real need for container operators, not a need for a general Zambian road-freight trucking company. Build if/when a customer actually runs container operations, not preemptively. |
| 10 | **Tyre Cost Calculator** | Yes, ties to a Phase 2 module | Cost/km = tyre price ÷ life in km. Once `deployfleet_tyres` (Phase 2, per [04-module-structure.md](04-module-structure.md)) exists and tracks real replacement history, this parameter can be computed from actual data instead of a manual assumption — same "start manual, enhance with real data" pattern as #3/#4. |
| 11 | **AI Calculator Assistant** | Not a calculator — a UI on top of #1–#10 | See §6. |

## 5. New vehicle fields needed — extends the same recommendation already made once

[12-ltl-freight-management-architecture.md](12-ltl-freight-management-architecture.md) §5 already recommended adding `max_weight_kg`/`max_volume_m3` to the already-shipped `deployfleet_vehicle` as a small, generically useful patch. This proposal's Weight & Payload Calculator (#8) and Fuel Calculator (#6) need two more, in the same patch rather than a second one: `gross_vehicle_weight_kg` (GVW) and `tare_weight_kg` (empty weight) — payload capacity is GVW minus tare, and an "OVERWEIGHT BY 2 TONS" check is exactly `tare_weight_kg + shipment.weight_kg > gross_vehicle_weight_kg`, no new model needed for that check specifically. `fuel_consumption_l_per_100km` is better modeled as a `deployfleet.calculation.parameter` scoped by `vehicle_type_id` (§3) than a field on every vehicle record, since it's a planning assumption that varies by truck type, not a measured fact per vehicle — though a real per-vehicle override is a reasonable future refinement once fuel-log history (`deployfleet_fuel`, Phase 2) exists to compute an actual figure instead of an assumed one.

## 6. AI Calculator Assistant — the existing pattern, once more

Per the standard established across every AI-touching document in this set: no new provider router, cache, or agent identity. "Can I make money carrying 32 tons of maize from Lusaka to Dar for $3,800?" is the Finance Agent (extended in [13-freight-intelligence-architecture.md](13-freight-intelligence-architecture.md) §5) calling this module's calculation engine and formatting the result conversationally — the arithmetic is deterministic and already exists in §3–§4; the AI's job is translating a natural-language question into the right calculator call and explaining the output, not computing a different number than the calculator would show a human clicking through the form. **The recommendation ("NEGOTIATE," "ACCEPT," suggested minimum rate) is exactly that — a recommendation.** Per [06-risks-and-recommendations.md](06-risks-and-recommendations.md) risk #7, restated once more because it applies here with full force: the AI never sends a counter-offer or accepts a load on the company's behalf. A human reads the recommendation and acts.

## 7. Integration

```
deployfleet_freight_calculator (the engine + core calculators)
        |
        +---- deployfleet_dispatch's scoring function (SS4 of 09-dispatch-module-design.md)
        |         can call the profit calculator to inform, not replace, its existing
        |         availability/qualification hard-disqualify logic
        |
        +---- deployfleet_rate_intelligence (13-freight-intelligence-architecture.md SS3)
        |         consumes this engine instead of maintaining its own cost model
        |
        +---- Dispatch Board (kanban, per 09-dispatch-module-design.md SS5) — a shipment's
        |         estimated profit is a natural column to surface there
        |
        +---- deployfleet_billing (Phase 4) — quotation/customer pricing eventually reads
        |         from the same engine, so a quoted price and the internal profit
        |         calculation are never two different numbers
        |
        +---- deployfleet_reports (analytics) — margin-by-lane, margin-by-customer
```

## 8. Roadmap placement — recommend earlier than the other three vision documents

Unlike [10](10-lead-intelligence-architecture.md)/[11](11-dispatch-network-architecture.md)/[13](13-freight-intelligence-architecture.md), nothing in the core engine (§3–§4, calculators #1–#2, #5–#7, #10) depends on historical trip data, a second business model, or AI. It depends only on: `deployfleet_vehicle` (shipped, plus the small field addition in §5), `deployfleet_route` (shipped, for distance), and company-configured parameters an admin enters once at setup. **Recommendation: schedule the core engine and calculators #1, #2, #5, #6, #7, #10 as a Phase 2 (Cost Control) addition**, alongside `deployfleet_fuel`/`deployfleet_maintenance`/`deployfleet_tyres` — it fits that phase's own stated goal ("save money... the product visibly pays for itself") better than almost anything else proposed in this document set, and per the proposal's own framing, may be worth prioritizing specifically because of its demo value with the incoming real customer.

Calculators #3 (Rate) and #4 (Empty Miles) ship with their v1 manual-assumption fallback in the same phase; upgrade them to use real benchmarking/backhaul data once [13-freight-intelligence-architecture.md](13-freight-intelligence-architecture.md)'s prerequisites are met — that upgrade is a parameter-source change, not a redesign, because the calculator's arithmetic doesn't change, only where the probability/benchmark number comes from. Calculator #8 (Weight & Payload) ships whenever the GVW/tare fields land (§5, bundled with the Phase 2 vehicle-fields patch). Calculator #9 (Container) and #11 (AI Assistant) are correctly lower priority — #9 until a customer actually runs containers, #11 until the Finance Agent extension in doc 13 exists to hang it on.
