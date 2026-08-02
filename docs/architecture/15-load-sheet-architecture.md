# 15 — Load Sheet Architecture (reconciliation, not a new entity layer)

**Status: mixed** — most of this proposal is enrichment of already-shipped models and two genuinely new, genuinely valuable small models; a couple of pieces are recommended against as proposed. Unlike [10](10-lead-intelligence-architecture.md)/[11](11-dispatch-network-architecture.md)/[13](13-freight-intelligence-architecture.md), nothing here is gated on historical data or AI — but unlike [14-freight-calculator-engine.md](14-freight-calculator-engine.md), most of it *is* gated on schema changes to an already-shipped, tested model, which is a real cost and should not be paid until it's needed. See §7 for the honest phasing recommendation.

## 1. The proposal, read against what's already shipped

The "Load Sheet" concept — a single comprehensive record of a load's identification, cargo, routing, truck/driver assignment, commercial terms, expenses, cash advances, documents, and status, framed with an aviation-flight-record/progressive-disclosure UI metaphor — groups into five categories once checked against the current domain model:

| Category | What the proposal describes | What it actually is |
|---|---|---|
| Load identity, cargo, routing, commercial terms | Structured load number, origin/destination, cargo detail, rate | **The same "Load" re-description caught three times already** (§2) — this is `deployfleet.shipment`, enriched, not a fourth entity |
| Truck/driver assignment | Which vehicle and driver carry the load, including non-owned/subcontracted trucks | **Mostly already shipped** (`deployfleet.dispatch.assignment`) — except the subcontracted-truck case, which is the already-flagged owner-operator gap, not new scope (§3) |
| Documents (POD, permits, weighbridge tickets, customer paperwork) | A documents section per load | **Odoo-native, not a new model** — `ir.attachment` + `mail.thread`, same as everywhere else in this codebase (§4) |
| Load expenses (fuel, tolls, loading fees, permits) actually incurred on a load | A cost-tracking section | **Genuinely new, genuinely useful** — `deployfleet.load.expense` (§5) |
| Driver cash advances for the trip (fuel float, tolls, subsistence) | A cash-advance section | **Genuinely new, and the strongest idea in the whole proposal** — `deployfleet.driver.advance` (§6) |
| Country-specific fields/behavior ("localization framework") | A dedicated module for market-specific load-sheet variations | **Anti-pattern as proposed** — reuse the country-pack-as-data pattern already established for payroll, don't build a new module (§8) |
| Custom/extensible fields, progressive-disclosure UI | Let operators add their own fields; show a load sheet like a flight record — summary first, detail on demand | **A UI/edition question, not a data-model question** — genuinely good instincts, with one honest caveat (§9) |

Sections 2–9 below cover each in turn. Only the genuinely new material (§5, §6) gets a full model design; everything already resolved by an earlier document is treated by reference, not re-litigated.

## 2. "Load" is `deployfleet.shipment` — fourth time, same answer

This is now the fourth time a "commercial cargo request" concept has been proposed under a new name: DeployGuard's own roster→attendance chain had no equivalent, then "Freight Order" in [12](12-ltl-freight-management-architecture.md), then "Load" in [13](13-freight-intelligence-architecture.md) §2, and now "Load" again here. The answer doesn't change: one entity, `deployfleet.shipment`, enriched over time as real needs arrive — not a family of near-duplicate models that eventually need reconciling against each other. Doc 13 §2 already scoped the specific enrichment (structured origin/destination beyond a depot reference, pickup windows, cargo classification, commercial rate fields) as its own effort, gated on an actual customer needing it (hazmat, temperature-controlled cargo, GPS-precision pickup points). Nothing in this proposal changes that recommendation; it just reconfirms the same fields are wanted. When that enrichment work happens, extend `deployfleet.shipment` directly — the same classical-extension pattern `deployfleet_driver` used on `hr.employee` — not a parallel `deployfleet.load` model.

## 3. Truck/driver assignment — mostly shipped, one real gap

`deployfleet.dispatch.assignment` (shipped, Phase 1) already links a shipment to a `deployfleet.vehicle` and a driver (`hr.employee`) with a score and workflow state. What the proposal adds that isn't shipped: the idea that the assigned truck might not be a company-owned `deployfleet.vehicle` at all — a subcontracted or owner-operator truck brought in for a specific load. That is not new scope invented by this proposal; it's the exact gap [07-domain-model-erd.md](07-domain-model-erd.md) §3 flagged and [11-dispatch-network-architecture.md](11-dispatch-network-architecture.md) §2 already designed for (`deployfleet.carrier`/`deployfleet.carrier.vehicle`). If a real customer needs "assign a subcontracted truck to this specific load" before they need a full dispatch-network business model, that's a signal to pull forward the carrier/carrier-vehicle models from doc 11 as a narrow slice — not a reason to design a third way of representing "a truck that isn't ours."

## 4. Documents — Odoo already solved this

POD, permits, weighbridge tickets, customs paperwork, customer-supplied documents: every model in this codebase that needs attachments already gets them for free via `ir.attachment`, and `mail.thread` (already used elsewhere in the codebase) gives a chatter/audit trail of who uploaded what and when, with no new model. `deployfleet.delivery` (shipped) already uses `Binary(attachment=True)` for signature/photo — the same pattern extends to any other document type a load needs. Building a bespoke `deployfleet.load.document` model would duplicate infrastructure Odoo ships natively and this codebase already leans on; don't.

## 5. `deployfleet.load.expense` — genuinely new, and it completes doc 14's picture

[14-freight-calculator-engine.md](14-freight-calculator-engine.md) computes what a load is *estimated* to cost, before or during dispatch. Nothing today records what a load *actually* cost. That gap is real and worth closing:

```python
class DeployfleetLoadExpense(models.Model):
    _name = "deployfleet.load.expense"
    _description = "DeployFleet Load Expense"

    shipment_id = fields.Many2one("deployfleet.shipment", required=True, ondelete="cascade")
    trip_id = fields.Many2one("deployfleet.trip")
    expense_type = fields.Selection(
        [("fuel", "Fuel"), ("toll", "Toll"), ("loading_fee", "Loading/Offloading Fee"),
         ("permit", "Permit"), ("weighbridge", "Weighbridge Fee"), ("other", "Other")],
        required=True,
    )
    amount = fields.Monetary(required=True)
    currency_id = fields.Many2one("res.currency", required=True, default=lambda self: self.env.company.currency_id)
    recorded_by = fields.Many2one("res.users", default=lambda self: self.env.user)
    receipt = fields.Binary(attachment=True, help="Photo of the physical receipt, per §4.")
```

This is not a new cost-calculation concept competing with doc 14's engine — it's the *actuals* side, and it's exactly what makes doc 14's estimates get better over time: once enough `deployfleet.load.expense` records exist for a lane/vehicle-type, `deployfleet.calculation.parameter` values (diesel price per liter, toll cost per route segment) can be checked against or even derived from real recorded expense, the same "start manual, improve with real data" pattern already used for the Rate and Empty Miles calculators in doc 14 §4. It also directly improves [13-freight-intelligence-architecture.md](13-freight-intelligence-architecture.md)'s `deployfleet.rate.benchmark`: actual cost minus actual invoiced rate is a truer profit figure than estimate minus invoiced rate, once billing (Phase 4) exists to supply the invoiced side.

## 6. `deployfleet.driver.advance` — the strongest idea in the proposal, and worth calling out as such

Cash advances to drivers for fuel float, tolls, border fees, and subsistence on a multi-day trip are a real, underserved operational pain point for African long-haul trucking specifically — it's exactly the kind of domain detail that separates a platform genuinely designed for this market from a generic fleet tool with vehicle types renamed. This deserves to be built, not deferred:

```python
class DeployfleetDriverAdvance(models.Model):
    _name = "deployfleet.driver.advance"
    _description = "DeployFleet Driver Cash Advance"

    driver_id = fields.Many2one("hr.employee", required=True, domain=[("deployfleet_is_driver", "=", True)])
    trip_id = fields.Many2one("deployfleet.trip")
    amount = fields.Monetary(required=True)
    currency_id = fields.Many2one("res.currency", required=True, default=lambda self: self.env.company.currency_id)
    issued_date = fields.Date(default=fields.Date.context_today, required=True)
    purpose = fields.Selection(
        [("fuel", "Fuel Float"), ("toll_border", "Tolls/Border Fees"), ("subsistence", "Subsistence"), ("other", "Other")],
    )
    reconciled_expense_ids = fields.One2many("deployfleet.load.expense", "advance_id",
                                              help="Actual expenses this advance was meant to cover.")
    state = fields.Selection(
        [("issued", "Issued"), ("reconciled", "Reconciled"), ("deducted", "Deducted from Payroll")],
        default="issued", required=True,
    )
```

The reason this is more than a standalone petty-cash log: it should reconcile against §5's `deployfleet.load.expense` records (an advance of $200 against $180 of recorded fuel/toll receipts leaves $20 either returned or short) and, when unreconciled, feed `deployfleet_payroll` (Phase 3, per [04-module-structure.md](04-module-structure.md)) as a deduction — the same "loans/advances against payslip" mechanism the payroll module already needs for `deployfleet_loans`. Don't build a second deduction pipeline; `deployfleet.driver.advance` becomes one more source feeding the payroll deduction engine doc 05's Phase 3 already plans, not a parallel one.

## 7. Roadmap placement for §5–§6

Both models are small, deterministic, and need no historical data or AI — the same profile that got doc 14's core engine recommended into Phase 2 ahead of the rest of the freight-intelligence document set. Recommendation: **`deployfleet.load.expense` and `deployfleet.driver.advance` are a Phase 2 (Cost Control) addition, alongside `deployfleet_freight_calculator`** (doc 14) — they belong in the same phase because they're the actuals-tracking companion to that phase's estimation engine, and because driver cash-advance tracking is real day-one value for the incoming customer regardless of what else has landed yet. The payroll-deduction *integration* (the `state = "deducted"` transition) waits for `deployfleet_payroll` in Phase 3, same as `deployfleet_loans`; until then, `deployfleet.driver.advance` still works standalone as an issue/reconcile record even without the payroll link wired up.

## 8. Localization framework — don't build a new module, extend the existing pattern

The proposal's instinct that load-sheet behavior should vary by country (different required permit types, different weighbridge/document conventions, different currency/tax handling) is correct — but a dedicated `deployfleet_localization_framework` module would be solving a problem this codebase already has a resolved answer for. [03-refactoring-roadmap.md](03-refactoring-roadmap.md) fixed exactly this class of problem for payroll: *"`deployfleet_payroll` depends only on `deployfleet_core`/`hr`; country packs (`deployfleet_l10n_zm`, `deployfleet_l10n_na`, future packs) each depend on `deployfleet_payroll` independently and register their rule sets via data, not via a manifest dependency chain between country packs."* The same shape applies here: `deployfleet_load_expense`/`deployfleet_driver_advance` (or `deployfleet_shipment` itself, wherever the country-specific field actually lives) stays country-neutral, and country packs contribute their own expense-type lists, required-document sets, or currency defaults as **data**, loaded by the relevant `deployfleet_l10n_*` module — not as a new abstraction layer that has to be designed once and gotten right for every country up front. Building a generic "localization framework" before there are two real countries' worth of requirements to generalize from is exactly the kind of speculative abstraction [09-dispatch-module-design.md](09-dispatch-module-design.md) and this codebase's own conventions (CLAUDE.md's "no half-finished implementations," "don't design for hypothetical future requirements") argue against.

## 9. Progressive disclosure / "flight record" UI — good instinct, one honest caveat

Framing a load sheet like an aviation flight record — a clean summary view with full detail available on demand, rather than one long form dumping every field at once — is a genuinely good fit for this project's own UI/UX standards ([CLAUDE.md](../../CLAUDE.md) §5: mobile-first, avoid stock Odoo list/form chrome where a purpose-built interface materially improves the workflow, OWL as the default for anything user-facing and non-trivial). A load sheet is a good candidate for a custom OWL component with a collapsed summary card (load number, route, status, assigned truck/driver) and expandable sections (cargo detail, expenses, advances, documents) rather than a standard Odoo form view with every field visible at once — consistent with the dispatch-board and vehicle-card treatment already called for elsewhere.

The caveat: the proposal's related idea of letting individual operators freely add their own custom fields to the load sheet is, in Odoo, primarily a **Studio** feature — and Studio is **Enterprise-only**. This ties directly to the still-open question in [06-risks-and-recommendations.md](06-risks-and-recommendations.md): Community vs. Enterprise is not yet decided. Until it is, "operators can add custom fields themselves" should not be treated as a given. If the edition decision lands on Community, the fallback is a bounded, admin-configured extension mechanism (e.g., a small set of generic `x_custom_char_1..3`-style fields exposed per record, or a `deployfleet.load.custom.field` key/value model scoped per company) — workable, but materially less flexible than Studio, and worth saying so plainly now rather than promising a capability that depends on an edition decision nobody has made yet.

## 10. What this document does not do

Consistent with every other reconciliation document in this set: it does not schedule shipment-field enrichment (§2) ahead of an actual customer need, does not create a new "Load" entity, and does not recommend building the localization framework or custom-fields mechanism before they're needed. What it does schedule concretely is §5–§6 into Phase 2, because — same test applied to doc 14 — they need no historical data, no AI, and no unresolved edition decision to be worth building now.
