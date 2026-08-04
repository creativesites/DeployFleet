# 20 — DeployFleet Experience Implementation Strategy

**Status:** Governing rollout strategy, set by explicit user direction after the Fleet & Vehicles custom-views work (Workshop Board, Vehicle 360, Parts/Asset Registries) proved the pattern. This document does not replace [16-experience-architecture.md](16-experience-architecture.md)–[19-animation-guidelines.md](19-animation-guidelines.md) — those remain the *what it should look like* set (visual personality, tokens, component catalog, motion). This document answers a different question: **in what order, to what depth, and against what bar do we actually finish the frontend, domain by domain?** It supersedes one specific part of doc 16: §11's lettered, horizontal Phase A–E rollout (build one category of screen — dashboards, then boards, then AI surfaces — across every domain at once) is replaced by the vertical, domain-completeness-first rollout defined here (§5). Doc 16's area-by-area redesign direction (§7) and doc 18's component catalog remain valid and load-bearing; only the *sequencing logic* changes.

---

## 1. Product philosophy

DeployFleet should not feel like an Odoo ERP. It should feel like a modern logistics operating system that just happens to be built on Odoo.

The biggest competitive advantage isn't features alone — most trucking software in this market covers similar ground functionally. It's **how approachable, intuitive, and impressive the product feels in the first five minutes of a demo.** Custom workspaces are not a polish pass; they are a sales mechanism:

- fewer clicks to do anything a dispatcher, fleet manager, or driver does every day
- complex multi-model workflows (a job card that touches parts stock and vehicle status; a dispatch assignment that touches compliance overrides) simplified into one screen instead of four
- a first-time user feels comfortable immediately, without training
- demos land — a prospect watches their own workflow happen in front of them, not a generic ERP form
- that directly increases DeployFleet's ability to win contracts

A trucking company owner should not feel like they are learning an ERP. They should feel like they are using software built specifically for trucking — because it is.

---

## 2. The New UI Rule

**As much as reasonably possible, every operational area should have custom views instead of stock Odoo list/form/kanban pages.** Default Odoo pages become implementation details — the data model underneath, not something a user routinely sees. Users interact with purpose-built DeployFleet workspaces. Each domain gets its own collection of custom pages, and each domain should feel like its own mini application within the product.

**This tightens [CLAUDE.md](../../CLAUDE.md) §5's existing UI/UX standard, not replaces it.** §5 already said "avoid excessive standard Odoo list/form views where a purpose-built interface materially improves the workflow" and "use judgment, don't rebuild everything in OWL reflexively." The judgment call now defaults harder toward custom, for one concrete reason found doing the Fleet & Vehicles work: **even simple master data reads as "ERP" the moment a user sees it.** `deployfleet.vehicle.type` is nine lines of Python (`name`, `code`, `sequence`) — about as close to "genuinely standard CRUD" as this product gets — but it's still a screen a fleet manager will open, and a stock editable list is still the tell that breaks the illusion mid-demo. So:

- **Every operational domain entity gets a custom view**, including simple master data (Vehicle Types, Part Categories, and similar), *if a user in that domain's normal workflow will ever see it.*
- **Pure admin/system configuration stays on standard views for now** — AI provider config, AI budget/usage log config, notification rule config, the event bus, mobile device registrations, licenses. These are the same "admin/config-only screens" doc 16 §3.1 and the Mega Menu curation already excluded from tile promotion — an operator never opens them to do their job; an implementer opens them once during setup. Revisit this list once every operational domain is done, not before — see §7.
- **"Custom view" does not always mean a new bespoke layout.** Reusing an established pattern (the registry-ledger style from Parts/Asset Registries, the tap-to-expand accordion from the Dispatch Board) *is* the custom view — consistency across a domain's own screens matters more than every screen being visually novel. What matters is that the *user* never lands on stock Odoo chrome, not that every screen invents new interaction language.

---

## 3. Domain catalog

Six top-level domains already exist as Mega Menu entries (`deployfleet_ui/static/src/mega_menu/domain_content.js`, built in Phase B): **Fleet & Vehicles, Dispatch & Trips, Compliance, Billing & Finance, Driver & HR, AI & Intelligence.** The user's own example list for this strategy named a slightly different, more granular set — Fleet & Vehicles, Dispatch, Customers, Maintenance, HR — which reads as the *aspirational shape of a fully custom product* rather than a literal instruction to restructure the six shipped Mega Menu domains today. Two real boundary questions came out of reconciling the two lists, and both are **open, not decided** — see §8's questions to the user before any restructuring work begins:

1. **Should Maintenance become its own top-level domain, split out of Fleet & Vehicles?** Today, Maintenance Schedules, the Workshop Board, and (via AI & Intelligence) Predictive Maintenance already exist, but split across two Mega Menu domains. The user's example list groups Maintenance Planner, Workshop, Predictive Maintenance, and Service History as one unit. This is a real navigation decision, not just a doc question — it would move an already-shipped Mega Menu tile and touch a shared component.
2. **Should a "Customers" domain be carved out of Billing & Finance / Dispatch & Trips?** Today, Contracts lives under Billing & Finance and Depots lives under Dispatch & Trips; there is no Customer 360 or Communication Timeline screen anywhere yet. The user's example list groups Customer 360, Contracts, Billing, Shipments, and a Communication Timeline as one "Customers" domain.

Until those are decided, this document treats the **current six Mega Menu domains as the domain catalog** and plans within them. Below is that catalog with the user's aspirational workspace list mapped onto it, and today's actual state noted against each (✅ built and custom, 🟡 exists but still stock Odoo, ⬜ doesn't exist as a distinct screen yet):

### Fleet & Vehicles
| Workspace | State |
|---|---|
| Fleet Command Center (fleet-wide status + Vehicle 360 detail) | ✅ |
| Vehicle Profile (single vehicle — the actual `deployfleet.vehicle` record) | 🟡 stock form (no tabs, no related-record rollups) |
| Workshop Board | ✅ |
| Parts Registry | ✅ |
| Asset Registry | ✅ |
| Vehicle Types Workspace | 🟡 stock editable list, no form |
| Fuel Intelligence (trend/anomaly view, not just a log list) | 🟡 stock list/form only |
| Tyre Manager (fleet-wide tyre inventory/replacement, not per-vehicle-only) | 🟡 stock list/form; also only reachable read-only inside Vehicle 360 |
| Insurance Center (fleet-wide policy/claims/renewal view) | 🟡 stock list/form; also only reachable read-only inside Vehicle 360 |

This is the domain being re-audited in §6 below — it's the furthest along and the template for every domain after it.

### Dispatch & Trips
| Workspace | State |
|---|---|
| Dispatch Board | ✅ |
| Shipments (Load Booking Workspace) | 🟡 stock views |
| Trips (Load Tracking / Trip Timeline) | 🟡 stock views |
| Routes / Route Planning | 🟡 stock views |
| Deliveries | 🟡 stock views |
| Depots | 🟡 stock views |
| Dispatch Calendar | ⬜ no `<calendar>` view exists anywhere in the product (doc 16 §1 flagged this at zero) |
| Driver Availability | ⬜ |

### Compliance
| Workspace | State |
|---|---|
| Compliance Documents | 🟡 stock views |
| Document Types | 🟡 stock views |
| Compliance Overrides log | 🟡 stock views |
| Compliance Center (expiry-first dashboard, doc 16 §7.11-adjacent) | ⬜ |

### Billing & Finance
| Workspace | State |
|---|---|
| Invoices | 🟡 stock views |
| Rate Cards | 🟡 stock views |
| Contracts | 🟡 stock views |
| Freight Calculator | 🟡 stock wizard |
| Load Expenses | 🟡 stock views |
| ZRA Submissions | 🟡 stock views |
| Client Summary Report | 🟡 stock wizard |
| Financial Intelligence (doc 16 §7.13) | ⬜ |

### Driver & HR
| Workspace | State |
|---|---|
| Driver Scorecards | ✅ |
| Driver 360 (full profile: trips, compliance, performance, pay in one view) | ⬜ — Driver Scorecards is deliberately partial, see doc 16 §7.14 |
| Driver Advances | 🟡 stock views |
| Leave Planner | 🟡 stock views |
| Payroll Dashboard | 🟡 stock views |
| Loans | 🟡 stock views |

### AI & Intelligence
| Workspace | State |
|---|---|
| Copilot Console (Agent Catalog + Usage Dashboard + NL query) | ✅ |
| Copilot Rail (ambient approval queue) | ✅ |
| Predictive Maintenance / Fuel Anomalies / Financial Forecast standalone views | 🟡 stock views |

This table is the honest baseline. Most of the product is still 🟡. That is expected — Fleet & Vehicles is domain #1 under this strategy specifically *because* it's the one already closest to done.

---

## 4. UX goal

Users should rarely leave a workspace. Concretely, inside any finished domain:

- **Information is already visible** — no clicking into a record to learn its status; the workspace surfaces what matters (Vehicle 360's Tyres/Insurance/Workshop sections, Mission Control's attention strip).
- **Common actions are one click away** — a status transition, a stock receipt, a job-card advance — wired directly to the backend's real action methods, not a form save.
- **AI insights are embedded naturally**, using the reserved AI-violet convention (doc 17 §2.2), silent unless there's something worth surfacing — never a permanent widget with nothing to say.
- **Related information is grouped together** — the Vehicle 360 pattern (pull compliance, fuel, tyres, insurance, workshop into one vehicle's expanded detail) is the model for every "360" screen this strategy calls for.
- **Navigation feels obvious** — the Mega Menus, Launcher, and Command Palette (Phase B) already give every domain a consistent way in; a finished domain's own internal navigation (which workspace, which filter) should feel equally obvious, not require memorizing where something lives.
- **Users rarely leave the workspace** — "Open full record" (the stock form) should become a rare escape hatch for edge cases a workspace doesn't yet cover, not the primary way anyone edits a record.

---

## 5. Design principle: domain-completeness-first rollout

**Every domain should be completed before moving to another. No partially redesigned domains.**

For each domain, in order:

1. **Audit** — read every model, field, action method, and existing view in the domain, the same discipline used for Fleet & Vehicles (CLAUDE.md §10's audit notes, this document's §6 below).
2. **Design** — plan the complete set of workspaces needed to replace every stock screen a user in that domain would otherwise see, collaboratively with the user before writing code (the same "we'll plan the ui and flows together" precedent Fleet & Vehicles set).
3. **Replace every important stock screen** — not just the flagship dashboard; the supporting list/form pairs too (Vehicle Types, Fuel Logs, Maintenance Schedules, Tyres, Insurance — the long tail is exactly what was still stock after Fleet & Vehicles' first four deliverables).
4. **Build all supporting workspaces** the design calls for.
5. **Polish interactions** — mobile touch targets, glassmorphism where Command Layer applies, empty/loading states, the same bar the Launcher's glassmorphism-polish pass set.
6. **Click-test everything** — on the demo server, on a real device where mobile matters, the same "syntax-valid is not the same as rendering correctly" discipline this project has carried since Phase A of `deployfleet_ui`.
7. **Only then move to the next domain.**

**This explicitly supersedes doc 16 §11's original phased rollout** (Phase A: design system → Phase B: navigation → Phase C: flagship screens *across every domain* → Phase D: AI → Phase E: premium experiences). That structure optimized for "get one instance of every screen *type* live everywhere" — reasonable when nothing existed yet, but it's why Fleet & Vehicles ended up with a polished Fleet Command Center sitting next to a completely untouched Vehicle Types list. Going forward, the unit of "done" is a **domain**, not a screen type. A domain is finished when its row in the table in §3 (or the domain's own equivalent table, once audited) is all ✅ — not when its flagship board is ✅ and everything else is still 🟡.

---

## 6. Fleet & Vehicles re-audit — what's left

The four deliverables shipped so far (Workshop Board, Vehicle 360, Parts Registry, Asset Registry) replaced the domain's *review and quick-action* surfaces. They did not replace the domain's *record-level* surfaces — the actual create/edit screens a user hits via "Open full record," or via a menu that was never touched because it wasn't part of the original four-deliverable plan. Re-auditing against the New UI Rule (§2) — every operational entity gets a custom view — surfaces five remaining gaps, verified directly against the current view XML (not guessed):

1. **Vehicle Profile.** `deployfleet.vehicle`'s stock form has zero tabs and zero related-record rollups — a user editing a vehicle's identity/capacity fields sees nothing about that vehicle's compliance, fuel, tyres, insurance, or workshop history on the same screen (those all live in Vehicle 360, a *read* surface reached from a *different* menu). A custom Vehicle Profile page is the natural home for editing `license_plate`, `model_id`, `vehicle_type_id`, `current_driver_id`, `odometer`, and the four capacity fields (`max_weight_kg`, `max_volume_m3`, `gross_vehicle_weight_kg`, `tare_weight_kg`, `payload_capacity_kg`), plus the four status-transition actions already proven in Vehicle 360 — likely built by evolving Vehicle 360's per-vehicle expanded-card content into a full page rather than starting over.
2. **Vehicle Types Workspace.** Nine fields, one stock editable list, no form. The smallest gap by data, but per §2's reasoning, still a visible ERP tell — a fleet manager configuring vehicle classes hits a bare Odoo list.
3. **Fuel Intelligence.** The stock list/form surfaces every field but nothing else — no trend view, no fleet-wide anomaly rollup, no reconciliation of the two anomaly signals outside Vehicle 360's per-vehicle context (doc 16 §7.10 already reconciled them per-vehicle; a fleet-wide Fuel Intelligence screen would be the first place to see *which vehicles* are trending anomalous, not just flag one log at a time).
4. **Tyre Manager.** Today, tyres are only reachable two ways: a stock list/form under `deployfleet_parts`'s menu, or read-only inside a specific vehicle's Vehicle 360 detail. Neither gives a fleet-wide view of tyre inventory/replacement due dates/tread-depth trend across the whole fleet — the actual workflow a workshop supervisor needs when planning a batch tyre replacement.
5. **Insurance Center.** Same shape of gap as Tyres — a stock list/form plus a read-only per-vehicle summary in Vehicle 360, no fleet-wide renewal/claims view (which policies expire this month, which vehicles have open claims).

**What this does not require rebuilding:** Fleet Command Center, Workshop Board, Parts Registry, and Asset Registry stay as-is — they already satisfy the New UI Rule for the surfaces they cover. This is additive, not a rework of the first four deliverables.

---

## 7. What "done" means for a domain

A domain is done when:

- Every model a normal user of that domain touches has a custom view for its primary read/browse surface (no stock list/kanban a user lands on routinely).
- Every model's primary create/edit surface is a custom view, or a deliberate, documented exception (the same transparency discipline every scope correction in this project has used — e.g., "Vehicle Types stays a stock form because X" would need to be an argued decision, not silence).
- Every workflow that today requires jumping between separate menus for related data (a vehicle's fuel/maintenance/tyres/insurance, previously four separate top-level menus) has at least one consolidated view.
- Mobile touch targets, empty states, and loading states meet the same bar the rest of `deployfleet_ui` already meets.
- The domain's own SCSS compiles cleanly (libsass, individually and in the full bundle) and has been click-tested on the demo server.
- Pure admin/config screens are the *only* remaining stock views in the domain, and that's a reviewed exclusion, not an oversight.

---

## 8. Open questions for the user before further restructuring

1. Should **Maintenance** split out of Fleet & Vehicles into its own top-level Mega Menu domain (Maintenance Planner, Workshop Board, Predictive Maintenance, Service History), or stay part of Fleet & Vehicles as it does today?
2. Should a **Customers** domain be carved out of Billing & Finance / Dispatch & Trips (Customer 360, Contracts, Billing, Shipments, Communication Timeline), or do those stay where they are?
3. For Fleet & Vehicles specifically (§6): confirm the five-gap list (Vehicle Profile, Vehicle Types Workspace, Fuel Intelligence, Tyre Manager, Insurance Center) and the proposed screen shapes before implementation starts, per the design-principle sequence in §5 (audit → design *together* → build).
4. Confirm the proposed domain build order after Fleet & Vehicles finishes: the next-closest domain today is Driver & HR (Driver Scorecards already shipped, five 🟡 items remain) or Dispatch & Trips (Dispatch Board shipped, but a larger 🟡/⬜ tail including the still entirely-missing Dispatch Calendar). No order is assumed here — this is the user's call per §5.

---

## 9. Success criteria

When someone demos DeployFleet, they should stop noticing Odoo. Instead they should notice beautiful workspaces, intuitive navigation, fast workflows, rich dashboards, contextual AI, and purpose-built interfaces — a premium trucking platform.

**The test:** if someone says *"this doesn't feel like Odoo,"* the strategy in this document has worked.
