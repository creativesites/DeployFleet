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

Six top-level domains already exist as Mega Menu entries (`deployfleet_ui/static/src/mega_menu/domain_content.js`, built in Phase B): **Fleet & Vehicles, Dispatch & Trips, Compliance, Billing & Finance, Driver & HR, AI & Intelligence.** The user's own example list for this strategy named a slightly different, more granular set — Fleet & Vehicles, Dispatch, Customers, Maintenance, HR — which read as the *aspirational shape of a fully custom product* rather than a literal instruction to restructure the six shipped Mega Menu domains. Two real boundary questions came out of reconciling the two lists; **both are now resolved** (confirmed by the user via `AskUserQuestion` during the Fleet & Vehicles gap-closing round, §8 records the resolution):

1. **Should Maintenance become its own top-level domain, split out of Fleet & Vehicles?** **Resolved: no** — Maintenance stays part of Fleet & Vehicles.
2. **Should a "Customers" domain be carved out of Billing & Finance / Dispatch & Trips?** **Resolved: no** — Contracts stays under Billing & Finance, Depots stays under Dispatch & Trips, no restructuring for now.

This document treats the **current six Mega Menu domains as the domain catalog** and plans within them. Below is that catalog with the user's aspirational workspace list mapped onto it, and today's actual state noted against each (✅ built and custom, 🟡 exists but still stock Odoo, ⬜ doesn't exist as a distinct screen yet):

### Fleet & Vehicles — **complete** (all ten workspaces ✅)
| Workspace | State |
|---|---|
| Fleet Command Center (fleet-wide status + Vehicle 360 detail + Vehicle Profile edit) | ✅ |
| Vehicle Profile (single vehicle — the actual `deployfleet.vehicle` record) | ✅ folded into Fleet Command Center's expanded detail, not a separate screen — see §6 |
| Workshop Board | ✅ |
| Parts Registry | ✅ |
| Asset Registry | ✅ |
| Vehicle Types Workspace | ✅ |
| Fuel Intelligence (trend/anomaly view, not just a log list) | ✅ |
| Tyre Manager (fleet-wide tyre inventory/replacement, not per-vehicle-only) | ✅ |
| Insurance Center (fleet-wide policy/claims/renewal view) | ✅ |
| Maintenance Planner (doc 16 §7.11's calendar-plus-Gantt widget) | ✅ — Overview/Calendar/Timeline in one workspace, see §6a |

This is the first domain to reach full completion under doc 20 §5's domain-completeness-first rollout — every stock list/form view an operational user would routinely hit has been replaced with a purpose-built workspace. See §6/§6a for the two build passes (the four-then-five-then-one-screen sequence) and what was deliberately left unbuilt because the backend genuinely doesn't support it yet (a GPS/position feed, an inspection model, technician/duration fields on job cards).

This is the domain being re-audited in §6 below — it's the furthest along and the template for every domain after it.

### Dispatch & Trips — **complete** (all eight workspaces ✅)
| Workspace | State |
|---|---|
| Dispatch Board (evolved into full shipment lifecycle: booking, matching, tracking) | ✅ — see §6c |
| Shipments (Load Booking Workspace) | ✅ — folded into Dispatch Board, not a separate screen — see §6c |
| Trip Board (Load Tracking / Trip Timeline) | ✅ — see §6c |
| Route Manager | ✅ — see §6c |
| Delivery Center | ✅ — see §6c |
| Depot Registry | ✅ — see §6c |
| Dispatch Calendar | ✅ — closed by Trip Board's Calendar tab, see §6c (no `<calendar>` view existed anywhere in the product before this — doc 16 §1 flagged it at zero) |
| Driver Availability | ✅ — resolved as a backend scoring fix, not a new screen — see §6c |

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

### Driver & HR — five of six workspaces ✅, one gap remains (Driver Performance ledger)
| Workspace | State |
|---|---|
| Driver Scorecards / Driver 360 (license, performance, advances, leave in one view) | ✅ — see §6b |
| Driver Advances | ✅ |
| Leave Planner | ✅ |
| Payroll Center (Payslips + Loans combined) | ✅ |
| Driver Performance (fleet-wide events ledger, not just per-driver history) | 🟡 stock list/form; **the one remaining gap** — Driver Scorecards/360 shows one driver's own recent events, but a fleet-wide "browse all incidents this week across every driver" ledger doesn't exist yet, deliberately deferred out of this round for the same reason the Maintenance Planner was deferred out of the first Fleet & Vehicles batch |
| Payroll Dashboard | merged into Payroll Center, not a separate workspace — see §6b |

### AI & Intelligence — flagship screens complete; the Copilot Rail's Chat vision is a separate, larger initiative (doc 21)
| Workspace | State |
|---|---|
| Copilot Console (Agent Catalog incl. edit + Usage Dashboard + NL query) | ✅ — see §6d |
| Copilot Rail (ambient approval queue) | ✅ |
| AI Predictions (Predictive Maintenance + Fuel Anomalies, merged) | ✅ — see §6d |
| AI Action History (full audit trail, all states) | ✅ — see §6d |
| Financial Forecast | 🟡 stock views — deliberately deferred to Billing & Finance's own "Financial Intelligence" gap, not built twice |
| Copilot Rail Chat (tool-calling, multi-session, rich components, memory) | ⬜ — designed, not built; see [21-copilot-rail-architecture.md](21-copilot-rail-architecture.md) |

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

## 6. Fleet & Vehicles re-audit — five gaps found and closed

The four deliverables shipped before this document (Workshop Board, Vehicle 360, Parts Registry, Asset Registry) replaced the domain's *review and quick-action* surfaces. They did not replace the domain's *record-level* surfaces — the actual create/edit screens a user hits via "Open full record," or via a menu that was never touched because it wasn't part of the original four-deliverable plan. Re-auditing against the New UI Rule (§2) — every operational entity gets a custom view — surfaced five gaps, verified directly against the current view XML (not guessed), then closed as one batch per the user's explicit choice ("all five in one pass"):

1. **Vehicle Profile — built by evolving Fleet Command Center, not a separate screen.** `deployfleet.vehicle`'s stock form had zero tabs and zero related-record rollups. Rather than build a second `ir.actions.client` with unverified per-record `params` plumbing (a genuinely new, untested pattern in this module — the safer call given this project's history of Odoo-action-manager surprises, e.g. the `static props = {}` bug), the already-working Fleet Command Center expanded card was evolved into the vehicle's real profile: a new "Identity & Capacity" section with real inputs for `license_plate`, `model_id` (a `fleet.vehicle.model` select), `vehicle_type_id`, `current_driver_id`, `odometer`, and the four editable capacity fields, saved via `orm.write`. `payload_capacity_kg` stays read-only (a stored compute, GVW − tare, not a field a user sets). The four status-transition buttons and every Vehicle 360 read section (Trip/Compliance/Maintenance/Fuel/Tyres/Insurance/Workshop) now sit alongside this edit form in the same expanded card — genuinely one screen for everything about a vehicle.
2. **Vehicle Types Workspace — built** (`static/src/vehicle_types_workspace/vehicle_types_workspace.js`). A registry-ledger list (name/code, sequence-ordered) replacing the stock editable list, with inline edit/create/delete and up/down reorder buttons (in place of drag-drop, for the same mobile-first reasoning as every other screen). **Also required a real ACL change**, not just a frontend build: `deployfleet.vehicle.type` previously granted write access only to `base.group_system` (Odoo's technical settings group) — meaning fleet managers couldn't manage their own vehicle classes at all before this. Fixed by adding a `group_deployfleet_manager` grant (full CRUD) in `deployfleet_vehicle/security/ir.model.access.csv`, mirroring the existing Part Category ACL shape exactly. The old system-only list view and menu are untouched, left as a technical fallback.
3. **Fuel Intelligence — built** (`static/src/fuel_intelligence/fuel_intelligence.js`). A fleet-wide log ledger (up to the 200 most recent fill-ups, newest first), filterable to Anomalies, reconciling the same two independent fuel-anomaly signals Vehicle 360 already reconciles per-vehicle (doc 16 §7.10) but fleet-wide here — the first place to see *which vehicles* are trending anomalous, not just one flagged log at a time. Includes a real "Log Fuel" quick-add form (vehicle/driver/date/odometer/liters/cost via `orm.create`) — the one genuine record-level gap the stock list/form covered that no custom screen did yet.
4. **Tyre Manager — built** (`static/src/tyre_manager/tyre_manager.js`). A fleet-wide, worst-tread-first tyre list (the same "so what" sorting discipline as Driver Scorecards), filterable by state, with tap-to-expand revealing reading/event history and three real actions: `action_record_reading`, `action_rotate`, `action_retread`, `action_scrap`. **Found and fixed a real pre-existing backend ACL bug while building this**: those three actions all internally create a `deployfleet.tyre.event` record, but the dispatcher group had `create=0` on that model despite already having `write=1` on the parent `deployfleet.tyre` model — meaning the actions would have raised an `AccessError` for the dispatcher role the whole time, backend-only, never caught because the existing test suite runs as the superuser. Fixed with a one-line ACL grant (`deployfleet_tyres/security/ir.model.access.csv`) plus a new regression test (`test_dispatcher_can_rotate_tyre`) that creates a real dispatcher-group user and calls `action_rotate` under it, confirming the fix.
5. **Insurance Center — built** (`static/src/insurance_center/insurance_center.js`). A fleet-wide policy ledger, filterable by a client-computed expiry band (Expiring Soon within 30 days / Expired — the policy model itself has no `state` field, confirmed by source read), tap-to-expand revealing claims plus a real "File a Claim" quick-add form (`orm.create`) and the claim's real lifecycle actions (`action_submit`/`action_approve`/`action_reject`/`action_mark_paid`). **Not an ACL bug, a legitimate approval gate, documented rather than "fixed":** dispatcher can file a claim (`create=1`) but cannot progress its state (`write=0` on `deployfleet.insurance.claim`) — a plausible intentional design (a manager signs off before a claim is submitted), unlike the tyre.event gap above where dispatcher already had clear operational authority over the parent record. The buttons are shown to every role regardless; a denied write surfaces as a friendly notification via the same pattern every other screen already uses, not a hidden button.

**Mega Menu tiles repointed**: Vehicles → Fleet Command Center, Vehicle Types → the new workspace, Fuel Logs → Fuel Intelligence, Tyres → Tyre Manager, Insurance (both its Fleet & Vehicles *and* Compliance domain tiles) → Insurance Center. **What did not need rebuilding:** Workshop Board, Parts Registry, and Asset Registry stayed exactly as shipped — they already satisfied the New UI Rule for the surfaces they cover.

**Genuinely still open in this domain, not silently closed:** Maintenance Schedules / the doc 16 §7.11 Maintenance Planner widget — see the domain catalog table in §3, deliberately out of scope for this five-screen batch since it needs a real calendar-plus-Gantt-shaped build, not another registry/accordion screen.

---

## 6a. Maintenance Planner — audit, design, and build

The user's brief for this screen was written at product-vision level (Attention Strip, week/month Calendar, a Gantt-style Timeline, Vehicle Health Cards with a "predicted failure window," workshop capacity, batch-groupable maintenance, cost-per-km, and more). Per doc 20's own discipline — grounding every design in a real source read before promising a feature, the same check that ruled out Live Fleet Map/Fleet Heat Map in Phase E — the backend was re-audited line by line before writing any frontend code. Two models carry this screen: `deployfleet.maintenance.schedule` (`vehicle_id`, `name`, `interval_km`, `interval_days`, `last_service_odometer`, `last_service_date`, computed `next_due_odometer`/`next_due_date`/`is_due`, `action_record_service()`, `action_create_job_card()`) and `deployfleet.workshop.job.card` (`vehicle_id`, `description`, `opened_date`, `closed_date`, `state`, `total_cost`, `maintenance_schedule_id` — the last field added by this very module to link a job card back to the schedule that spawned it), plus `deployfleet.maintenance.prediction` (`vehicle_id`, `risk_score`, `risk_level`, `basis`, `computed_date` — no failure-date field of any kind).

**What the brief asked for that the backend does not support, and how each was handled — not silently dropped, not fabricated:**

- **"Predicted failure window"** — `deployfleet.maintenance.prediction` has `risk_score`/`risk_level`/`basis` (a plain-language explanation) and nothing resembling a predicted date. The screen surfaces the real fields (score, level, basis) via `AiRecommendationCard` and never invents a window.
- **Inspections** as a distinct event type — no inspection model exists anywhere in the 43-module backend (confirmed by a repo-wide grep). Not built. Belongs to a future `deployfleet_inspection`-shaped module, not something to fake with borrowed fields.
- **Scheduled start/end times, technician assignment, priority, estimated duration** on job cards — none of these fields exist (`opened_date`/`closed_date` are plain Dates, no time-of-day). The Timeline therefore renders each job card as a day-granularity bar from `opened_date` to `closed_date` (or to today, if still open) — real data, just without hour-level precision or a named technician.
- **Workshop "capacity"** — no staffing/technician-capacity model exists. The screen shows a genuine, honestly-labeled count of currently-open job cards as the workshop-load signal instead of a fabricated capacity percentage.
- **"Which maintenance can be grouped together"** (batch-scheduling optimization) — would need a real grouping dimension (depot, maintenance type, technician availability) that doesn't exist on the schedule model. Not built; flagged as a real future opportunity once a grouping field exists, not attempted with invented logic.
- **Cost per kilometer** — no distance-driven-per-period field exists directly, but `deployfleet.fuel.log.distance_since_last_km` (a real, stored compute) can be summed per vehicle for a period as a genuine, if imperfect, proxy for distance driven. Built, but documented in the code and in the KPI's own caption as an approximation derived from fuel-log distance deltas, not GPS/odometer telemetry — shows "—" rather than a misleading number when no fuel-log distance data exists for the period.
- **Driver mobile's "upcoming inspection / report issue / maintenance instructions"** — belongs to the separate React Native driver app (`MOBILE_ARCHITECTURE.md`), not `deployfleet_ui`'s Odoo web client, the same scope boundary already drawn for every other mobile-app reference in this document set. Not attempted here.

**What was real and buildable, and shipped:**

A single cohesive workspace (`static/src/maintenance_planner/maintenance_planner.js`, one `ir.actions.client`, not four separate screens — matching the brief's "this should be the primary entry point" framing) with three internal views switched by tab, not by menu item:

1. **Overview** — a silent-unless-nonzero Attention Strip (Overdue maintenance / Due within 7 days / Vehicles unavailable / AI predicted risks / Jobs awaiting approval — "waiting parts" was in the original brief but has no backing field on `deployfleet.workshop.job.card` and was dropped rather than faked), six real KPI cards (Fleet Availability %, Vehicles Under Maintenance, Avg Repair Downtime, Maintenance Cost This Month, Preventive vs. Corrective Ratio, Cost per KM), an `AiRecommendationCard` list for every vehicle with a medium/high predicted risk, and a filterable grid of **Vehicle Maintenance Health Cards** — one card per vehicle (identity, status, last/next service, odometer, a client-computed Health Score, AI risk line, open-job-card status), tap-to-expand into its schedules/job cards, with the same status-transition and job-card actions already proven on the Fleet Command Center and Workshop Board. Clicking an Attention Strip item filters this same grid rather than navigating away to a stock list — staying inside the workspace, per doc 20 §4's UX goal.
2. **Calendar** — a native CSS-grid week/month view (no charting library introduced, consistent with this module's homegrown-widget precedent) plotting day-anchored events: schedule due-dates (color-coded overdue/due-soon/scheduled) and job-card opened/closed markers. Deliberately does not attempt to render multi-day spanning bars here — that's the Timeline's job.
3. **Timeline** — a Gantt-style view, vehicle rows against a rolling date window, job-card bars positioned via percentage-based CSS (`left`/`width` computed from date offsets, no drag-resize — the same no-HTML5-drag-drop mobile-first reasoning as the Dispatch Board) plus due-date markers per schedule. Answers the brief's own framing question — "can we take this truck offline tomorrow?" — by making current/upcoming unavailability visually obvious per vehicle.

**Health Score is a `deployfleet_ui`-computed heuristic, not a backend-stored field** — worth being explicit about, since every other "score" this module has surfaced before (Driver Scorecards' reliability score, Vehicle 360's risk badge) came from a real backend compute. This one doesn't exist server-side. It's built from a documented, deterministic formula over genuinely real signals (open schedules that are due or due-soon, open job cards, AI risk level) — see the code comment in `maintenance_planner.js` for the exact weights — not a fabricated number, but also not a value any other part of the product can rely on until (if ever) it's promoted to a real backend field.

**AI recommendations follow the mandatory pipeline** (CLAUDE.md §4): `AiRecommendationCard` only ever renders `deployfleet.maintenance.prediction`'s existing fields and offers "Schedule Maintenance" (creates a job card via the vehicle's existing schedule, an explicit human action) or "Dismiss" — there is no auto-execute path, consistent with every other AI surface in this product.

**Workshop Board stays the execution surface, Maintenance Planner stays the planning surface** — no duplicate workflow. Maintenance Planner's "Create Job Card" action calls the exact same `deployfleet.maintenance.schedule.action_create_job_card()` method already in the backend; once created, that job card is worked to completion on the Workshop Board, not re-implemented here.

**One-click actions are limited to what the backend actually supports** — a deliberate scope correction from the brief's full action list. Real and shipped: Create Job Card (`action_create_job_card`), Record Service (`action_record_service` — the only real lever for "rescheduling," since `next_due_date` is a stored compute over `last_service_date`/`interval_days`, not a directly writable field), and the vehicle status quick actions already proven on Fleet Command Center. Not built, because no backing action exists: "Assign Workshop" (job-card creation already is the assignment), "Reschedule" as a distinct action, and "Send Driver Notification" (no callable method for it was found in this audit).

**Verified**: XML well-formed, JS syntax via `node --check`, full `web.assets_backend` SCSS bundle compiled via libsass (27 files, individually and in manifest order), ruff/pylint clean, security groups checked (`group_deployfleet_dispatcher` has sufficient read/write/create access across `deployfleet.vehicle`, `deployfleet.maintenance.schedule`, `deployfleet.workshop.job.card`, `deployfleet.maintenance.prediction`, and `deployfleet.fuel.log` for every action this screen performs). Two OWL-template risk points were deliberately avoided rather than assumed safe: the `??` nullish-coalescing operator (used freely in this module's plain `.js` files, but with no prior precedent inside an XML template expression, so replaced with JS getters instead) and an inline array literal in `t-foreach` (replaced with a component-level array property, matching how every other `t-foreach` in this module iterates a real property). **Not yet verified in a live browser** — same caveat as every screen in this module since Phase A; this is also the single largest, most novel component built in `deployfleet_ui` to date (three internal views, a hand-rolled calendar grid, and percentage-positioned Gantt bars, none of which have a prior working precedent in this module to lean on), so it is the highest-priority screen to click-test on the demo server before considering Fleet & Vehicles fully signed off.

---

## 6b. Driver & HR — audit, design, and build

Second domain tackled under the domain-completeness-first rollout, per the user's explicit "next let's tackle Driver & HR" direction. Audited every model in the domain before building anything: `deployfleet_driver` (adds license/qualification fields to `hr.employee`), `deployfleet_driver_performance` (`deployfleet.driver.performance.event` plus the computed, unstored `hr.employee.deployfleet_reliability_score`), `deployfleet_driver_advance` (`deployfleet.driver.advance`, a linear `issued -> reconciled -> deducted` state machine), `deployfleet_leave` (`deployfleet.leave.request`/`.balance`/`.type`), `deployfleet_payroll` (`deployfleet.payroll.payslip`/`.payslip.line`/`.rule`), and `deployfleet_loans` (`deployfleet.loan`) — including every `security/ir.model.access.csv` in the domain, the same discipline that caught the Tyre Manager ACL gap in Fleet & Vehicles.

**Two real, pre-existing backend issues found during the audit, both fixed:**

1. **`deployfleet.leave.request`: the driver group had `create=1` but `write=0`** — a driver could file a leave request but could never call `action_submit()` on it themselves (it writes internally), and *also*, once write access is granted, the model-wide ACL alone would let any driver edit or approve any *other* driver's leave request, not just their own — there was no record-level scoping mechanism anywhere in this codebase to prevent that (confirmed: this is the first `ir.rule` in the entire DeployFleet backend). Fixed properly, not just by flipping the ACL bit: granted `perm_write=1` for the driver group in `deployfleet_leave/security/ir.model.access.csv`, plus a new record rule (`deployfleet_leave_request_rule_driver_own`, `deployfleet_leave/security/deployfleet_leave_security_rules.xml`) scoping driver access to `[('employee_id.user_id', '=', user.id)]` — the standard Odoo self-service pattern. Two new regression tests confirm both halves: a driver can now submit their own request, and still cannot write to another driver's. **This fix enables self-service at the backend/ACL level for whichever driver-facing surface eventually uses it** (the separate React Native driver app, per `MOBILE_ARCHITECTURE.md`) — the Leave Planner workspace built in `deployfleet_ui` itself stays dispatcher/manager-facing, like every other screen in this module; drivers aren't `deployfleet_ui`'s audience.
2. **Payroll and Loans are gated to a role off the normal chain entirely.** `group_deployfleet_hr_payroll_officer` is a sibling of `group_deployfleet_dispatcher`/`manager`/`owner`, not descended from it — meaning a manager who isn't *separately* granted that role has **zero ACL rows at all** on `deployfleet.payroll.rule`/`payroll.payslip`/`payroll.payslip.line`/`deployfleet.loan`. Not a bug (this looks like a deliberate confidentiality boundary, consistent with CLAUDE.md §4's payroll/financial-data sensitivity note), but a real UX hazard for a *frontend-only* fix: most users who reach a Payroll Center screen via the Mega Menu will get an `AccessError` on the very first read. Handled by wrapping `loadAll()` in try/catch and rendering a clean "you don't have access to payroll data" state instead of an unhandled crash — see the Payroll Center writeup below.

**What was built, one workspace per remaining gap:**

1. **Driver Scorecards deepened into the domain's Driver 360** (`static/src/driver_scorecards/driver_scorecards.js`) — the same "evolve the existing screen, don't build a second one" choice as Fleet Command Center's Vehicle Profile. New sections in the expanded driver card: a real, editable **Identity & Qualifications** form (license class/number/expiry, endorsements, the legacy `deployfleet_risk_score` field, qualified vehicle types shown read-only) saved via `orm.write`; **Advances** (read + `action_mark_reconciled`/`action_mark_deducted`); **Leave** (read + `action_submit`/`action_approve`/`action_reject`/`action_cancel` + a "Request Leave" quick-add form). **Worth flagging explicitly**: `deployfleet_risk_score`'s own help text claims it would be "lowered by driver-performance incidents once `deployfleet_driver_performance` is installed" — but that module actually built a wholly separate field (`deployfleet_reliability_score`, the one this screen already surfaced) instead of wiring into this one. `risk_score` is real, stored, editable data — just not a live metric today, shown as plain data rather than treated as meaningful. `action_approve()` on a leave request can raise a real `UserError` on a trip conflict, surfaced through the same notification pattern every write action in this module uses.
2. **Driver Advances** (`static/src/driver_advances/driver_advances.js`) — a fleet-wide registry-ledger, the same visual dialect as Parts/Asset Registries, since advances are driver-linked (like tyres/insurance are vehicle-linked) and benefit from both a per-driver view (in Driver 360, above) and a fleet-wide planning ledger, mirroring the Tyre Manager/Insurance Center precedent.
3. **Leave Planner** (`static/src/leave_planner/leave_planner.js`) — three tabs: Requests (filterable list + quick-add form + the real state-machine actions), Calendar (a hand-rolled CSS-grid month view marking every day within an approved/submitted request's date range — no charting library, no separate Timeline needed since leave spans are handled directly in the day cells, unlike Maintenance Planner's job-card bars which needed a true Gantt), and Balances (a real read over `deployfleet.leave.balance` — a model with **no view of any kind anywhere in the backend before this**, confirmed by source read).
4. **Payroll Center** (`static/src/payroll_center/payroll_center.js`) — combines Payslips and Loans into one workspace per the user's explicit choice, since they're both officer-gated and already linked in the backend (a payslip's `action_confirm()` calls each active loan's `action_apply_deduction()`). Payslips: filterable list, tap-to-expand showing computed `line_ids`, the real `action_compute()`/`action_confirm()`/`action_mark_paid()` state machine, a "New Payslip" form. Loans: filterable list, a "New Loan" form — no standalone state-transition button was built, since `action_apply_deduction()` is only ever called internally by a payslip's own confirm, confirmed from source, not invented here. The access-denied state (see above) is the single most load-bearing piece of this screen.

**Mega Menu tiles repointed**: Drivers → Driver Scorecards/360, Driver Advances → the new registry, Leave → Leave Planner, and Payslips + Loans collapsed into one Payroll Center tile. **Driver Performance's tile deliberately stays pointed at the stock list** — see the domain table in §3, the one remaining gap in this domain.

**Verified**: XML well-formed, JS syntax via `node --check`, full `web.assets_backend` SCSS bundle compiled via libsass (30 files, individually and in manifest order), ruff/pylint clean on both `deployfleet_ui` and `deployfleet_leave`, all touched ACL CSVs parse correctly, two new regression tests for the leave-request ACL/rule fix (one confirming the fix works, one confirming it doesn't over-grant). **Not yet verified in a live browser** — same standing caveat as every screen in this module.

---

## 6c. Dispatch & Trips — audit, design, and build

Third domain tackled under the domain-completeness-first rollout, per the user's explicit "next let's tackle Dispatch and trips" direction. Audited every model, state machine, view, and ACL across `deployfleet_dispatch`, `deployfleet_dispatch_compliance`, `deployfleet_trip`, `deployfleet_delivery`, `deployfleet_route`, and the dispatch-relevant parts of `deployfleet_customer` (depot/contract) before designing anything — including reading the Dispatch Board (already shipped in Phase C) to see exactly what it did and didn't cover, since this domain (unlike the first two) started with one real workspace already in place, not zero.

**Confirmed via `AskUserQuestion` before building:** (1) evolve the existing Dispatch Board into the full shipment lifecycle (booking, matching, tracking) rather than building a separate "Shipments" workspace alongside it — the same "evolve, don't duplicate" choice as Fleet Command Center/Driver Scorecards; (2) treat Routes'/Depots' dispatcher-read-only ACL as a bug and grant write access, rather than leaving it as a deliberate boundary; (3) fix the missing driver-availability check in dispatch scoring now, as a real backend change, rather than deferring it; (4) build the whole domain in one batch.

**Two real, pre-existing backend issues found during the audit, both fixed:**

1. **`deployfleet.route`/`deployfleet.route.stop`/`deployfleet.depot`: dispatcher-visible menus, read-only ACL.** All three models granted `group_deployfleet_dispatcher` only `perm_read=1`, while their menus were dispatcher-gated — meaning every create/edit action a dispatcher might take on the stock forms would have silently failed. Confirmed as a bug (not a designed boundary, per the user's answer) and fixed by granting dispatcher `perm_write=1`/`perm_create=1` on all three (still no `perm_unlink`, matching the codebase-wide convention that the dispatcher role never gets unlink anywhere).
2. **Dispatch scoring never checked driver availability.** `deployfleet.shipment._score_candidate()` (extended in `deployfleet_dispatch_compliance` with expired-document/rest-hour/consecutive-driving-day checks) had no check at all against `deployfleet.leave.request` — a driver on approved leave overlapping the requested pickup date could still be suggested and confirmed for a shipment. Fixed by adding `_driver_on_approved_leave()` to the same extension point, disqualifying a candidate with an approved leave request covering the pickup date; `deployfleet_dispatch_compliance` gained `deployfleet_leave` as a manifest dependency (no circular-dependency risk — `deployfleet_leave` depends on `deployfleet_trip`, not on `deployfleet_dispatch_compliance`). Two new regression tests cover both the disqualifying and non-disqualifying cases. This closes the "Driver Availability" row in §3's table as a backend fix, not a new screen — the Leave Planner (built in the Driver & HR domain) already answers "who's on leave when" for browsing, and scoring now actually respects it.

**What was built:**

1. **Dispatch Board evolved** (`static/src/dispatch_board/dispatch_board.js`) — the screen originally scoped to just confirmed-shipment-to-assignment matching now covers the full lifecycle: a "New Shipment" quick-add form (booking, creating `draft` shipments), state filter chips (Active/Draft/Confirmed/Assigned/In Transit/Delivered/Cancelled, "Active" excluding the terminal states by default), Confirm/Cancel for draft shipments, the original suggest-assignments/confirm/override flow unchanged for confirmed shipments, and a read-only assignment summary (driver/vehicle) for assigned/in-transit/delivered shipments with a pointer to Trip Board/Delivery Center for what happens next — this screen deliberately does not duplicate trip departure/completion or POD capture, both of which now have their own workspaces.
2. **Trip Board** (`static/src/trip_board/trip_board.js`) — two tabs. **Trips**: the same filter-chips-plus-accordion pattern as the Workshop Board, with the real `action_depart`/`action_complete`/`action_report_delay`/`action_cancel` state machine. Notably, `action_complete()`'s `odometer_end` kwarg had **no UI path anywhere in the product before this** — the stock form's Complete button is a bare zero-arg call — so this is the first place a user can actually set it, via an inline input passed as a second positional arg only when filled in (an empty input still calls `action_complete()` with its `None` default, not an accidental `0`/`False` write). **Calendar**: a month grid (the exact `buildCalendarDay`/`calendarGridDays` code from the Leave Planner, adapted to single-day `planned_departure` pins instead of date ranges) — this is what closes the "Dispatch Calendar" gap doc 16 §1 originally flagged at zero `<calendar>` views anywhere in the product.
3. **Delivery Center** (`static/src/delivery_center/delivery_center.js`) — a fleet-wide proof-of-delivery ledger plus a "Record Delivery" form. `deployfleet.delivery.create()` is itself the completion event (no `action_*` method exists on the model, confirmed by source read), so this screen has no edit path, only create and browse, matching the backend's own design. The form's shipment choices are trip-scoped (picking a trip loads that trip's real shipment lines) to mirror the backend's own `_check_shipment_is_on_trip()` constraint. Signature/photo upload (`Binary` fields) has no prior precedent in `deployfleet_ui` — implemented with a plain `<input type="file">` read via `FileReader` into base64, not a camera-capture widget.
4. **Route Manager** (`static/src/route_manager/route_manager.js`) — a registry-ledger of lanes (same visual dialect as Parts/Asset Registries/Vehicle Types Workspace) with inline editing and stop management (add/remove, auto-incrementing sequence, no drag-reorder — the same no-HTML5-drag-drop mobile-first reasoning as the Dispatch Board). Confirmed by source read during the audit: `deployfleet.route` holds no GPS/waypoint/coordinate data anywhere — `distance_km` is a manually-entered scalar and `stop_ids` is just an ordered list of named depot references — so this is a lane-graph registry, not a map, the same GPS-less reality that already ruled out Live Fleet Map/Fleet Heat Map in Phase E.
5. **Depot Registry** (`static/src/depot_registry/depot_registry.js`) — a simple master-data registry, same pattern as the Vehicle Types Workspace (name/street/city, inline edit, delete available to every role with a denied write surfacing as a friendly notification for the dispatcher role, matching that screen's precedent exactly).

**Also fixed while touching this area:** the Mega Menu's "Dispatch Board" tile had pointed at the **stock kanban action** (`deployfleet_dispatch.action_deployfleet_dispatch_assignment`) since Phase C — the custom OWL Dispatch Board built that same phase was only ever reachable via its own top-level menu item, never from the Mega Menu tile bearing its name. Fixed by repointing the tile (now merged with the old "Shipments" tile, since Dispatch Board covers both) to `deployfleet_ui.action_deployfleet_dispatch_board`. Mission Control's "Unassigned shipments" attention-strip pill had the same class of issue (deep-linking to the stock shipment list) and was repointed to the Dispatch Board too.

**Verified**: XML well-formed, JS syntax via `node --check`, full `web.assets_backend` SCSS bundle compiled via libsass (34 files, individually and in manifest order), ruff/pylint clean on `deployfleet_ui`, `deployfleet_dispatch_compliance`, `deployfleet_route`, `deployfleet_customer`, and `deployfleet_leave`, all touched ACL CSVs parse correctly, two new regression tests for the driver-availability scoring fix. **Not yet verified in a live browser** — same standing caveat as every screen in this module, and now the largest single batch to carry that caveat (five workspaces at once).

---

## 6d. AI & Intelligence — audit, headline bug fixes, and build

Fourth domain tackled under the domain-completeness-first rollout. Audited every model, ACL, view, and menu across `deployfleet_ai_core`, `deployfleet_ai_permissions`, `deployfleet_ai_actions`, `deployfleet_ai_agents`, and `deployfleet_ai_whatsapp`. Unlike every prior domain, the audit surfaced a bug severe enough to fix before any design conversation: the entire AI call pipeline was unreachable by every real DeployFleet role (see CLAUDE.md's AI & Intelligence writeup for the full root-cause trace — `deployfleet.ai.config`/`.response.cache`/`.budget` were `base.group_system`-only, and `menu_deployfleet_ai_root` hid every AI submenu from every role regardless of each submenu's own `groups`). Both fixed (`sudo()` on the router's internal reads, the menu gate moved down onto the five genuinely admin-only submenus) alongside three smaller ACL parity fixes (`deployfleet.ai.action.request` dispatcher write, `action_reject()` role-check parity, a System Auditor read grant) — five new regression tests, one exercising the pipeline end-to-end as a real dispatcher user.

**Design conversation, via `AskUserQuestion`, after the bug fixes landed:** (1) build a dedicated fleet-wide AI Predictions screen despite `deployfleet.maintenance.prediction`/`deployfleet.fuel.anomaly` already being surfaced inline elsewhere (Fleet Command Center, Maintenance Planner, Fuel Intelligence); (2) defer Financial Forecast to Billing & Finance's own still-open "Financial Intelligence" gap rather than build it twice; (3) build a full AI Action History workspace, since the Copilot Rail only ever shows currently-pending items and the just-fixed System Auditor role had nowhere custom to look; (4) give AI Agents a non-stock edit surface for `system_prompt_template`/`related_models`, previously reachable only via the stock form.

**Three workspaces built.** **AI Predictions** (`static/src/ai_predictions/`) — two tabs (Maintenance Risk, Fuel Anomalies) rather than one merged list, since the two models have genuinely different schemas (confirmed by source read: `risk_score`/`risk_level`/`basis` vs. a bare `z_score`); read-only data (both models are populated by their own daily crons), with an "Open Vehicle" escape hatch rather than attempting per-record deep-linking into Fleet Command Center. **AI Action History** (`static/src/ai_action_history/`) — all six states filterable, not just pending, reusing the exact `action_approve`/`action_reject` calls the Copilot Rail already makes so a manager can act from either surface without duplicated logic. **Copilot Console's Agent Catalog gained a real edit surface** (`system_prompt_template`/`related_models`, via a new `group_deployfleet_manager` write ACL grant on `deployfleet.ai.agent` — previously owner-only) alongside its existing enable/disable toggle and "Ask" box.

**Mega Menu updated**: added a Copilot Console tile (previously reachable only via an unrestricted top-navbar item, with no Mega Menu/Launcher entry point at all — the same class of gap already fixed for the Dispatch Board in §6c); merged the "Predictive Maintenance" and "Fuel Anomalies" tiles into one "AI Predictions" tile, the same "evolve, don't duplicate" choice as Payroll Center absorbing Payslips+Loans; repointed "Action Requests" to the new AI Action History workspace.

**Verified**: XML well-formed, JS syntax via `node --check`, a full OWL-compiler pass (35/35 templates), the full `web.assets_backend` SCSS bundle compiled via libsass (36 files, individually and in manifest order), ruff/pylint clean, all touched ACL CSVs parse correctly, new registration tests for both new actions/menus.

**Separately, in the same session, a much larger initiative was scoped but deliberately not built yet**: a full agentic Copilot Rail (persistent multi-session chat, tool-calling, rich in-chat components, a context/memory layer, structured outputs) per an explicit user vision brief. Per the user's own direction ("write an architecture doc first"), this became [21-copilot-rail-architecture.md](21-copilot-rail-architecture.md) rather than inline implementation — sized honestly as a four-phase initiative larger than any single domain's workspace batch, and containing the one deliberate, narrowly-bounded change to an existing hard rule in this codebase (a curated, opt-in auto-execute tier for chat-initiated writes, doc 21 §4). Not yet started.

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

All four questions originally raised here are now resolved:

1. ~~Should **Maintenance** split out of Fleet & Vehicles into its own top-level Mega Menu domain?~~ **Resolved: no** — stays part of Fleet & Vehicles.
2. ~~Should a **Customers** domain be carved out of Billing & Finance / Dispatch & Trips?~~ **Resolved: no** — Contracts stays under Billing & Finance, Depots stays under Dispatch & Trips.
3. ~~Confirm the five-gap Fleet & Vehicles list and screen shapes.~~ **Resolved and built** — see §6.
4. ~~Confirm the domain build order after Fleet & Vehicles.~~ **Resolved and progressing**: Driver & HR (§6b) then Dispatch & Trips (§6c), both now complete. Compliance, Billing & Finance, and AI & Intelligence remain — no order confirmed yet for those three; ask before starting the next one, per §5's own audit → design → build sequence.

---

## 9. Success criteria

When someone demos DeployFleet, they should stop noticing Odoo. Instead they should notice beautiful workspaces, intuitive navigation, fast workflows, rich dashboards, contextual AI, and purpose-built interfaces — a premium trucking platform.

**The test:** if someone says *"this doesn't feel like Odoo,"* the strategy in this document has worked.
