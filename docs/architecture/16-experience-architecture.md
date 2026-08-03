# 16 — Experience Architecture

**Status:** Strategy document, not an implementation plan. No code, no OWL components, no CSS tokens as files exist yet as a result of this document — it defines *what to build and why*, the same way [08-ai-architecture.md](08-ai-architecture.md) defined the AI architecture before `deployfleet_ai_core` was written. Frontend work on any dashboard, board, or workspace named below should be checked against this document first, the same discipline [CLAUDE.md](../../CLAUDE.md) §2 already asks for against the domain-model and module-structure docs.

**Mandate.** DeployFleet's 43 modules are functionally complete (see [CLAUDE.md](../../CLAUDE.md) §10) and now deployed as a live demo. But functionally complete is not the same as commercially credible. This document is the answer to a specific, narrow question: **what turns DeployFleet from "an Odoo installation with trucking fields" into "a premium logistics operating system a fleet owner would show a customer with pride"?** Everything below is written by someone acting as senior UX architect, product designer, OWL frontend architect, and enterprise software designer — evaluating, not implementing.

**Grounding.** Two things anchor this document in fact rather than aspiration, both established before a word of strategy was written:

1. **DeployFleet's actual current UI state**, audited directly against the live module tree (§1).
2. **DeployGuard's actual OWL component code**, read file-by-file in the donor repository (`creativesites/DogFrce-Security-Services-Custom-Odoo-Modules`), not assumed from module names or prior summaries. §3 reports what was actually found — including places where the popular understanding of a DeployGuard pattern (e.g., "Timeline Views," "Quick Actions") turns out to be a looser fit than the name implies. Where the fit is loose, this document says so and reframes rather than forcing a match.

---

## 1. Executive diagnosis: what DeployFleet actually looks like today

This is not a hypothetical "stock Odoo feels generic" complaint. It's a literal inventory of the live module tree:

- **Zero custom OWL components exist anywhere in the 43-module tree.** The only file in any module's `static/` directory is `deployfleet_core/static/description/icon.png` — the module's app icon. Every dashboard, every board, every workspace named in this document's mandate is, today, either a standard Odoo list/form view or does not exist as a distinct screen at all.
- **Every view in the codebase is `<list>` or `<form>`**, with exactly **three** `<kanban>` views in the entire product (`deployfleet.dispatch.assignment`, `deployfleet.shipment`, `deployfleet.vehicle`), all stock Odoo kanban with 3–4 fields per card and no drag-drop, no color logic beyond a default state-based grouping, no avatars, no map, no timeline.
- **Zero `<calendar>`, `<map>`, `<graph>`, `<pivot>`, or `<gantt>` views exist anywhere.** For a logistics platform, this is the single starkest gap: there is no calendar for trips, leave, or maintenance schedules; no map for vehicles, routes, or depots; no graph/pivot for any of the financial, fuel, or compliance data Phase 2–5 spent months building.
- **The "Dispatch Board"** — arguably the product's single most important screen, the one a dispatcher will stare at eight hours a day — is today a bare kanban card showing shipment, driver, vehicle, and a numeric score, grouped by state. [09-dispatch-module-design.md](09-dispatch-module-design.md) explicitly and deliberately deferred the custom OWL board past Phase 1 "once the underlying assignment model has been used for real dispatch decisions." That condition has now been met — 43 modules and a full demo dataset later, this document is that fast-follow.
- **Navigation is a single flat Odoo app menu** (`menu_deployfleet_root`, `deployfleet_core/views/deployfleet_menus.xml`) with every other module's menu nested underneath as a child — i.e., the standard Odoo horizontal top bar and dropdown, not a mega menu, not a launcher, not a command palette.
- **There is no AI-facing UI at all.** Six AI agents, a permission layer, and a mandatory approval pipeline exist in the backend ([08-ai-architecture.md](08-ai-architecture.md)) with a standard Odoo form/list view over `deployfleet.ai.action.request` — there is no dedicated surface where a human actually *works* the approval queue, sees agent output ranked by confidence, or asks a question in natural language.
- **Mobile apps (driver/dispatcher/customer) exist as React Native scaffolding** ([MOBILE_ARCHITECTURE.md](../../MOBILE_ARCHITECTURE.md)) with the same "glassmorphic, not default native styling" intent stated but, per that document's own status, largely unbuilt against real screens yet.

This is the honest starting line. It's also, properly read, good news: there is no legacy custom UI to migrate or unwind — every recommendation below is additive against a clean slate, not a renovation fighting existing investment.

---

## 2. Design philosophy — the principles that resolve every decision below

Six principles, stated once here so later sections can invoke them by name instead of re-arguing them per screen.

**1. Two visual layers, not one, and not two competing ones by accident.** DeployGuard's own codebase (§3.0) drifted into two incompatible visual languages — a dark, saturated, gradient-heavy "OS" aesthetic (launcher, mega menus, home command center) and a flat, desaturated, Stripe-style finance aesthetic (Billing Command Center) — apparently through an undocumented later pivot that was never back-ported. DeployFleet inherits the *idea* that navigation/launch moments and data-entry/review moments want different visual treatments, but resolves it deliberately instead of by accident:

- **Command Layer** — full-screen or overlay surfaces whose job is *orientation and launch*: the app launcher, mega menus, command-center home screens, the AI co-pilot rail when expanded. These earn the glassmorphism, the gradient accent chips, the blur, the motion. A user is here for seconds, not hours — visual richness doesn't fight task completion.
- **Workspace Layer** — surfaces whose job is *sustained work*: list views, form views, the Dispatch Board's cell-level detail, billing tables, compliance registers. These are flat, high-contrast, desaturated except for semantic status color, dense where density serves scanning, generous where a single number needs to be read from across a cab. A dispatcher doing this for eight hours must not be fighting a translucent card for contrast.

Every area analyzed in §7 states explicitly which layer it belongs to. Getting this assignment wrong — e.g., glassmorphic blur behind a 40-row compliance table — is the single most common way "premium" tips into "annoying."

**2. AI is a visible, distinct author — never an invisible hand.** [CLAUDE.md](../../CLAUDE.md) §4 and [08-ai-architecture.md](08-ai-architecture.md) already make the mandatory suggestion→approval→execute→audit pipeline non-negotiable at the data layer. The visual language must carry that same guarantee: **anything AI-suggested or AI-generated gets a distinct, consistent visual treatment (a color, a badge, an icon) everywhere in the product**, so a user never has to wonder whether a number, a suggestion, or a pre-filled field came from a human, a rule, or a model. This is proposed as a genuinely new convention (§4) — DeployGuard's codebase has no equivalent, because its AI engine had no dedicated UI at all.

**3. Reduce clicks by collapsing navigation, not by cramming forms.** Every "reduce clicks" opportunity in §7 is a navigation or workflow-collapse opportunity (fewer screens between intent and action), never information-density-at-the-cost-of-legibility. A driver on a moving vehicle's dashboard tablet and a dispatcher scanning fifty rows have different tolerances for density; neither is served by cramming.

**4. Status is a color language, applied identically everywhere.** DeployGuard converged, largely by convention, on green/amber/red/blue-purple as compliant-or-on-time / needs-attention-soon / critical / informational. DeployFleet adopts this explicitly as a platform-wide rule rather than a per-dashboard convention re-invented each time (§4), extended with the one deliberate inversion DeployGuard itself modeled well: color follows *business meaning*, not metric direction — a rising cost is red even though the number went up, exactly as DeployGuard's payroll-expenditure trend arrows did.

**5. Every dense screen has a "so what" layer above it.** The Main OS Command Center's quiet, only-appears-if-nonzero attention strip (§3.3) is the strongest single idea found in the donor codebase: a cross-domain, one-glance answer to "what needs me right now," computed from parallel counts, silent when there's nothing to act on. Every command-center-class screen in §7 gets one.

**6. Mobile-first means truck-stop-first, not phone-mockup-first.** The target user checks a phone with one hand, in sunlight, possibly with gloves on, on a 3G connection outside Lusaka, not at a desk. Every mobile recommendation in §7 is evaluated against that condition, not against how it looks in a clean simulator screenshot — large touch targets, offline-tolerant data patterns, and legible-in-sunlight contrast take priority over density or animation richness on any driver-facing screen.

---

## 3. DeployGuard pattern reuse inventory

Grounded in a direct read of the donor codebase's `.js`/`.xml`/`.css` (paths cited). Where a named pattern turns out to be a narrower or different thing than its name suggests, this section says so plainly rather than forcing the requested mapping.

### 3.0 The uncomfortable finding first: two design systems, not one

DeployGuard has no single imported design-system source of truth. `security_base/static/src/css/design_system.css` is a real, deliberate token file (self-labeled "Clean Corporate Light — Goldman Sachs meets modern SaaS") but it only reskins *stock* Odoo widgets — none of the custom dashboards import it. Every custom dashboard instead re-declares its own near-identical slate/navy palette (`#0f172a`, `#1e293b`, `#64748b`, `#e2e8f0` recur verbatim across a dozen files) under its own 2–4 letter CSS prefix (`.bcc-*`, `.fd-*`, `.rb-*`, `.dgcc-*`, `.dfal-*`...) — a de facto standard maintained by copy-paste discipline, not a real shared library. Layered on top of that is the genuine visual-language fork described in Principle 1 above.

**The lesson for DeployFleet, stated once so it doesn't need repeating per component below:** build the design-system module *first* (§4) and have every subsequent dashboard consume its tokens by import, not by copying the last dashboard's CSS file and renaming the prefix. This is a process discipline, not a design opinion, and it's the one thing DeployGuard's own team visibly meant to do (the design-system file exists!) and didn't finish following through on.

Also worth knowing before evaluating "chart" and "real-time" claims below: **no charting library is used anywhere in DeployGuard** (no Chart.js, ApexCharts, D3 — zero matches). Every visual "chart" is hand-rolled div/SVG. **No real-time push exists either** — no websockets, no `bus_service` subscriptions in custom code; every "live" dashboard is load-on-open plus a manual refresh. Both are legitimate, lightweight choices worth deliberately deciding whether to keep or upgrade (§7), not defaults to assume away.

### 3.1 Mega Menu → adapt as-is, consolidate the shared CSS

**What it actually is:** not a navbar dropdown — a full-screen modal overlay (`position:fixed; inset:0`) triggered as a client action, not a menu widget. Dark `rgba(15,23,42,.45)` scrim with `backdrop-filter: blur(12px)` behind a centered white rounded card (max-width 1100px), scale+fade entrance. Header with search input and a close button that rotates on hover; a horizontal pill tab bar; body is a responsive 3-column card grid (icon chip, title, description, colored tag) that collapses to 2 then 1 column. Client-side substring search filters cards instantly, no debounce, no server round-trip. Five separate modules (workforce, fleet, equipment, clients/sites, rostering) each ship their own copy of this component, all sharing one CSS file's class names by bundle-concatenation luck rather than an explicit shared import — fragile, but proof the pattern was consciously repeated.

**Reuse for DeployFleet:** directly, as the **Domain Mega Menu** pattern — one per major operational domain (Fleet & Vehicles, Dispatch & Trips, Compliance, Billing & Finance, Driver & HR, AI & Intelligence), reachable from the global nav (§7.1) and from contextual "see everything in this domain" entry points. Fix the fragility DeployGuard shipped: one real shared OWL component (`MegaMenu`) parameterized by a domain's tile list, not five copy-pasted files.

### 3.2 Enterprise OS Launcher → the strongest single asset, adapt directly

**What it actually is:** genuinely replaces Odoo's native app grid, patching `web.NavBar`'s `AppsMenu` via OWL extension inheritance. The heaviest glassmorphism in the codebase: `backdrop-filter: blur(28px) saturate(135%)` over a near-black gradient card with a translucent hairline border and an inset top highlight — real glass, not a css-filter afterthought. Layout: search box, then a **"priority workspaces" strip** — six accent-colored pill shortcuts with `Alt+<letter>` keyboard badges jumping straight to the most-used command centers — above the full app grid, where every Odoo top-level menu renders as a gradient icon tile keyed by keyword-matched color family. Client-side search, escape-to-close, click-outside-to-close; no favorites/recents persistence, no drag-drop reordering.

**Reuse for DeployFleet:** directly, as the **DeployFleet Launcher**. Two specific ideas are worth preserving deliberately rather than being lost in a rebuild: the **priority-workspace strip with keyboard shortcuts** (translate to `Alt+D` Dispatch Board, `Alt+F` Fleet Command Center, `Alt+M` Maintenance Center, `Alt+B` Billing Workspace, `Alt+A` AI Workspace, `Alt+H` Home) and the **keyword-to-gradient color-family mapping** for auto-coloring app tiles, extended with the AI-content violet family from Principle 2 for anything AI-related in the grid. New for DeployFleet: **persist recents and pin favorites per user** — a genuine gap in the source component, and a real click-reduction win for a dispatcher who opens the same four screens every morning.

### 3.3 Command Centers → keep the attention-strip idea, resolve the visual-language split explicitly

**What exists:** at least five, in two incompatible visual languages (Principle 1). The Main OS Command Center and Workforce Command Center share the mega-menu's glass-modal shell, plus one genuinely distinct and excellent addition: a slim **attention strip** beneath the tab bar that renders *only when there's something to act on* (five parallel `search_count` calls — unfilled critical slots, no-shows, certs expiring in 7 days, pending leave, draft invoices), each count a clickable pill jumping straight to the underlying list. The Billing Command Center abandons the glass-modal shell entirely for a flat, desaturated, Stripe-style in-page workspace — a deliberate, apparently later, un-reconciled design pivot. The Executive/Analytics Dashboard defines yet a *third* independent token set and uses a persistent navy sidebar rather than either overlay pattern. No dedicated "Fleet Ops Command Center" client action exists — don't assume one when reading old references to "Fleet Widgets" (§3.7 is the real fleet pattern).

**Reuse for DeployFleet:** the **attention strip is the single most operationally valuable idea in this entire audit** and is adopted platform-wide, not just on the home screen — every command-center-class screen in §7 (Home, Fleet Command Center, Maintenance Center, Billing Workspace, AI Workspace) gets its own domain-scoped attention strip, computed the same way (parallel counts, silent when empty, click-through to the underlying record set). The visual-language split is *not* inherited — per Principle 1, Command Layer screens (home, launch, overview) get the glass treatment; Workspace Layer screens (billing, compliance registers) get the flat treatment, applied *consistently* rather than as an unexplained fork.

### 3.4 Dashboard Cards → componentize what DeployGuard only converged on by convention

**What exists:** the same DNA — label+icon header, one big bold number, a short colored caption, subtle hover lift, no chart, no library — repeated with variation across nearly every dashboard, sometimes as inline-styled Bootstrap grid markup (Workforce Dashboard), sometimes with a colored left-border stripe (Revenue Dashboard), sometimes a top-border stripe (Attendance History). No two dashboards use the exact same markup for what is conceptually the identical component.

**Reuse for DeployFleet:** the concept, standardized once as a real OWL component (`KpiCard`) rather than five hand-rolled variants. Recommend the **left-border-stripe variant** (cleaner at a glance, reads well in dense rows, and doubles naturally as a status-color carrier per Principle 4) as the one true form, retired everywhere else.

### 3.5 Quick Actions → reframe: a button stack and quick-create modals, not a floating-action tray

**What exists:** no FAB, no floating tray anywhere in the codebase (explicitly checked). "Quick Actions" is a **vertical stack of full-width, colored, icon-labeled buttons pinned in a dashboard sidebar** (e.g., "Auto-Fill Gaps" with an inline loading spinner and button-text swap while running) plus lightweight **quick-create modals** (3–5 fields, single submit, live-calculated totals as you type) launched from row-level buttons.

**Reuse for DeployFleet:** the sidebar action-stack and quick-create-modal pattern, honestly described as such. A genuinely new addition for DeployFleet worth layering on top (§6): a **contextual quick-action rail** that changes its button set based on what record is currently open — a floating, docked (not modal) panel is a legitimate upgrade over the source's static sidebar, since a dispatcher moving between shipment, trip, and driver records benefits from actions that follow the selection rather than living in one fixed sidebar.

### 3.6 Roster Board → the flagship reuse, adapted into the Dispatch Board

**What exists:** the richest, most sophisticated interaction pattern in the donor codebase, by a wide margin. A CSS-grid shell (fixed sidebar + timeline grid of site/post rows × date columns, cells = slot cards), with a right-hand guard-suggestion pool that appears only when a slot is selected. The mechanics, in order of value to DeployFleet:

- **Native HTML5 drag-and-drop** (no library) — draggable suggestion cards, drop-target cells, the same assignment call path whether triggered by drag or by click.
- **A three-way server response contract**: every assignment attempt returns `success`, `hard_block` (flatly refused, inline red error), or `override_required` — the last of which opens a **typed-reason override dialog** that becomes part of the audit trail. This is a genuinely excellent, directly portable compliance-UX pattern already conceptually present in `deployfleet_dispatch_compliance`'s backend (hard-disqualify vs. override-with-reason) — it currently has no matching frontend at all.
- **Scoring-engine suggestions surfaced inline**, not just computed server-side and buried in a form — ranked candidates with visible per-candidate score, both draggable and click-to-assign.
- **A pulsing critical-gap visual alarm** (`@keyframes` box-shadow pulse, stops on hover) on unfilled slots that matter — a deliberate, restrained urgency cue, not a blanket red wash.
- **Right-click context menu** on cards for secondary actions (suggest / unassign / view / swap).
- **Bulk auto-fill actions** with proper loading-state button feedback.
- **A real, considered mobile breakpoint**: below ~760px the side suggestion panel becomes a `position:fixed` bottom sheet with a drag handle and slide-up animation — not just column-stacking.

**Reuse for DeployFleet — this is §7.9's flagship, detailed there.** Every mechanic above maps almost one-to-one: guard→driver-or-vehicle, post/slot→trip/route leg, the hard-block/override-with-reason contract already exists in `deployfleet_dispatch_compliance`'s backend and just needs this exact frontend contract wired to it, and the scoring-suggestions panel maps directly onto `action_suggest_assignments()`'s existing output.

### 3.7 Fleet Widgets → the direct ancestor of the Fleet Command Center

**What exists:** the Fleet Dashboard — sidebar + tabbed table (Vehicles/Runs/Fuel) + a **row-click slide-in inspector panel** (the table area re-grids to make room rather than navigating away), one-click state-transition buttons, small quick-create modals with live-calculated totals, and a genuinely nice touch: a **client-side CSV export** that builds the file in-browser with no server round-trip. A cosmetic "LIVE" pill exists but the data is load-on-open, not pushed.

**Reuse for DeployFleet — detailed in §7.10 as the Fleet Command Center's direct pattern ancestor.** The sidebar/table/slide-in-inspector shell, one-click state transitions, and the in-browser CSV export are all worth carrying forward as-is. The cosmetic-only "LIVE" label is *not* — if DeployFleet claims live, it should be live (§7.10 recommends where actual polling is worth the cost and where it isn't).

### 3.8 Analytics Cards → keep the DIY approach, know its ceiling

**What exists:** beyond the KPI stat cards already covered in §3.4, one genuinely distinct visualization: a hand-rolled, div-based **paired bar chart** (invoiced vs. paid, per period) with CSS-transitioned heights — no charting library anywhere in the codebase.

**Reuse for DeployFleet:** keep the no-dependency philosophy where the visualization stays this simple (period-over-period paired or single-series bars, no zoom/tooltip/drill-down needed). §7's financial-forecast and dispatch-scoring areas (Phase 5 output) will need genuine drill-down and multi-series comparison the DIY approach can't cleanly express — that's the one place recommending a real lightweight charting library (evaluated, not chosen, in §7.16) is justified rather than DIY-for-its-own-sake.

### 3.9 Timeline Views → reframe honestly: a grouped, expandable history log

**What exists:** Attendance History is the closest match to "timeline" in the source and it is **not** a timeline visualization — no time-axis, no line-with-dots rendering. It's a date-grouped list (most recent date first), each date a card with a dark header bar and count, rows beneath colored by a left status-stripe, with a click-to-expand-in-place (not a modal) detail panel showing hour-bucket breakdowns. Well executed, genuinely useful — just not a timeline by any visual definition.

**Reuse for DeployFleet:** adopt the actual pattern under its actual name — a **grouped expandable history log** — for trip history, delivery history, driver-performance events, and compliance-document history (§7.10, §7.13). Where DeployFleet genuinely needs a time-axis visualization (a vehicle's day, a multi-stop route's schedule, a driver's hours-of-service across a week) that is new UX territory DeployGuard doesn't have an answer for — proposed fresh in §6 as the **Route Timeline**.

### 3.10 Visual KPIs → the circular gauge is directly portable; extend the trend-arrow convention

**What exists:** a genuinely well-built, dependency-free SVG circular progress-ring field widget (band-colored: green ≥80, amber 60–79, red <60, with matching text label), registered as a real Odoo field widget usable declaratively on any integer field — and a simple trend-arrow badge convention (colored by business meaning, not by literal direction — DeployGuard correctly renders a *rising* payroll cost in red because rising cost is bad, not because the arrow points up). No sparklines exist anywhere.

**Reuse for DeployFleet:** the gauge widget, directly, retargeted at driver safety score, on-time delivery percentage, vehicle utilization, and fuel efficiency (§7.13, §7.10). The trend-arrow convention, extended platform-wide with the same discipline: color follows business meaning per metric, decided explicitly per KPI, not defaulted to "up is green."

---

## 4. Design system foundation

This section specifies *what the design-system module should contain as decisions*, not code. Building it as an actual importable module (SCSS custom properties + a small OWL component library) is the first implementation step to fall out of this document, and every subsequent screen in §7 consumes it rather than reinventing tokens per dashboard — the discipline DeployGuard's own team visibly intended and didn't finish (§3.0).

**Brand palette — deliberately distinct from DeployGuard's navy, per [CLAUDE.md](../../CLAUDE.md)'s "not a re-skin" instruction.** DeployGuard converged on a Goldman-Sachs-adjacent deep navy (`#1B3A6B` family). DeployFleet's domain — trucks, roads, cargo, depots — has its own visual vocabulary available: deep teal-blue as the primary (professional, distinct from DeployGuard's navy, evokes horizon/movement rather than finance), paired with a **warm amber-orange accent** drawn deliberately from road-safety and high-visibility signage rather than from DeployGuard's palette at all — this becomes the one accent color that appears nowhere in the Workspace Layer except as the AI-adjacent or primary-CTA color, keeping it meaningful rather than decorative.

**Status color semantics — adopted platform-wide, not per-dashboard:**

| Meaning | Color family | Applies to |
|---|---|---|
| On-time / compliant / available / healthy | Green | Trip on schedule, document valid, vehicle available, driver compliant |
| Needs attention soon / approaching threshold | Amber | Document expiring within N days, maintenance due soon, invoice approaching due date |
| Critical / blocking / expired / broken | Red | Expired compliance document, vehicle breakdown, overdue invoice, hard-disqualified dispatch candidate |
| Informational / in progress / neutral state | Blue | In-transit, draft, awaiting confirmation |
| **AI-authored or AI-suggested content** | **Violet** — a new, deliberate fifth semantic, absent from DeployGuard entirely | Any AI-agent suggestion, prediction, or pre-filled field, anywhere in the product, before human approval |

The violet convention is the single most important net-new addition to the color system relative to DeployGuard, because DeployGuard's AI engine never had a real UI to need one (§3, cross-cutting note). Its job is to make Principle 2 — AI is a visible, distinct author — literally impossible to miss: a predicted-maintenance card, a suggested dispatch candidate, an AI-drafted customer message, all carry the same violet left-border/badge treatment, everywhere, so approving or rejecting AI output never requires the user to first figure out that it *is* AI output.

**Elevation & glass recipe — codified once, applied per-layer (Principle 1):**

- **Command Layer surfaces** (launcher, mega menus, command-center overlays): dark scrim (`rgba(2,6,23,.6–.76)`) + heavy blur (24–28px) + saturate boost behind translucent gradient cards with a hairline border and inset top highlight — the Enterprise OS Launcher's actual recipe (§3.2), inherited directly because it is genuinely well executed.
- **Workspace Layer surfaces** (lists, forms, billing tables, compliance registers): flat white/near-white cards, no blur, shadow reserved for true elevation changes (a hovering card, an open modal) rather than applied decoratively to every panel. This is the Billing Command Center's flat instinct (§3.3), generalized as the rule for anything data-dense rather than treated as an unexplained one-off.

**Typography, spacing, iconography, motion** — specified as principles, not pixel values, since the actual token file is an implementation artifact: a single type scale shared by both layers (Command Layer permits slightly larger display numbers for KPI moments); an 8px base spacing unit; one icon set used consistently (no mixing Font Awesome with a second icon library, a small inconsistency visible across DeployGuard's own modules); and motion reserved for *state change communication* (a card entering, a status flipping, a value updating) rather than ambient decoration — durations in the 150–300ms range matching DeployGuard's own better-executed transitions (the mega-menu entrance, the gauge's stroke-dashoffset animation), never longer, since a working dispatcher should never wait on an animation to finish before acting.

---

## 5. Global navigation & the home experience

**Global Navigation** becomes three coordinated surfaces, replacing today's single flat app menu:

1. **The DeployFleet Launcher** (§3.2) — the entry point from anywhere, `Alt+Space` or a persistent corner control. Priority-workspace strip with keyboard shortcuts, full app grid below, user-pinned favorites and recents (the one deliberate improvement over DeployGuard's source).
2. **Domain Mega Menus** (§3.1) — one per operational domain, reachable both from the launcher and as a persistent top-bar entry per domain, so a dispatcher living inside Dispatch all day never has to leave that context to jump between Fleet, Compliance, and Billing sub-areas.
3. **A Command Palette** (`Cmd/Ctrl+K`) — genuinely new, absent from DeployGuard entirely (§6). Type a shipment number, a driver name, a vehicle plate, or an action verb ("assign driver," "log fuel," "approve invoice") and jump directly there or execute it inline. This is the single highest-leverage click-reduction opportunity in the whole document: today, reaching any specific record requires navigating the app menu → sub-menu → list → filter → row, every time.

**The Home Dashboard** is role-scoped, not one screen:

- **Owner/Manager**: a Command-Layer "Mission Control" home (§6) — the Main Command Center's attention-strip-plus-launchpad pattern (§3.3), scoped platform-wide: unassigned shipments, expiring compliance documents across the whole fleet, overdue invoices, vehicles in breakdown, pending AI approvals — five or six silent-unless-nonzero counters, each a direct jump.
- **Dispatcher**: opens directly to the Dispatch Board (§7.9), not a generic home screen — a dispatcher's day starts with today's board, not a launcher.
- **Driver (mobile)**: today's assigned trip, one tap to navigation/inspection/POD — detailed in §7.17.
- **Customer (portal)**: shipment status and documents — detailed in §7.19.

---

## 6. New DeployFleet-native UX concepts

Ideas with no DeployGuard ancestor at all — proposed because transportation/logistics has needs a workforce-scheduling platform simply never had.

- **Command Palette** (`Cmd/Ctrl+K`, described above) — universal search + action execution, the single largest click-reduction lever available.
- **Live Trip Map** — a real map view (genuinely absent from DeployGuard and from DeployFleet today alike) showing active vehicles as pins with breadcrumb trails, route lines, and depot markers; clicking a pin opens that vehicle's Fleet Command Center inspector inline rather than navigating away. This is the single most-requested-feeling screen a trucking company will expect on first demo and the platform currently has no answer for at all.
- **Compliance Traffic-Light Wall** — every vehicle and driver as a single-row-per-entity grid of red/amber/green status chips (insurance, roadworthiness, permit, license, medical) — one screen answering "who can't legally run today" without opening a single record. Directly closes the gap between `deployfleet_vehicle_compliance`/`deployfleet_dispatch_compliance`'s rich backend logic and the fact that today nothing surfaces it at a glance.
- **Route Timeline** — a genuine time-axis view (not the "grouped log" DeployGuard mislabels as a timeline, §3.9) for a vehicle's day or a multi-stop route's schedule — the concrete answer to the gap flagged in §3.9 and directly relevant to the LTL/multi-stop work scoped in [12-ltl-freight-management-architecture.md](12-ltl-freight-management-architecture.md).
- **Load Visual Builder** — for multi-drop/consolidated shipments (again tying to doc 12), a truck-silhouette capacity-fill visualization as cargo is assigned to a trip, so a dispatcher sees remaining weight/volume capacity at a glance instead of doing the arithmetic mentally.
- **Driver Scorecard** — the Visual-KPI gauge (§3.10) retargeted at a driver: safety score, on-time percentage, fuel efficiency, paired with the driver-performance module's existing events, framed as a constructive scorecard a driver can check themselves (mobile), not a surveillance tool — this distinction matters for adoption and should be an explicit product-tone decision, not an afterthought.
- **AI Co-Pilot Rail** — a persistent, collapsed-by-default docked panel (Command Layer treatment, violet-accented per §4) present across every workspace, expanding on demand to show contextually relevant agent output for whatever record is open (a predicted maintenance date on a vehicle record, a suggested dispatch candidate on a shipment, a drafted customer status update) — never a separate chatbot window disconnected from context, and never auto-executing anything per the mandatory approval pipeline.
- **Proof-of-Delivery Gallery** — POD photos/signatures already captured by the driver mobile app surfaced as a visual gallery inside the Billing Workspace and Customer Portal, not buried as form-view attachments.

---

## 7. Systematic area-by-area analysis

Each area: **current state**, **problems** (evaluated against first impression, discoverability, ease of use, visual hierarchy, mobile usability, AI workflows, dashboard design, navigation, task speed, click count, cognitive load, as relevant to that area), **missing cues/dashboards**, and **redesign direction** (OWL/glass/animation/AI/contextual-action opportunities, plus which DeployGuard pattern from §3 it draws on, if any).

### 7.1 Global Navigation
**Current state:** a single flat Odoo app menu, every module nested underneath as children — no mega menu, no launcher, no command palette, no search-to-navigate. **Problems:** discoverability is entirely dependent on knowing the menu hierarchy by heart; there is no way to jump to a specific record without navigating through a list first; first impression on demo is "generic Odoo," immediately, before any data is even seen. **Missing cues:** no visual distinction between domains, no indication of what needs attention anywhere in the nav chrome itself. **Redesign direction:** DeployFleet Launcher + Domain Mega Menus + Command Palette, per §5, drawing directly on §3.1/§3.2.

### 7.2 Home Dashboard
**Current state:** does not exist — opening the app lands on whatever the last-used menu was, or Odoo's default. **Problems:** no orientation moment at all; a manager has no single place to ask "is anything wrong today." **Missing dashboards:** entirely missing. **Redesign direction:** role-scoped Mission Control home, per §5/§3.3's attention-strip pattern.

### 7.3 Module Dashboards
**Current state:** none of Phase 1–5's modules have a dashboard screen — each is a list view with filters. **Problems:** a fleet manager wanting "how many vehicles need maintenance this week" must build a filtered list manually every time; no persistent view of module health. **Redesign direction:** every phase-group (Operations, Cost Control, Compliance, Customer, Intelligence) gets a Command-Layer summary screen using the standardized `KpiCard` (§3.4/§4) plus its own attention strip, consuming the shared design-system tokens rather than bespoke CSS per dashboard (§3.0's lesson, applied).

### 7.4 List Views
**Current state:** stock Odoo lists throughout, functional but visually undifferentiated from any other Odoo install. **Problems:** no status-color coding beyond default badges in most lists; no inline quick actions beyond the two dispatch-list buttons found; dense financial/compliance lists have no visual hierarchy beyond column order. **Redesign direction:** apply the platform-wide status-color semantics (§4) as row-left-border stripes consistently (the Revenue Dashboard/Attendance History convention, §3.4/§3.9, generalized to every list, not just dashboards); add row-level contextual quick actions matching the record's available state transitions, styled consistently with the Fleet Dashboard's one-click transition buttons (§3.7).

### 7.5 Form Views
**Current state:** stock Odoo forms, every field visible at once regardless of relevance to current state. **Problems:** cognitive load — a shipment or vehicle form shows compliance, billing, and operational fields simultaneously regardless of what the current viewer actually needs; [15-load-sheet-architecture.md](15-load-sheet-architecture.md) already flagged this exact problem for the load sheet specifically. **Redesign direction:** the collapsed-summary-card-plus-expandable-sections treatment doc 15 already recommended for shipments extends platform-wide to vehicle, driver, and trip records — a compact identity header (plate/name/status) always visible, with maintenance/compliance/financial/history sections collapsed by default and expandable on demand, rather than one long scroll.

### 7.6 Kanban Views
**Current state:** three bare kanban boards (dispatch assignment, shipment, vehicle), 3–4 fields per card, no avatars, no color logic beyond default grouping. **Problems:** a kanban card today conveys almost no information at a glance — exactly the gap the Dispatch Board section addresses in depth. **Redesign direction:** richer card templates (status-color left border, avatar/icon, key metric, AI-suggestion badge where relevant) as the default `KpiCard`-adjacent card component, applied to all three existing boards even before the full custom Dispatch Board (§7.9) ships, as a faster, smaller first win.

### 7.7 Map Views
**Current state:** does not exist anywhere in the product. **Problems:** for a logistics platform this is the single largest visible gap on first demo — a prospective customer will expect to see trucks on a map within the first five minutes. **Redesign direction:** the Live Trip Map (§6) — vehicle pins with breadcrumb trails, route lines, depot markers, click-through to the Fleet Command Center inspector; also a static depot/route network map as a lighter-weight first version if live GPS feed integration isn't ready.

### 7.8 Calendar Views
**Current state:** does not exist anywhere — no calendar for trips, maintenance schedules, leave, or compliance-document expiry. **Problems:** a fleet manager currently has no way to see "what expires this month" or "what's scheduled this week" without building a filtered list and reading dates manually. **Redesign direction:** a shared calendar surface (standard Odoo calendar view is an acceptable, fast first step here, upgraded later with color-coded event types matching §4's status semantics) across maintenance schedules, leave requests, and compliance-document expiry — genuinely low-effort, high-value, and currently 100% missing.

### 7.9 Dispatch Board — flagship reuse
**Current state:** a bare kanban card grouped by state; the underlying scoring, hard-disqualify, and override-with-reason logic in `deployfleet_dispatch`/`deployfleet_dispatch_compliance` is fully built and has no matching frontend richness at all. **Problems:** a dispatcher today clicks into each proposed assignment individually to see the score and confirm — there is no board-level view of the day, no visual urgency signal for unassigned shipments, no drag-drop. **Missing cues:** nothing distinguishes an urgent unassigned shipment from a routine one; the override-reason requirement exists in the backend with only a plain form field to satisfy it. **Redesign direction — directly adapting the Roster Board (§3.6), domain-remapped:** a timeline/board hybrid (shipments as rows or cards, driver/vehicle assignment as the interaction), native drag-drop assignment, a right-hand ranked-candidate suggestion panel sourced from `action_suggest_assignments()`, the exact three-way hard-block/override-required/success contract wired to a proper override dialog demanding a typed reason, a pulsing urgency indicator on unassigned shipments approaching their pickup window, right-click context actions, bulk "auto-assign remaining," and the same considered mobile-bottom-sheet breakpoint DeployGuard shipped for its suggestion panel. This is the single highest-priority build to come out of this document.

### 7.10 Fleet Command Center
**Current state:** a stock vehicle list/form/kanban; no dashboard, no inspector, no consolidated fleet view. **Problems:** seeing a vehicle's compliance, maintenance, fuel, and current assignment together requires navigating four separate modules' list views. **Redesign direction — adapting the Fleet Dashboard (§3.7) directly:** sidebar + tabbed table (Vehicles/Trips/Fuel/Maintenance) + row-click slide-in inspector consolidating compliance status, current assignment, recent fuel logs, and maintenance schedule for that one vehicle; one-click state transitions (available/in-transit/maintenance/breakdown); genuine live status (§3.0's caveat about DeployGuard's cosmetic-only "LIVE" label — here it should be real, since vehicle state changes are exactly the kind of event `deployfleet_event_bus` already fires and a dashboard can genuinely subscribe to); the Driver Scorecard gauge (§6) surfaced per-vehicle utilization; in-browser CSV export retained from the source pattern.

### 7.11 Maintenance Center
**Current state:** stock list/form for maintenance schedules; predictive-maintenance output from Phase 5 (`deployfleet.maintenance.prediction`) has only a standard Odoo view, disconnected visually from the schedules it's meant to inform. **Problems:** a maintenance manager cannot currently see "what's due soon, what's predicted, what's overdue" in one place — has to cross-reference two modules manually. **Missing dashboards:** entirely missing. **Redesign direction:** a Command-Layer summary (attention strip: overdue, due this week, AI-predicted-at-risk) with predictions visually distinguished via the violet AI-content convention (§4) so a manager can tell at a glance which entries are scheduled fact versus model prediction, and act on the prediction as a suggestion, not a scheduled event, until acted upon.

### 7.12 Workshop UI
**Current state:** stock list/form for job cards and job lines; no kanban-by-status, no visual job-card board. **Problems:** a workshop supervisor tracking multiple open jobs has no at-a-glance board of what's in diagnosis vs. repair vs. awaiting parts. **Redesign direction:** a job-card kanban board (diagnosis → repair → parts-wait → complete), each card showing vehicle, technician, elapsed time, and parts-line cost running total; no direct DeployGuard ancestor exists for this specific workflow, so this is new design, though it borrows the Fleet Dashboard's inspector-panel mechanic for a card's full detail.

### 7.13 Billing Workspace
**Current state:** stock list/form for invoices; the accounting-integration work (this session's chart-of-accounts fix, ZRA submission) is entirely invisible in the UI beyond a status field. **Problems:** an AR-aging view, a "what's overdue" glance, and ZRA-submission status visibility are all currently absent. **Redesign direction — adapting the Billing Command Center + Revenue Dashboard (§3.3/§3.8) directly, including their flat Workspace-Layer treatment since this is precisely the dense-data context that visual language suits:** AR-aging KPI row, the paired-bar invoiced-vs-paid chart pattern retained as-is (no library needed at this data complexity), a clear ZRA-submission-status color chip per invoice, and the Proof-of-Delivery Gallery (§6) surfaced per-invoice so a billing clerk can visually confirm delivery before chasing payment.

### 7.14 Driver Workspace
**Current state:** driver records live inside `hr.employee` extensions with stock form views; no consolidated driver 360 exists in the backend UI (distinct from the mobile app). **Problems:** a dispatcher wanting a driver's compliance status, recent performance events, and current assignment together must open three modules. **Redesign direction:** a driver 360 card adapting the Attendance-History grouped-expandable-log pattern (§3.9) for trip/performance history, the circular gauge (§3.10) for the Driver Scorecard (§6), and compliance status as traffic-light chips (§6) inline.

### 7.15 Customer Workspace
**Current state:** stock `res.partner`/`deployfleet.customer` form and list views; no consolidated view of a customer's contracts, active shipments, and billing status together. **Problems:** account management currently requires cross-referencing customer, shipment, and invoice modules separately. **Redesign direction:** adapting the Clients/Sites Mega Menu's tile-navigation concept (§3.1) into a customer 360 workspace — contract terms, active/recent shipments as a mini-board, outstanding balance, all one screen.

### 7.16 AI Workspace
**Current state:** does not exist as a distinct surface at all — `deployfleet.ai.action.request` has only a standard list/form view; there is no agent catalog view, no usage/cost dashboard exposed to an operator, no natural-language query surface. **Problems:** this is the largest gap between backend sophistication (a full six-agent catalog, permission layer, and mandatory approval pipeline, per [08-ai-architecture.md](08-ai-architecture.md)) and frontend reality (nothing) anywhere in the product. **Redesign direction:** the AI Co-Pilot Rail (§6) as the ambient, cross-app surface, plus a dedicated **AI Workspace** as its own command-center-class screen: an approval queue (pending action requests, ranked, one-click approve/reject with the reason field the backend already requires), an agent catalog view (six agents, each showing recent output, confidence, and its on/off toggle per [CLAUDE.md](../../CLAUDE.md) §4's non-negotiable per-feature switch), and a usage/cost dashboard over `deployfleet.ai.usage` (tokens, cost, cache-hit rate, per company) that currently has no visual home despite being fully logged in the backend. This is the one area of §7 with no DeployGuard ancestor to adapt at all — genuinely new design, and arguably the second-highest-priority build after the Dispatch Board, since it's the only way the AI investment already made becomes visible and usable rather than backend-only.

### 7.17 Mobile Experience
**Current state:** three React Native app scaffolds (driver/dispatcher/customer) per [MOBILE_ARCHITECTURE.md](../../MOBILE_ARCHITECTURE.md), with the glassmorphic-not-native-default intent stated but few real screens built against it yet. **Problems:** none of the desktop redesign work above automatically transfers to mobile — a driver's actual moment-to-moment need (today's trip, one-tap navigation handoff, POD capture, breakdown reporting) is a different information architecture from a shrunk desktop screen. **Redesign direction:** driver home = today's assigned trip as a single card, one-tap actions (navigate/inspect/report issue/capture POD), Driver Scorecard (§6) as a secondary, opt-in tab rather than the landing screen; the Roster Board's considered bottom-sheet breakpoint (§3.6) is the concrete pattern precedent for how DeployFleet's own mobile-web-adjacent surfaces (not the native app itself, but any web view surfaced on a phone) should collapse.

### 7.18 Customer Portal
**Current state:** `deployfleet_customer_portal` exists with basic shipment-status visibility; per Phase 4 build notes, functional but minimal. **Problems:** a customer currently sees status text, not the Proof-of-Delivery gallery, not a visual shipment timeline, not documents in one place. **Redesign direction:** shipment status as the Route Timeline concept (§6) simplified for an external audience, POD Gallery (§6) attached per shipment, documents (invoices, PODs, compliance certificates where relevant) consolidated in one tab rather than scattered.

### 7.19 Driver Portal
**Current state:** no distinct web portal for drivers exists separate from the mobile app and the internal `hr.employee` form — this is currently a gap between "internal record" and "mobile app," with no web-accessible self-service surface. **Problems:** a driver without the mobile app installed (a real onboarding-day scenario) has no way to see their own schedule, documents, or payslips. **Redesign direction:** a lightweight self-service web portal (schedule, documents, payslips, leave requests) mirroring the Customer Portal's shape but scoped to a driver's own data — new territory, low DeployGuard precedent beyond the general portal-module pattern.

### 7.20 Tablet Experience
**Current state:** unaddressed as a distinct form factor anywhere in current design intent. **Problems:** a dispatcher's desk tablet and a warehouse check-in tablet are real, common hardware in trucking operations and neither phone-sized nor desktop-sized layouts serve them well by default. **Redesign direction:** the Dispatch Board and Fleet Command Center (§7.9/§7.10) should both be explicitly designed against a tablet breakpoint, not just "responsive desktop" — larger touch targets on drag-drop targets specifically, since a tablet's touch-drag precision is worse than a mouse's, directly affecting the Roster-Board-derived interaction model's usability.

---

## 8. Cross-cutting AI-assisted workflow strategy

Consolidating the AI-related opportunities scattered through §7 into one coherent shape, since AI assistance is a platform-wide capability, not a per-screen feature:

- **The violet-content convention (§4)** is the visual backbone — every AI touchpoint, everywhere, is visually identifiable as AI before a user reads a word.
- **The AI Co-Pilot Rail (§6)** is the ambient, always-available surface; the **AI Workspace (§7.16)** is the destination for actually working the approval queue and understanding cost/usage.
- **Every AI suggestion surfaced inline** (predicted maintenance on a vehicle record, a suggested dispatch candidate, a drafted customer message) follows the identical suggestion→approve/reject→audit interaction, never a bespoke one-off per module — consistency here is what makes the mandatory approval pipeline feel like a feature (trustworthy, fast to work through) rather than friction.
- **Cost and permission visibility is a first-class screen, not an admin afterthought** — per [CLAUDE.md](../../CLAUDE.md) §4's non-negotiable per-feature toggles and cost tracking, the AI Workspace's usage dashboard is where a fleet owner actually sees what AI is costing them and switches off what they don't want, in one place.

---

## 9. Accessibility, performance & motion discipline

Glassmorphism and heavy blur are real costs, not free polish, and this document does not treat them as such:

- **Contrast first.** Every Command-Layer glass surface must be checked against WCAG AA contrast for its text against the blurred background in both light and dark ambient conditions — a translucent card that reads beautifully in a design tool and poorly in truck-stop sunlight has failed its actual user.
- **`backdrop-filter` is expensive on low-end Android devices** common among driver-facing hardware in the target market — Command-Layer blur is acceptable on desktop/tablet dispatcher and manager surfaces; driver-facing mobile screens should default to a solid, high-contrast Workspace-Layer treatment even where the rest of the platform uses glass, per Principle 6.
- **Respect reduced-motion preferences** platform-wide; every animation named in this document (mega-menu entrance, gauge fill, pulsing urgency indicator) needs a static equivalent.
- **Offline tolerance is a UX requirement, not just a backend one** for driver-facing mobile screens — trip data, POD capture, and inspection forms need to work and queue on poor connectivity, a real condition for the target market, not an edge case.

---

## 10. Success metrics & validation method

This document's claims are falsifiable; they should be checked, not assumed correct on aesthetic grounds alone:

- **Clicks-to-complete, per key workflow**, measured before/after: confirm a dispatch assignment (today: open kanban card → open form → read score → click confirm, ~4 steps); log a fuel entry; approve an AI action; find a specific shipment by number. The Command Palette (§6) and Dispatch Board (§7.9) redesigns should each show a measurable drop here.
- **Time-on-task** for the same workflows, not just click count — a design can reduce clicks while increasing time if each step is heavier.
- **Mobile task-completion rate** for the driver app's core loop (accept trip → navigate → POD capture) under realistic connectivity, not just simulator conditions.
- **A qualitative "does this feel premium" check** — literally showing the redesigned Dispatch Board and Fleet Command Center to someone outside the project (ideally a real trucking-company stakeholder, tying back to [CLAUDE.md](../../CLAUDE.md) §10's still-open domain-validation item) before broad rollout, since "premium" is this document's stated goal and it is a subjective judgment that deserves a real outside check, not just internal confidence.

---

## 11. Phased rollout recommendation

Sequenced for impact-per-effort, not enforced as a rigid schedule — a design/frontend planning aid, not a replacement for [05-implementation-roadmap.md](05-implementation-roadmap.md)'s phase gates:

1. **Foundation** — the design-system module (§4: tokens, `KpiCard`, status-color rules, the violet AI convention) and the Command Palette (§6, disproportionately high value for near-zero design risk).
2. **Flagship workspaces** — Dispatch Board (§7.9) and Fleet Command Center (§7.10), the two screens a demo lives or dies by.
3. **Global navigation** — Launcher + Domain Mega Menus (§5), once there are enough redesigned destination screens to make the launcher worth opening.
4. **The AI Workspace** (§7.16) — closing the single largest backend-to-frontend gap in the product.
5. **Remaining module dashboards and Map/Calendar views** (§7.3, §7.7, §7.8) — genuinely missing infrastructure, high value, lower design risk than the flagship boards.
6. **Mobile, Customer Portal, Driver Portal, Tablet** (§7.17–§7.20) — once the desktop/tablet design language is proven out, so mobile isn't reinventing patterns the flagship work hasn't validated yet.
7. **New concepts** (§6: Live Trip Map, Route Timeline, Load Visual Builder, Driver Scorecard, POD Gallery) — layered in opportunistically as their underlying data (GPS feed, multi-stop model) matures, per the gating already noted in docs 11–13.

---

## 12. Governance

This document is now the authoritative elaboration of [CLAUDE.md](../../CLAUDE.md) §5's UI/UX standards, the same relationship [08-ai-architecture.md](08-ai-architecture.md) has to §4. Before building any dashboard, board, or workspace named in §7, check it against this document the same way AI work is checked against doc 08 — and if a real implementation constraint contradicts a recommendation here (a performance ceiling, an Odoo Community-edition limitation per the still-open edition question in [06-risks-and-recommendations.md](06-risks-and-recommendations.md)), update this document in the same session, per [CLAUDE.md](../../CLAUDE.md) §8's own rule that architecture docs are living records, not write-once artifacts.
