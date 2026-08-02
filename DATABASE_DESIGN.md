# Database Design

Short entry point — the maintained, detailed version with the full entity-relationship diagram and workflow sequences is [docs/architecture/07-domain-model-erd.md](docs/architecture/07-domain-model-erd.md). Read that before creating or modifying any model.

## Summary

The core operational chain: **Customer → Shipment → Route → Dispatch Assignment → Trip → Delivery**, with Vehicle (`deployfleet.vehicle`, delegating Odoo's native `fleet.vehicle` via `_inherits`) and Driver (`hr.employee` extended via `_inherit`) as the two resources dispatch assigns.

Notable, deliberate design choices — treat these as decided, not obvious defaults to second-guess mid-implementation:

- **Shipment ↔ Trip is many-to-many** (via `deployfleet.trip.shipment.line`), not one-to-one — a trip can carry multiple shipments (consolidated cargo) and a shipment can require multiple trips (multi-leg, split loads). Building the join model from day one is cheap even if the simple case (one shipment, one trip) is what's actually common; retrofitting it later after Trip has a hardcoded single `shipment_id` is not.
- **Contract on a Shipment is optional** — supports spot loads booked without a standing contract.
- **Dispatch Assignment is distinct from Trip** — preserves a plan-vs-execution split (the assignment can be revised before it becomes a committed trip).
- **Compliance documents are polymorphic** (`res_model`/`res_id`) — one expiry/verification engine serves both driver documents (license, medical) and vehicle documents (registration, insurance, roadworthiness).
- **Owner-operator vs. company-owned vehicle is not yet modeled** — an explicitly flagged gap, not an oversight. See [docs/architecture/07-domain-model-erd.md](docs/architecture/07-domain-model-erd.md) §3 and open question #5 in [docs/architecture/06-risks-and-recommendations.md](docs/architecture/06-risks-and-recommendations.md).

## This schema is a draft pending real-world validation

[docs/architecture/07-domain-model-erd.md](docs/architecture/07-domain-model-erd.md) is explicit that its judgment calls (spot loads, backhauls, consolidated cargo handling) are derived from the DeployGuard codebase's shape and general trucking-domain reasoning, not yet from a working session with a real Zambian trucking operator. Do not treat Phase 1's schema as frozen until that validation has happened — see [docs/architecture/06-risks-and-recommendations.md](docs/architecture/06-risks-and-recommendations.md) risk #5.
