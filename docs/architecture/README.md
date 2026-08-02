# DeployFleet — Phase 1 Architecture Planning

**Status:** Draft for review (revision 2). No code has been written or forked yet — this document set is the Phase 1 deliverable: analysis and a transformation plan for turning DeployGuard (a security-workforce platform) into DeployFleet (a transportation & logistics operations platform), starting with local trucking companies in Zambia.

Source codebase analyzed: `creativesites/DogFrce-Security-Services-Custom-Odoo-Modules` (Odoo 19 Community, 45 custom modules, ~28k lines of Python, ~30k lines of XML, plus an Expo/React Native mobile app).

Target repository: `creativesites/DeployFleet`.

## Revision log

**Revision 2** (this version) incorporates a full architecture review. Changes of substance, not just wording:

- **Naming unified under `deployfleet_*`** everywhere — modules, technical model names, security groups — replacing v1's `fleet_*`/`dfleet.*` split, since "fleet" alone reads as native Odoo.
- **Vehicle architecture resolved**: `deployfleet.vehicle` uses delegation inheritance (`_inherits`) over Odoo's native `fleet.vehicle`, not a standalone model and not plain field-bolt-on `_inherit`. See [03-refactoring-roadmap.md](03-refactoring-roadmap.md) §A.2.
- **A working event bus was found in the source** (`security_base/models/security_event_bus.py`, missed in v1) and promoted to a first-class `deployfleet_event_bus` foundation module, with one real defect (hardcoded subscriber list) flagged to fix during the port. See [02-reuse-strategy.md](02-reuse-strategy.md) §0.
- **Shipment/Load added as a first-class entity** between Customer and Trip — v1's domain model went straight from contract to route to trip with no cargo concept, which review correctly called out ("a trip without cargo is meaningless").
- **Module regrouping**: driver split into its own module from core identity; "discipline" reframed as `deployfleet_driver_performance`; equipment split three ways (parts / tyres / assets, not two); mobile split three ways by role (driver / dispatcher / customer) instead of one API module.
- **MVP-12 first release** replaces v1's broader install-profile framing — a focused, sellable 12-module scope, with infrastructure modules (core, event bus, security) treated as substrate rather than counted against that number.
- **Roadmap restructured** into 5 phases (Operational Foundation → Cost Control → Compliance → Customer Platform → Intelligence) instead of v1's 7, with a Phase 0 prerequisite gate kept in front of all of them.
- **New deliverable**: [07-domain-model-erd.md](07-domain-model-erd.md) — the domain model/ERD review asked for as the concrete next step, with entities, relationships, and key workflows, plus explicit notes on where it's a judgment call pending real-world validation (spot loads, backhauls, owner-operator vehicles, consolidated cargo).

## How to read this document set

| Doc | Answers |
|-----|---------|
| [01-module-audit.md](01-module-audit.md) | What exists today, module by module, and what happens to each one (keep / rename / refactor / split / remove) |
| [02-reuse-strategy.md](02-reuse-strategy.md) | What business logic (incl. the event bus), UI, security model, reports, APIs, and mobile code we carry forward largely intact |
| [03-refactoring-roadmap.md](03-refactoring-roadmap.md) | Technical debt inherited from DeployGuard, the naming/model-identity strategy (incl. the vehicle-delegation pattern), and what to fix *while* forking rather than after |
| [04-module-structure.md](04-module-structure.md) | The proposed DeployFleet module list, dependency graph, and MVP-12 first-release scope |
| [05-implementation-roadmap.md](05-implementation-roadmap.md) | The 5-phase build sequence and what "done" looks like per phase |
| [06-risks-and-recommendations.md](06-risks-and-recommendations.md) | Risks, this architect's recommendations, and the remaining open questions for sign-off |
| [07-domain-model-erd.md](07-domain-model-erd.md) | The entity model, relationships, and key workflows Phase 1 implementation builds against |

## Executive summary

**The core finding: this fork is unusually favorable.** DeployGuard was already built as a workforce-scheduling-and-payroll platform with a *fleet module bolted on the side* (`security_fleet`) for guard transport shuttles. That side module already contains a `Vehicle`, `ShuttleRoute`, `ShuttleRun`, `Passenger`, `FuelLog`, `VehicleInspection`, and `VehicleServiceLog` — i.e., the literal seed of DeployFleet's entire core domain. It also — as revision 2 found — already contains a working, if slightly flawed, cross-module event bus (`security.event.log`), which turns out to be one of the most valuable and least obvious assets in the whole codebase. Fleet and dispatch stop being peripheral and become the product's center of gravity; almost everything else (payroll, HR, billing, documents, notifications, AI, mobile, licensing, theming) is either generically reusable plumbing or an adjacent bridge module whose *pattern* is reusable even where its *content* is not.

**What this is not:** a like-for-like rename. The operational core has to remodel from `client → site → post → shift requirement → roster batch → roster slot → attendance record` into `customer → shipment → route → dispatch assignment → trip → delivery` — a genuine domain remodel per [07-domain-model-erd.md](07-domain-model-erd.md), not a find-and-replace. The scoring engine, document-expiry engine, payroll pipeline, billing pipeline, event bus, and AI facade are reusable *machinery*; the operational domain model is not.

**What must not be forked:** `security_dogforce_data` (71k+ lines loading a real client's actual company data via XLSX) and the Namibia/Zambia-guard-specific demo data modules. See [06-risks-and-recommendations.md](06-risks-and-recommendations.md) risk #1.

**What ships first:** not all ~48 modules. [04-module-structure.md](04-module-structure.md) defines a focused MVP-12 (driver, vehicle, dispatch, trip, delivery, fuel, maintenance, compliance, billing, driver mobile app, reports, plus the core/event-bus substrate) as the first sellable product, with everything else — workshop depth, tyres/parts/assets, insurance, payroll/localization, dispatcher and customer apps, CRM/Sales/Accounting bridges, AI, WhatsApp — sequenced across the 5 phases in [05-implementation-roadmap.md](05-implementation-roadmap.md).

**What's still open, not yet decided:** Odoo edition (Community vs. Enterprise), whether any real trucking-operator discovery work has validated [07-domain-model-erd.md](07-domain-model-erd.md) yet, and whether the owner-operator-vehicle distinction matters for the initial target customers. See [06-risks-and-recommendations.md](06-risks-and-recommendations.md) for the full list.

No implementation should begin until the module structure in [04-module-structure.md](04-module-structure.md), the phased roadmap in [05-implementation-roadmap.md](05-implementation-roadmap.md), and the domain model in [07-domain-model-erd.md](07-domain-model-erd.md) are agreed — and ideally, until the domain model has been checked against at least one real trucking company's actual dispatch workflow.
