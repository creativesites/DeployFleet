# DeployFleet — Phase 1 Architecture Planning

**Status:** Draft for review. No code has been written or forked yet — this document set is the Phase 1 deliverable: analysis and a transformation plan for turning DeployGuard (a security-workforce platform) into DeployFleet (a transportation & logistics operations platform), starting with local trucking companies in Zambia.

Source codebase analyzed: `creativesites/DogFrce-Security-Services-Custom-Odoo-Modules` (Odoo 19 Community, 45 custom modules, ~28k lines of Python, ~30k lines of XML, plus an Expo/React Native mobile app).

Target repository: `creativesites/DeployFleet` (currently empty — this is its first commit).

## How to read this document set

| Doc | Answers |
|-----|---------|
| [01-module-audit.md](01-module-audit.md) | What exists today, module by module, and what happens to each one (keep / rename / refactor / split / remove) |
| [02-reuse-strategy.md](02-reuse-strategy.md) | What business logic, UI, security model, reports, APIs, and mobile code we carry forward largely intact |
| [03-refactoring-roadmap.md](03-refactoring-roadmap.md) | Technical debt inherited from DeployGuard, the naming/model-rename strategy, and what to fix *while* forking rather than after |
| [04-module-structure.md](04-module-structure.md) | The proposed DeployFleet module list, dependency graph, and naming convention |
| [05-implementation-roadmap.md](05-implementation-roadmap.md) | Phased build sequence, sprint-level sequencing, and what "done" looks like per phase |
| [06-risks-and-recommendations.md](06-risks-and-recommendations.md) | Open decisions, risks, and this architect's specific recommendations |

## Executive summary

**The core finding: this fork is unusually favorable.** DeployGuard was already built as a workforce-scheduling-and-payroll platform with a *fleet module bolted on the side* (`security_fleet`) for guard transport shuttles. That side module already contains a `Vehicle`, `ShuttleRoute`, `ShuttleRun`, `Passenger`, `FuelLog`, `VehicleInspection`, and `VehicleServiceLog` — i.e., the literal seed of DeployFleet's entire core domain. Fleet stops being a peripheral module and becomes the product's center of gravity; almost everything else in the codebase (payroll, HR, billing, documents, notifications, AI, mobile, licensing, theming) is either generically reusable HR/ops/fintech plumbing or an adjacent bridge module whose *pattern* is reusable even where its *content* is not.

**What this is not:** a like-for-like rename. The operational core — the object model that today reads `client → site → post → shift requirement → roster batch → roster slot → attendance record` — has to become `client → contract/lane → route → trip schedule → dispatch assignment → trip execution`. That is a genuine domain remodel, not a find-and-replace. The scoring engine, document-expiry engine, payroll pipeline, billing pipeline, and AI facade are reusable *machinery*; the operational domain model is not.

**What must not be forked:** `security_dogforce_data` (71k+ lines loading a real client's actual company data via XLSX) and the Namibia/Zambia-guard-specific demo data modules. These are client-specific and, in the case of `security_dogforce_data`, carry real business data that has no place in a new commercial product's codebase — not even as a reference. See [06-risks-and-recommendations.md](06-risks-and-recommendations.md) for why this is flagged as a hard risk, not just cleanup.

**Recommended framing for effort:** of the 45 source modules, roughly:
- **12 keep unchanged or rename-only** (pure platform plumbing: licensing, theming, help, tours, backup, notifications, reconciliation core, reporting shell)
- **9 keep with heavy refactor** (payroll, HR, billing, mobile API, AI engine — generic engine, industry-specific surface)
- **11 keep with domain remodel** (the operations/scheduling/attendance/document/equipment core — this is where the real design work happens)
- **6 split into smaller modules** (fleet and operations are too large and too central to stay monolithic in a product where they're the star, not a side dish)
- **7 removed outright** (client-specific data, guard-specific demo seeds, meta-installers that reference removed modules by name)

No implementation should begin until the module structure in [04-module-structure.md](04-module-structure.md) and the phased roadmap in [05-implementation-roadmap.md](05-implementation-roadmap.md) are agreed.
