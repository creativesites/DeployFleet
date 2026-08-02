# Module Structure

Short entry point — the maintained, detailed version is [docs/architecture/04-module-structure.md](docs/architecture/04-module-structure.md). Read that for the full module table, dependency graph, and MVP-12 rationale.

## Summary

~50 target modules across 8 groupings — Foundation, People, Fleet Assets, Operations, Finance, Reporting, Mobile & Portal, Intelligence — all under the `deployfleet_*` package namespace (see [CLAUDE.md](CLAUDE.md) §3 for the naming rules). This is more modules than DeployGuard's 45, not fewer, because fleet/dispatch/AI are now the product's center of gravity and get split into smaller, independently-installable pieces rather than staying as the few large, do-everything modules they were in the source.

## First commercial release: MVP-12

Do not build all ~50 modules before the first sale. The first sellable product:

`deployfleet_core`, `deployfleet_driver`, `deployfleet_vehicle`, `deployfleet_dispatch`, `deployfleet_trip`, `deployfleet_delivery`, `deployfleet_fuel`, `deployfleet_maintenance`, `deployfleet_compliance`, `deployfleet_billing`, `deployfleet_mobile_driver`, `deployfleet_reports` — plus the infrastructure substrate (`deployfleet_security`, `deployfleet_event_bus`, `deployfleet_ai_core`'s foundation) that every install needs regardless and isn't counted against the "12."

Full detail, including two packaging notes on where Shipment/Load and the event bus live for the MVP specifically: [docs/architecture/04-module-structure.md](docs/architecture/04-module-structure.md) §"First commercial release."

## Everything else is sequenced, not backlogged

Workshop depth, tyres/parts/assets, insurance, payroll/localization, dispatcher and customer mobile apps, CRM/Sales/Accounting bridges, and the full AI agent/action layer are deliberate expansion modules sequenced across 5 phases in [docs/architecture/05-implementation-roadmap.md](docs/architecture/05-implementation-roadmap.md) — not an undated "we'll get to it" list.
