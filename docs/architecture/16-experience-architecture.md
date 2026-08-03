# 16 — Experience Architecture

**Status:** Strategy document, not an implementation plan. No code, no OWL components, no CSS tokens as files exist yet as a result of this document — it defines *what to build and why*, the same way [08-ai-architecture.md](08-ai-architecture.md) defined the AI architecture before `deployfleet_ai_core` was written. Frontend work on any dashboard, board, or workspace named below should be checked against this document first, the same discipline [CLAUDE.md](../../CLAUDE.md) §2 already asks for against the domain-model and module-structure docs.

This document now anchors a four-document set, split the same way [08-ai-architecture.md](08-ai-architecture.md) stayed the AI *strategy* doc while implementation detail lives in the modules it specifies:

| Doc | Answers |
|---|---|
| **16 (this doc)** | Why, what, and in what order — diagnosis, philosophy, brand personality, DeployGuard pattern reuse, area-by-area redesign direction, rollout sequencing |
| [17-design-system.md](17-design-system.md) | The actual token system — color, type, spacing, elevation, glass, iconography, motion, AI styling, dark mode, accessibility rules. DeployFleet's equivalent of a Material Design spec: no developer should ever need to invent a shadow value or a button color again |
| [18-component-library.md](18-component-library.md) | The `deployfleet_ui` OWL component catalog — every reusable component a module should import rather than hand-roll, from basic atoms through the signature "wow" widgets |
| [19-animation-guidelines.md](19-animation-guidelines.md) | The motion system — exact timing/easing per interaction class, so animation reads as one consistent language rather than five developers' five guesses |

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
- **The product currently looks and reads like an ERP module list, not a fleet intelligence platform** — menu labels are literally the model names (Customers, Drivers, Trips, Vehicles), which is the correct information architecture for a database administrator and the wrong first impression for a fleet owner deciding whether this looks like software worth paying for. §2 treats this as a real, fixable finding, not a cosmetic complaint.

This is the honest starting line. It's also, properly read, good news: there is no legacy custom UI to migrate or unwind — every recommendation below is additive against a clean slate, not a renovation fighting existing investment.

---

## 2. Design philosophy, personality, and identity

### 2.1 Visual personality — a deliberate break from DeployGuard's register

DeployGuard's strongest Command Layer surfaces (§3.2's Enterprise OS Launcher especially) are genuinely well built, but their register is **military operations center** — dark, dense, alarm-strip, "command and control." That register made sense for a private-security-guard workforce platform. It is the wrong register for DeployFleet, and copying it verbatim would be exactly the "re-skin" [CLAUDE.md](../../CLAUDE.md) already rules out.

DeployFleet's target register instead: **Tesla Fleet, Stripe, Linear, Notion, Uber Freight, Motive, Samsara** — modern, fast, minimal, confident. Concretely, that means:

- Confidence expressed through **restraint and whitespace**, not density and alarm color. A screen that looks calm because everything is actually fine reads as more premium than a screen that looks busy because it's trying to look important.
- **One accent color earns attention**, used sparingly (§4/doc 17's amber), rather than DeployGuard's gradient-per-domain color-coding applied everywhere.
- Motion communicates *state change*, per Principle 3 below, never *atmosphere* — no ambient pulsing chrome, no decorative particle effects, nothing that reads as "trying to look futuristic."
- Where DeployGuard's Command Layer names lean militaristic ("Command Center," "OS Launcher"), DeployFleet keeps the operationally honest ones (Fleet Command Center is a genuinely accurate name for a screen you command fleet actions from) and deliberately avoids adding more of that register than already exists — see the naming table in §2.3.

### 2.2 The DeployFleet DNA

A short, memorizable identity statement — the thing that should be true of every screen this document and its siblings (17–19) produce, and the test any new screen should be checked against before it ships:

> **Fleet intelligence first.** Maps everywhere they add value. AI is always visible but never intrusive. Operational status is instantly understandable through consistent colors and badges. Every screen leads naturally to the next action. Beautiful command centers for orientation, clean workspaces for execution. Enterprise power without enterprise complexity.

Six sentences, each one a load-bearing rule the rest of this document (and 17–19) exists to operationalize: fleet intelligence first → §2.4/§7 "every screen answers a question"; maps everywhere → §6/§7.7; AI visible-not-intrusive → §2.1/§8/doc 17's violet convention; consistent color/badge language → doc 17 §status-semantics; every screen leads to an action → §2.5; command centers vs. workspaces → the Command Layer/Workspace Layer split (Principle 1 below); enterprise power without enterprise complexity → the whole document's reason for existing.

### 2.3 Naming — language changes perception

DeployGuard's own naming is functional but generic-enterprise ("Dashboard," "Reports"). DeployFleet adopts sharper, more specific language platform-wide, decided once here rather than improvised per screen:

| Generic/ERP-flavored term | DeployFleet term | Where it applies |
|---|---|---|
| Dashboard (analytics/summary screens) | **Intelligence** | Fleet Intelligence, Maintenance Intelligence, Compliance Intelligence, Financial Intelligence — the per-domain "Module Dashboards" of §7.3 |
| Reports | **Insights** | `deployfleet_client_reports`' customer-facing output, and any analytics export surface |
| AI Workspace / AI settings | **Copilot Console** (destination screen) / **Copilot Rail** (ambient, docked panel) | §7.16, §8, §6 |
| (n/a — new) | **Mission Control** | The owner/manager Home Dashboard (§2.5/§5) — deliberately NASA/SpaceX-coded modern-ops language, not the military-command register §2.1 rejects |

Two names are deliberately *kept* rather than replaced, because they are already accurate and specific rather than generic: **Fleet Command Center** (§7.10) is a genuinely operational, action-oriented screen — "command center" earns its name there — and **Dispatch Board** (§7.9) is plain, correct, and doesn't need reinventing. The distinction that resolves which naming convention applies where: **"Intelligence" names an analytics/insight screen; "Command Center"/"Board" names an operational, action-taking screen.** Don't blend the two — a screen that only shows numbers is Intelligence; a screen you act from is a Command Center or a Board.

### 2.4 Every screen answers a question

A dashboard that is merely pretty has failed. Every command-center-class or intelligence-class screen in §7 is designed backward from **one plain-English question it answers on load, with no further clicking**:

| Screen | Question it answers |
|---|---|
| Mission Control (Home) | *Is anything wrong today?* |
| Fleet Command Center | *Which trucks are making money?* |
| Dispatch Board | *Which load should go next?* |
| Maintenance Intelligence | *What is about to fail?* |
| Financial Intelligence / Billing Workspace | *Where are we losing money?* |
| Driver Workspace | *Which drivers need attention?* |
| Copilot Console | *What should I do today?* |

Any new screen proposed against this document should be able to fill in that same one-line blank before a single component is designed. If it can't, it's a list view with extra styling, not an Intelligence or Command Center screen, and should be named and scoped honestly as such.

### 2.5 First five minutes, storytelling, and always-a-next-action

Three tightly related principles about what a user experiences in the first moments and on every subsequent screen:

- **The first five minutes are designed, not defaulted.** A user's first login should show moving trucks (§6 Live Fleet Map), the day's dispatches, revenue, active loads, AI suggestions, driver statuses, and alerts — a working fleet, not a settings-app-shaped list of "Customers / Drivers / Trips / Vehicles" menu items. That menu list is correct as an information architecture and wrong as a first impression; Mission Control (§2.3/§5) exists specifically to be what a user sees before they ever need the menu.
- **Every screen tells a story, not a field dump.** A vehicle record isn't "Vehicle → Trips → Maintenance → Fuel" as four separate tabs to click through — it's *"Truck 504. Currently in transit to Copperbelt, ETA 4:20 PM, 72% fuel, K18,400 revenue this month, next service in 6 days, driver score 91, last inspection Tuesday, AI predicts a brake-pad replacement within 3 weeks."* One narrative, told through the collapsed-summary-card-plus-expandable-sections pattern §7.5 already specifies for form views — this principle is *why* that pattern matters, not a separate idea.
- **No screen is a dead end.** DeployGuard shipped genuine look-only screens. DeployFleet's rule: every record view asks "what can I do next" and answers it with visible, contextual actions (assign a load, schedule maintenance, contact the driver, view the route, view expenses, ask the Copilot, generate a report) — never a form with nothing to press but the browser back button. §3.5's contextual quick-action rail is the mechanical answer to this principle; this is the principle itself.

### 2.6 The resolving principles

Six mechanical principles that resolve implementation-level decisions throughout §3–§11:

**1. Two visual layers, not one, and not two competing ones by accident.** DeployGuard's own codebase (§3.0) drifted into two incompatible visual languages — a dark, saturated, gradient-heavy "OS" aesthetic (launcher, mega menus, home command center) and a flat, desaturated, Stripe-style finance aesthetic (Billing Command Center) — apparently through an undocumented later pivot that was never back-ported. DeployFleet inherits the *idea* that navigation/launch moments and data-entry/review moments want different visual treatments, but resolves it deliberately instead of by accident:

- **Command Layer** — full-screen or overlay surfaces whose job is *orientation and launch*: the app launcher, mega menus, command-center home screens, the Copilot Rail when expanded. These earn the glassmorphism, the gradient accent chips, the blur, the motion. A user is here for seconds, not hours — visual richness doesn't fight task completion. **Revised mid-Phase-D: the glass panel itself is light, not dark.** Every Command Layer screen originally shipped with a dark translucent gradient panel (light text on near-black glass), matching DeployGuard's own Enterprise OS Launcher recipe. An explicit product decision after Phase C's flagship screens landed — "only light backgrounds, as much as possible" — retrofitted the Launcher, Mega Menus, Mission Control, and the Copilot Rail (plus the shared `Card` atom's `command` variant) to a light, near-white translucent panel with dark text instead, while keeping every other part of the recipe (scrim, blur, saturation boost, hairline border, motion) unchanged. See doc 17 §6's changelog note for the token-level detail — this is a genuine revision to the design system, not a one-off screen tweak, so any future Command Layer surface should use the light recipe by default.
- **Workspace Layer** — surfaces whose job is *sustained work*: list views, form views, the Dispatch Board's cell-level detail, billing tables, compliance registers. These are flat, high-contrast, desaturated except for semantic status color, dense where density serves scanning, generous where a single number needs to be read from across a cab. A dispatcher doing this for eight hours must not be fighting a translucent card for contrast.

Every area analyzed in §7 states explicitly which layer it belongs to. Getting this assignment wrong — e.g., glassmorphic blur behind a 40-row compliance table — is the single most common way "premium" tips into "annoying."

**2. AI is a visible, distinct author — never an invisible hand, and never confined to one module.** [CLAUDE.md](../../CLAUDE.md) §4 and [08-ai-architecture.md](08-ai-architecture.md) already make the mandatory suggestion→approval→execute→audit pipeline non-negotiable at the data layer. The visual language must carry that same guarantee, platform-wide: **anything AI-suggested or AI-generated gets a distinct, consistent visual treatment (a color, a badge, an icon) everywhere in the product**, so a user never has to wonder whether a number, a suggestion, or a pre-filled field came from a human, a rule, or a model — detailed fully in §8's ambient-AI strategy and doc 17's violet convention.

**3. Reduce clicks by collapsing navigation, not by cramming forms.** Every "reduce clicks" opportunity in §7 is a navigation or workflow-collapse opportunity (fewer screens between intent and action), never information-density-at-the-cost-of-legibility. A driver on a moving vehicle's dashboard tablet and a dispatcher scanning fifty rows have different tolerances for density; neither is served by cramming.

**4. Status is a color language, applied identically everywhere.** DeployGuard converged, largely by convention, on green/amber/red/blue-purple as compliant-or-on-time / needs-attention-soon / critical / informational. DeployFleet adopts this explicitly as a platform-wide rule (full table in [17-design-system.md](17-design-system.md)) rather than a per-dashboard convention re-invented each time, extended with the one deliberate inversion DeployGuard itself modeled well: color follows *business meaning*, not metric direction — a rising cost is red even though the number went up, exactly as DeployGuard's payroll-expenditure trend arrows did.

**5. Every dense screen has a "so what" layer above it.** The Main OS Command Center's quiet, only-appears-if-nonzero attention strip (§3.3) is the strongest single idea found in the donor codebase: a cross-domain, one-glance answer to "what needs me right now," computed from parallel counts, silent when there's nothing to act on. Every command-center-class screen in §7 gets one — this is the mechanical implementation of §2.4's "every screen answers a question."

**6. Mobile-first means truck-stop-first, not phone-mockup-first.** The target user checks a phone with one hand, in sunlight, possibly with gloves on, on a 3G connection outside Lusaka, not at a desk. Every mobile recommendation in §7 is evaluated against that condition, not against how it looks in a clean simulator screenshot — large touch targets, offline-tolerant data patterns, and legible-in-sunlight contrast take priority over density or animation richness on any driver-facing screen.

---

## 3. DeployGuard pattern reuse inventory

Grounded in a direct read of the donor codebase's `.js`/`.xml`/`.css` (paths cited). Where a named pattern turns out to be a narrower or different thing than its name suggests, this section says so plainly rather than forcing the requested mapping. **Read together with §2.1: reuse here means mechanics and interaction models, not DeployGuard's dark militaristic visual register** — every pattern below is adopted for *how it works*, restyled per doc 17's own palette, never re-skinned as-is.

### 3.0 The uncomfortable finding first: two design systems, not one

DeployGuard has no single imported design-system source of truth. `security_base/static/src/css/design_system.css` is a real, deliberate token file (self-labeled "Clean Corporate Light — Goldman Sachs meets modern SaaS") but it only reskins *stock* Odoo widgets — none of the custom dashboards import it. Every custom dashboard instead re-declares its own near-identical slate/navy palette (`#0f172a`, `#1e293b`, `#64748b`, `#e2e8f0` recur verbatim across a dozen files) under its own 2–4 letter CSS prefix (`.bcc-*`, `.fd-*`, `.rb-*`, `.dgcc-*`, `.dfal-*`...) — a de facto standard maintained by copy-paste discipline, not a real shared library. Layered on top of that is the genuine visual-language fork described in Principle 1 above.

**The lesson for DeployFleet, stated once so it doesn't need repeating per component below:** build [17-design-system.md](17-design-system.md)'s token system and [18-component-library.md](18-component-library.md)'s `deployfleet_ui` module *first*, and have every subsequent dashboard consume them by import, not by copying the last dashboard's CSS file and renaming the prefix. This is a process discipline, not a design opinion, and it's the one thing DeployGuard's own team visibly meant to do (the design-system file exists!) and didn't finish following through on.

Also worth knowing before evaluating "chart" and "real-time" claims below: **no charting library is used anywhere in DeployGuard** (no Chart.js, ApexCharts, D3 — zero matches). Every visual "chart" is hand-rolled div/SVG. **No real-time push exists either** — no websockets, no `bus_service` subscriptions in custom code; every "live" dashboard is load-on-open plus a manual refresh. Both are legitimate, lightweight choices worth deliberately deciding whether to keep or upgrade (§7, doc 18), not defaults to assume away.

### 3.1 Mega Menu → adapt as-is, consolidate the shared CSS

**What it actually is:** not a navbar dropdown — a full-screen modal overlay (`position:fixed; inset:0`) triggered as a client action, not a menu widget. Dark `rgba(15,23,42,.45)` scrim with `backdrop-filter: blur(12px)` behind a centered white rounded card (max-width 1100px), scale+fade entrance. Header with search input and a close button that rotates on hover; a horizontal pill tab bar; body is a responsive 3-column card grid (icon chip, title, description, colored tag) that collapses to 2 then 1 column. Client-side substring search filters cards instantly, no debounce, no server round-trip. Five separate modules (workforce, fleet, equipment, clients/sites, rostering) each ship their own copy of this component, all sharing one CSS file's class names by bundle-concatenation luck rather than an explicit shared import — fragile, but proof the pattern was consciously repeated.

**Reuse for DeployFleet:** directly, as the **Domain Mega Menu** pattern — one per major operational domain (Fleet & Vehicles, Dispatch & Trips, Compliance, Billing & Finance, Driver & HR, AI & Intelligence), reachable from the global nav (§7.1) and from contextual "see everything in this domain" entry points. Fix the fragility DeployGuard shipped: one real shared OWL component (`MegaMenu`, cataloged in doc 18), not five copy-pasted files.

### 3.2 Enterprise OS Launcher → the strongest single asset, adapt directly

**What it actually is:** genuinely replaces Odoo's native app grid, patching `web.NavBar`'s `AppsMenu` via OWL extension inheritance. The heaviest glassmorphism in the codebase: `backdrop-filter: blur(28px) saturate(135%)` over a near-black gradient card with a translucent hairline border and an inset top highlight — real glass, not a css-filter afterthought. Layout: search box, then a **"priority workspaces" strip** — six accent-colored pill shortcuts with `Alt+<letter>` keyboard badges jumping straight to the most-used command centers — above the full app grid, where every Odoo top-level menu renders as a gradient icon tile keyed by keyword-matched color family. Client-side search, escape-to-close, click-outside-to-close; no favorites/recents persistence, no drag-drop reordering.

**Reuse for DeployFleet:** the mechanics, not the mechanism. Two specific ideas were preserved deliberately: the **priority-workspace strip with keyboard shortcuts** and the **keyword-to-gradient color-family mapping** for auto-coloring destination tiles, extended with the AI-content violet family (doc 17) for the AI & Intelligence domain specifically. New for DeployFleet: **persist recents and pin favorites** — a genuine gap in the source component, and a real click-reduction win for a dispatcher who opens the same screens every morning.

**Built as a self-contained overlay, not a `web.NavBar` patch — a deliberate risk decision made during Phase B Slice 3.** DeployGuard's launcher works by patching Odoo's own `NavBar`/`AppsMenu` template via OWL extension inheritance, literally replacing the native apps button's behavior. DeployFleet's implementation does not do this: a bad xpath match against the exact Odoo 19 nightly this project runs on could break the top navigation bar across the *entire product*, not just this feature, and that template's current internal structure cannot be verified against a live instance from a development environment with no browser. Instead, the DeployFleet Launcher is a self-contained, always-mounted overlay — a global `Alt+L` hotkey (not `Alt+Space`, which collides with Windows' own system-menu shortcut at the OS level) plus a persistent corner trigger button — delivering every other part of the spec without touching Odoo's own chrome. Patching the native apps-button to open this same overlay remains a valid future enhancement once it can be verified against a live instance first, not something to attempt speculatively against production chrome. The priority-strip shortcuts shipped in Slice 3: `Alt+D` Dispatch & Trips, `Alt+F` Fleet & Vehicles, `Alt+C` Compliance, `Alt+B` Billing & Finance, `Alt+R` Driver & HR, `Alt+I` AI & Intelligence — pointed at the six Mega Menu domains, since neither Mission Control nor any other Phase C flagship screen existed yet. `Alt+H` was deliberately left unassigned at the time specifically so Mission Control (Phase C / Slice 1, §7.2) could reclaim it once built, exactly as doc 16 §5 always intended — it now does.

A second implementation-discovered constraint worth recording: DeployFleet nests all 43 modules under one single "DeployFleet" app menu rather than the many distinct top-level apps DeployGuard used, so a destination grid populated purely from Odoo's own `getApps()` would be nearly empty. The Launcher's grid is populated from the six curated Mega Menu domains instead (genuinely the meaningful destinations today), with Odoo's own real top-level apps (Settings, Discuss, ...) shown separately as "Other Apps."

### 3.3 Command Centers → keep the attention-strip idea, resolve the visual-language split explicitly

**What exists:** at least five, in two incompatible visual languages (Principle 1). The Main OS Command Center and Workforce Command Center share the mega-menu's glass-modal shell, plus one genuinely distinct and excellent addition: a slim **attention strip** beneath the tab bar that renders *only when there's something to act on* (five parallel `search_count` calls — unfilled critical slots, no-shows, certs expiring in 7 days, pending leave, draft invoices), each count a clickable pill jumping straight to the underlying list. The Billing Command Center abandons the glass-modal shell entirely for a flat, desaturated, Stripe-style in-page workspace — a deliberate, apparently later, un-reconciled design pivot. The Executive/Analytics Dashboard defines yet a *third* independent token set and uses a persistent navy sidebar rather than either overlay pattern. No dedicated "Fleet Ops Command Center" client action exists — don't assume one when reading old references to "Fleet Widgets" (§3.7 is the real fleet pattern).

**Reuse for DeployFleet:** the **attention strip is the single most operationally valuable idea in this entire audit** and is adopted platform-wide, not just on the home screen — every command-center-class or Intelligence-class screen in §7 (Mission Control, Fleet Command Center, Maintenance Intelligence, Billing Workspace, Copilot Console) gets its own domain-scoped attention strip, computed the same way (parallel counts, silent when empty, click-through to the underlying record set). The visual-language split is *not* inherited — per Principle 1, Command Layer screens (home, launch, overview) get the glass treatment; Workspace Layer screens (billing, compliance registers) get the flat treatment, applied *consistently* rather than as an unexplained fork, and both restyled per §2.1's Tesla/Stripe/Linear register rather than DeployGuard's own.

### 3.4 Dashboard Cards → componentize what DeployGuard only converged on by convention

**What exists:** the same DNA — label+icon header, one big bold number, a short colored caption, subtle hover lift, no chart, no library — repeated with variation across nearly every dashboard, sometimes as inline-styled Bootstrap grid markup (Workforce Dashboard), sometimes with a colored left-border stripe (Revenue Dashboard), sometimes a top-border stripe (Attendance History). No two dashboards use the exact same markup for what is conceptually the identical component.

**Reuse for DeployFleet:** the concept, standardized once as a real OWL component (`MetricCard`, cataloged in doc 18) rather than five hand-rolled variants. Recommend the **left-border-stripe variant** (cleaner at a glance, reads well in dense rows, and doubles naturally as a status-color carrier per Principle 4) as the one true form, retired everywhere else.

### 3.5 Quick Actions → reframe: a button stack and quick-create modals, not a floating-action tray

**What exists:** no FAB, no floating tray anywhere in the codebase (explicitly checked). "Quick Actions" is a **vertical stack of full-width, colored, icon-labeled buttons pinned in a dashboard sidebar** (e.g., "Auto-Fill Gaps" with an inline loading spinner and button-text swap while running) plus lightweight **quick-create modals** (3–5 fields, single submit, live-calculated totals as you type) launched from row-level buttons.

**Reuse for DeployFleet:** the sidebar action-stack and quick-create-modal pattern, honestly described as such. A genuinely new addition for DeployFleet worth layering on top (cataloged in doc 18 as the `QuickActionBar`): a **contextual quick-action rail** that changes its button set based on what record is currently open — a floating, docked (not modal) panel is a legitimate upgrade over the source's static sidebar, since a dispatcher moving between shipment, trip, and driver records benefits from actions that follow the selection rather than living in one fixed sidebar. This is the mechanical answer to §2.5's "no dead ends" principle.

### 3.6 Roster Board → the flagship reuse, adapted into the Dispatch Board

**What exists:** the richest, most sophisticated interaction pattern in the donor codebase, by a wide margin. A CSS-grid shell (fixed sidebar + timeline grid of site/post rows × date columns, cells = slot cards), with a right-hand guard-suggestion pool that appears only when a slot is selected. The mechanics, in order of value to DeployFleet:

- **Native HTML5 drag-and-drop** (no library) — draggable suggestion cards, drop-target cells, the same assignment call path whether triggered by drag or by click.
- **A three-way server response contract**: every assignment attempt returns `success`, `hard_block` (flatly refused, inline red error), or `override_required` — the last of which opens a **typed-reason override dialog** that becomes part of the audit trail. This is a genuinely excellent, directly portable compliance-UX pattern already conceptually present in `deployfleet_dispatch_compliance`'s backend (hard-disqualify vs. override-with-reason) — it currently has no matching frontend at all.
- **Scoring-engine suggestions surfaced inline**, not just computed server-side and buried in a form — ranked candidates with visible per-candidate score, both draggable and click-to-assign.
- **A pulsing critical-gap visual alarm** (`@keyframes` box-shadow pulse, stops on hover) on unfilled slots that matter — a deliberate, restrained urgency cue, not a blanket red wash.
- **Right-click context menu** on cards for secondary actions (suggest / unassign / view / swap).
- **Bulk auto-fill actions** with proper loading-state button feedback.
- **A real, considered mobile breakpoint**: below ~760px the side suggestion panel becomes a `position:fixed` bottom sheet with a drag handle and slide-up animation — not just column-stacking.

**Reuse for DeployFleet — this is §7.9's flagship, detailed there.** Every mechanic above maps almost one-to-one: guard→driver-or-vehicle, post/slot→trip/route leg, the hard-block/override-with-reason contract already exists in `deployfleet_dispatch_compliance`'s backend and just needs this exact frontend contract wired to it, and the scoring-suggestions panel maps directly onto `action_suggest_assignments()`'s existing output — restyled entirely per §2.1, since this is the mechanic worth keeping, not DeployGuard's rostering-specific visual chrome.

### 3.7 Fleet Widgets → the direct ancestor of the Fleet Command Center

**What exists:** the Fleet Dashboard — sidebar + tabbed table (Vehicles/Runs/Fuel) + a **row-click slide-in inspector panel** (the table area re-grids to make room rather than navigating away), one-click state-transition buttons, small quick-create modals with live-calculated totals, and a genuinely nice touch: a **client-side CSV export** that builds the file in-browser with no server round-trip. A cosmetic "LIVE" pill exists but the data is load-on-open, not pushed.

**Reuse for DeployFleet — detailed in §7.10 as the Fleet Command Center's direct pattern ancestor.** The sidebar/table/slide-in-inspector shell, one-click state transitions, and the in-browser CSV export are all worth carrying forward as-is. The cosmetic-only "LIVE" label is *not* — if DeployFleet claims live, it should be live (§7.10 recommends where actual polling is worth the cost and where it isn't).

### 3.8 Analytics Cards → keep the DIY approach, know its ceiling

**What exists:** beyond the KPI stat cards already covered in §3.4, one genuinely distinct visualization: a hand-rolled, div-based **paired bar chart** (invoiced vs. paid, per period) with CSS-transitioned heights — no charting library anywhere in the codebase.

**Reuse for DeployFleet:** keep the no-dependency philosophy where the visualization stays this simple (period-over-period paired or single-series bars, no zoom/tooltip/drill-down needed). Doc 18's signature widgets (Revenue River, Profit Waterfall, Driver Performance Radar) need genuine multi-series and drill-down capability the DIY approach can't cleanly express — that's the one place recommending a real, small, evaluated charting library is justified rather than DIY-for-its-own-sake; doc 18 specifies the requirement without prescribing a specific package.

### 3.9 Timeline Views → reframe honestly: a grouped, expandable history log

**What exists:** Attendance History is the closest match to "timeline" in the source and it is **not** a timeline visualization — no time-axis, no line-with-dots rendering. It's a date-grouped list (most recent date first), each date a card with a dark header bar and count, rows beneath colored by a left status-stripe, with a click-to-expand-in-place (not a modal) detail panel showing hour-bucket breakdowns. Well executed, genuinely useful — just not a timeline by any visual definition.

**Reuse for DeployFleet:** adopt the actual pattern under its actual name — a **grouped expandable history log** — for trip history, delivery history, driver-performance events, and compliance-document history (§7.10, §7.14). Where DeployFleet genuinely needs a time-axis visualization (a vehicle's day, a multi-stop route's schedule, a driver's hours-of-service across a week) that is new UX territory DeployGuard doesn't have an answer for — proposed fresh in §6 as the **Animated Route Timeline**.

### 3.10 Visual KPIs → the circular gauge is directly portable; extend the trend-arrow convention

**What exists:** a genuinely well-built, dependency-free SVG circular progress-ring field widget (band-colored: green ≥80, amber 60–79, red <60, with matching text label), registered as a real Odoo field widget usable declaratively on any integer field — and a simple trend-arrow badge convention (colored by business meaning, not by literal direction — DeployGuard correctly renders a *rising* payroll cost in red because rising cost is bad, not because the arrow points up). No sparklines exist anywhere.

**Reuse for DeployFleet:** the gauge widget, directly, becomes the base of the **Truck Health Ring** and **Fleet Score** signature widgets (§6), retargeted at driver safety score, on-time delivery percentage, vehicle utilization, and fuel efficiency. The trend-arrow convention, extended platform-wide with the same discipline: color follows business meaning per metric, decided explicitly per KPI, not defaulted to "up is green."

---

## 4. Design system foundation — see [17-design-system.md](17-design-system.md) for the full spec

Doc 17 is where the token system actually lives — full color scales, type scale, spacing unit, elevation and glass recipes per layer, iconography rules, dark-mode strategy, and accessibility requirements, specified as "no developer ever invents a button again." Two decisions from that document are load-bearing enough to restate inline here, since nearly every section below references them directly:

**Status color semantics — adopted platform-wide, not per-dashboard:**

| Meaning | Color family | Applies to |
|---|---|---|
| On-time / compliant / available / healthy | Green | Trip on schedule, document valid, vehicle available, driver compliant |
| Needs attention soon / approaching threshold | Amber | Document expiring within N days, maintenance due soon, invoice approaching due date |
| Critical / blocking / expired / broken | Red | Expired compliance document, vehicle breakdown, overdue invoice, hard-disqualified dispatch candidate |
| Informational / in progress / neutral state | Blue | In-transit, draft, awaiting confirmation |
| **AI-authored or AI-suggested content** | **Violet** — a new, deliberate fifth semantic, absent from DeployGuard entirely | Any AI-agent suggestion, prediction, or pre-filled field, anywhere in the product, before human approval |

The violet convention is the single most important net-new addition to the color system relative to DeployGuard, because DeployGuard's AI engine never had a real UI to need one. Its job is to make Principle 2 (§2.6) — AI is a visible, distinct author — literally impossible to miss: a predicted-maintenance card, a suggested dispatch candidate, an AI-drafted customer message, all carry the same violet left-border/badge treatment, everywhere, so approving or rejecting AI output never requires the user to first figure out that it *is* AI output.

**Brand palette — deliberately distinct from DeployGuard's navy, per [CLAUDE.md](../../CLAUDE.md)'s "not a re-skin" instruction, and from its militaristic register per §2.1.** Full specification in doc 17; the direction is a deep teal-blue primary (professional, distinct from DeployGuard's navy, evokes horizon/movement rather than finance) paired with a warm amber-orange accent drawn from road-safety/high-visibility signage rather than from DeployGuard's palette at all.

---

## 5. Global navigation & the home experience

**Global Navigation** becomes three coordinated surfaces, replacing today's single flat app menu:

1. **The DeployFleet Launcher** (§3.2) — the entry point from anywhere, `Alt+L` or a persistent corner control. Priority-workspace strip with keyboard shortcuts, a destination grid below, user-pinned favorites and recents (the one deliberate improvement over DeployGuard's source).
2. **Domain Mega Menus** (§3.1) — one per operational domain, reachable both from the launcher and as a persistent top-bar entry per domain, so a dispatcher living inside Dispatch all day never has to leave that context to jump between Fleet, Compliance, and Billing sub-areas.
3. **A Command Palette** (`Cmd/Ctrl+K`) — genuinely new, absent from DeployGuard entirely (§6). Type a shipment number, a driver name, a vehicle plate, or an action verb ("assign driver," "log fuel," "approve invoice") and jump directly there or execute it inline. This is the single highest-leverage click-reduction opportunity in the whole document: today, reaching any specific record requires navigating the app menu → sub-menu → list → filter → row, every time.

**Mission Control (the Home Dashboard, §2.3)** is role-scoped, not one screen, and is where §2.5's "first five minutes" principle is executed literally:

- **Owner/Manager**: opens on moving trucks (the Live Fleet Map, §6), today's revenue and active loads, today's dispatches, AI recommendations, driver statuses, and a silent-unless-nonzero attention strip (§3.3) — the Main Command Center's attention-strip-plus-launchpad pattern, scoped platform-wide, restyled per §2.1. Never a menu list of model names as the first thing seen.
- **Dispatcher**: opens directly to the Dispatch Board (§7.9), not a generic home screen — a dispatcher's day starts with today's board, not a launcher.
- **Driver (mobile)**: today's assigned trip, one tap to navigation/inspection/POD — detailed in §7.17.
- **Customer (portal)**: shipment status and documents — detailed in §7.19.

---

## 6. New DeployFleet-native UX concepts, and the signature "wow" widget set

Ideas with no DeployGuard ancestor at all — proposed because transportation/logistics has needs a workforce-scheduling platform simply never had. The foundational concepts first, then the full signature-widget set (fully specified in [18-component-library.md](18-component-library.md)) that should become instantly recognizable as *DeployFleet's*, the way a Roster Board or a Command Center is recognizably DeployGuard's.

**Foundational new concepts:**

- **Command Palette** (`Cmd/Ctrl+K`, described above) — universal search + action execution, the single largest click-reduction lever available.
- **Live Fleet Map** — a real map view (genuinely absent from DeployGuard and from DeployFleet today alike) showing active vehicles as pins with breadcrumb trails, route lines, and depot markers; clicking a pin opens that vehicle's Fleet Command Center inspector inline rather than navigating away. This is the single most-requested-feeling screen a trucking company will expect on first demo and the platform currently has no answer for at all.
- **Compliance Traffic-Light Wall** — every vehicle and driver as a single-row-per-entity grid of red/amber/green status chips (insurance, roadworthiness, permit, license, medical) — one screen answering "who can't legally run today" without opening a single record.
- **Copilot Rail** — a persistent, collapsed-by-default docked panel (Command Layer treatment, violet-accented per doc 17) present across every workspace, expanding on demand to show contextually relevant agent output for whatever record is open — never a separate chatbot window disconnected from context, and never auto-executing anything per the mandatory approval pipeline. Detailed in §8.

**The signature widget set** — the components that should make someone say "that's a DeployFleet screen" on sight:

| Widget | What it does | Lives in | Priority |
|---|---|---|---|
| Live Fleet Map | Real-time vehicle pins, breadcrumb trails, route lines, depot markers | Mission Control, Fleet Command Center (§7.7, §7.10) | Flagship |
| Animated Route Timeline | Genuine time-axis view of a vehicle's day or a multi-stop route | Fleet Command Center, Customer Portal (§7.8, §7.18) | Flagship |
| Truck Health Ring | Per-vehicle SVG gauge (§3.10 lineage) blending compliance, maintenance due-date, and utilization into one glanceable score | Fleet Command Center vehicle inspector (§7.10) | Near-term |
| Driver Performance Radar | Multi-axis (safety, on-time %, fuel efficiency, compliance, customer feedback) spider chart, richer than a single gauge | Driver Workspace (§7.14) | Near-term |
| Fleet Score | One overall fleet-health number on Mission Control, rolling up vehicle health, compliance, and on-time performance | Mission Control (§5) | Near-term |
| AI Recommendation Card | The standard, consistent format every ambient AI suggestion renders in — recommendation text, quantified impact where available, accept/dismiss tied to the approval pipeline | Everywhere per §8 | Flagship |
| Revenue River | An animated flow visualization of revenue moving from shipments → invoices → payments, surfacing where cash is stuck | Billing Workspace (§7.13) | Near-term |
| Profit Waterfall | Revenue-minus-cost walk (fuel, maintenance, driver pay, overhead) per vehicle or per route, answering §2.4's Financial Intelligence question directly | Billing Workspace, Fleet Command Center (§7.10, §7.13) | Near-term |
| Fleet Heat Map | Geographic density/utilization heat map of where the fleet actually operates versus where lanes are underused | Fleet Command Center, Financial Intelligence | Aspirational |
| Risk Matrix | Two-axis (likelihood × impact) plot of compliance/driver/vehicle risk, turning the Compliance Traffic-Light Wall's raw list into a prioritized view | Compliance areas (§7.11 lineage) | Aspirational |
| Maintenance Planner | A calendar-plus-Gantt hybrid scheduling view, not just a list of due dates | Maintenance Intelligence (§7.11) | Near-term |
| Fleet Calendar | The elevated, signature version of §7.8's calendar views — maintenance, leave, and compliance expiry, color-coded per doc 17's status semantics | Maintenance Intelligence, Compliance areas | Near-term |
| Load Builder | A truck-silhouette capacity-fill visualization as cargo is assigned to a multi-drop trip | Dispatch Board (ties to [12-ltl-freight-management-architecture.md](12-ltl-freight-management-architecture.md)) | Aspirational, gated on multi-stop model |
| Proof-of-Delivery Gallery | POD photos/signatures surfaced visually, not as buried form attachments | Billing Workspace, Customer Portal (§7.13, §7.18) | Near-term |
| Fleet Globe | An ambitious 3D/global network view for multi-region or multi-country operators, showing the whole operation at once | Aspirational, explicitly gated on real multi-region demand existing — do not build speculatively | Aspirational |

Priority tags (Flagship / Near-term / Aspirational) map to §11's phased rollout, not to this table's row order — full component contracts (props, states, data sources per DeployFleet model) live in doc 18.

---

## 7. Systematic area-by-area analysis

Each area: **current state**, **problems** (evaluated against first impression, discoverability, ease of use, visual hierarchy, mobile usability, AI workflows, dashboard design, navigation, task speed, click count, cognitive load, as relevant to that area), **missing cues/dashboards**, and **redesign direction** (OWL/glass/animation/AI/contextual-action opportunities, plus which DeployGuard pattern from §3 it draws on, if any).

### 7.1 Global Navigation
**Current state:** a single flat Odoo app menu, every module nested underneath as children — no mega menu, no launcher, no command palette, no search-to-navigate. **Problems:** discoverability is entirely dependent on knowing the menu hierarchy by heart; there is no way to jump to a specific record without navigating through a list first; first impression on demo is "generic Odoo," immediately, before any data is even seen. **Missing cues:** no visual distinction between domains, no indication of what needs attention anywhere in the nav chrome itself. **Redesign direction:** DeployFleet Launcher + Domain Mega Menus + Command Palette, per §5, drawing directly on §3.1/§3.2.

### 7.2 Home Dashboard → Mission Control
**Current state (Phase C / Slice 1 — built):** a real screen now exists — reachable via the menu (sequence 0, ahead of the six Mega Menu domains) and via the Launcher's `Alt+H` shortcut. **What shipped:** a silent-unless-nonzero attention strip (doc 16 §3.3) computed from five genuine parallel `searchCount` queries against real, field-verified models (unassigned shipments, expired/expiring-soon compliance documents, vehicles in breakdown, pending AI approvals — the last using the `ai` StatusPill variant, a deliberate, correct use of doc 17 §2.3's reserved violet since this pill is literally about AI-suggested actions awaiting review); three KPI cards (Active Vehicles, Active Shipments, Confirmed Revenue); and a quick-links row to all six Mega Menu domains. **What's still a placeholder relative to the original vision:** no Live Fleet Map yet (§6, gated on a real GPS feed — Phase E), no Fleet Score hero metric (gated on the Truck Health Ring existing first). **Mobile-first, built-in from this slice on:** every touch target on this screen is checked against a 44px minimum (a retroactive fix also applied to the shared Button and StatusPill atoms, since both are reused everywhere), and the KPI grid stacks to one column below 641px rather than the reverse (start dense, relax for mobile) — the discipline CLAUDE.md's explicit mobile-first instruction asks for, applied as the default going forward for every Phase C screen, not just this one.

### 7.3 Module Dashboards → domain Intelligence screens
**Current state:** none of Phase 1–5's modules have a dashboard screen — each is a list view with filters. **Problems:** a fleet manager wanting "how many vehicles need maintenance this week" must build a filtered list manually every time; no persistent view of module health. **Redesign direction:** every phase-group becomes a named Intelligence screen per §2.3 (Fleet Intelligence, Maintenance Intelligence, Compliance Intelligence, Financial Intelligence), each answering its own one-line question (§2.4), using the standardized `MetricCard` (§3.4/doc 18) plus its own attention strip, consuming the shared design-system tokens rather than bespoke CSS per dashboard (§3.0's lesson, applied).

### 7.4 List Views
**Current state:** stock Odoo lists throughout, functional but visually undifferentiated from any other Odoo install. **Problems:** no status-color coding beyond default badges in most lists; no inline quick actions beyond the two dispatch-list buttons found; dense financial/compliance lists have no visual hierarchy beyond column order. **Redesign direction:** apply the platform-wide status-color semantics (doc 17) as row-left-border stripes consistently (the Revenue Dashboard/Attendance History convention, §3.4/§3.9, generalized to every list, not just dashboards); add row-level contextual quick actions matching the record's available state transitions, styled consistently with the Fleet Dashboard's one-click transition buttons (§3.7) — never a dead-end row per §2.5.

### 7.5 Form Views
**Current state:** stock Odoo forms, every field visible at once regardless of relevance to current state. **Problems:** cognitive load — a shipment or vehicle form shows compliance, billing, and operational fields simultaneously regardless of what the current viewer actually needs; [15-load-sheet-architecture.md](15-load-sheet-architecture.md) already flagged this exact problem for the load sheet specifically. **Redesign direction:** the collapsed-summary-card-plus-expandable-sections treatment doc 15 already recommended for shipments extends platform-wide to vehicle, driver, and trip records — a compact identity header (plate/name/status) always visible, with maintenance/compliance/financial/history sections collapsed by default and expandable on demand, told as one narrative per §2.5's storytelling principle (the "Truck 504" example) rather than a field dump, and always closing with contextual next-action buttons per §2.5.

### 7.6 Kanban Views
**Current state:** three bare kanban boards (dispatch assignment, shipment, vehicle), 3–4 fields per card, no avatars, no color logic beyond default grouping. **Problems:** a kanban card today conveys almost no information at a glance — exactly the gap the Dispatch Board section addresses in depth. **Redesign direction:** richer card templates (status-color left border, avatar/icon, key metric, AI-suggestion badge where relevant) as the default `MetricCard`-adjacent card component, applied to all three existing boards even before the full custom Dispatch Board (§7.9) ships, as a faster, smaller first win.

### 7.7 Map Views
**Current state:** does not exist anywhere in the product. **Problems:** for a logistics platform this is the single largest visible gap on first demo — a prospective customer will expect to see trucks on a map within the first five minutes, per §2.5. **Redesign direction:** the Live Fleet Map (§6) — vehicle pins with breadcrumb trails, route lines, depot markers, click-through to the Fleet Command Center inspector; also a static depot/route network map as a lighter-weight first version if live GPS feed integration isn't ready.

### 7.8 Calendar Views
**Current state:** does not exist anywhere — no calendar for trips, maintenance schedules, leave, or compliance-document expiry. **Problems:** a fleet manager currently has no way to see "what expires this month" or "what's scheduled this week" without building a filtered list and reading dates manually. **Redesign direction:** a shared calendar surface (standard Odoo calendar view is an acceptable, fast first step here) evolving into the signature **Fleet Calendar** (§6) — color-coded per doc 17's status semantics — across maintenance schedules, leave requests, and compliance-document expiry, genuinely low-effort, high-value, and currently 100% missing.

### 7.9 Dispatch Board — flagship reuse
**Answers:** *which load should go next?* (§2.4)
**Current state:** a bare kanban card grouped by state; the underlying scoring, hard-disqualify, and override-with-reason logic in `deployfleet_dispatch`/`deployfleet_dispatch_compliance` is fully built and has no matching frontend richness at all. **Problems:** a dispatcher today clicks into each proposed assignment individually to see the score and confirm — there is no board-level view of the day, no visual urgency signal for unassigned shipments, no drag-drop. **Missing cues:** nothing distinguishes an urgent unassigned shipment from a routine one; the override-reason requirement exists in the backend with only a plain form field to satisfy it. **Redesign direction — directly adapting the Roster Board (§3.6), domain-remapped:** a timeline/board hybrid (shipments as rows or cards, driver/vehicle assignment as the interaction), native drag-drop assignment, a right-hand ranked-candidate suggestion panel sourced from `action_suggest_assignments()`, the exact three-way hard-block/override-required/success contract wired to a proper override dialog demanding a typed reason, a pulsing urgency indicator on unassigned shipments approaching their pickup window, right-click context actions, bulk "auto-assign remaining," and the same considered mobile-bottom-sheet breakpoint DeployGuard shipped for its suggestion panel. **Ambient AI on this screen** (§8): an AI Recommendation Card surfaced inline — *"Swap Truck 12 with Truck 17 on this route. Estimated savings: $240."* — sitting alongside the rule-based scoring suggestions, visually distinguished by the violet convention, never auto-applied. This is the single highest-priority build to come out of this document.

**Current state (Phase C / Slice 2 — built), with three deliberate scope corrections relative to the description above:**

1. **Tap-to-assign, not native drag-drop.** HTML5 drag-and-drop has poor touch-device support, and CLAUDE.md's mobile-first mandate applies to every Phase C screen without exception — building drag-drop as the *primary* interaction would directly contradict it. The shipped interaction is tap-to-expand a shipment card, "Suggest Assignments" to populate ranked candidates (`action_suggest_assignments()`, unchanged), then tap "Confirm" on a candidate. Desktop drag-drop remains a valid future progressive enhancement layered on top, not a reversal of this decision.
2. **The backend contract is a plain `UserError`, not a three-way `{success, hard_block, override_required}` response.** `deployfleet.dispatch.assignment.action_confirm()` (in both `deployfleet_dispatch` and the `deployfleet_dispatch_compliance` override) raises a `UserError` demanding a reason when a higher-scored sibling exists or a compliance document has expired — it does not return a structured result the way DeployGuard's Roster Board did. The shipped override dialog reconciles this: on a caught error it shows the raised message and a single reason textarea, and on submit writes that one reason to both `override_reason` and `compliance_override_reason` before retrying `action_confirm` — one operator input satisfies whichever backend check actually fired, without the frontend parsing the error message to tell them apart.
3. **Workspace Layer, not Command Layer** — the one deliberate exception to every other Phase B/C screen shipped so far (Mission Control, the Mega Menus, the Launcher are all Command Layer dark glass). §2.1 Principle 1 is explicit that sustained-work screens must not fight a translucent card for contrast, and a dispatcher's shift-long board is exactly that case. Flat, light, high-contrast cards; a left-border-stripe urgency color (danger/warning, matching the `MetricCard` convention) instead of full-card color-wash; a `df-pulse-ambient` pulse (the one deliberate Ambient-band exception per doc 19) on cards past their pickup window.

**What's still a placeholder relative to the original vision above:** no right-hand persistent candidate panel (candidates render inline in the expanded card instead); no bulk "auto-assign remaining"; no right-click context actions; no AI Recommendation Card yet (gated on the Copilot Rail/Console work, §7.16) — the scoring-suggestion panel is the existing rule-based `action_suggest_assignments()` output only, not yet annotated with an ambient AI suggestion alongside it.

### 7.10 Fleet Command Center
**Answers:** *which trucks are making money?* (§2.4)
**Current state:** a stock vehicle list/form/kanban; no dashboard, no inspector, no consolidated fleet view. **Problems:** seeing a vehicle's compliance, maintenance, fuel, and current assignment together requires navigating four separate modules' list views. **Redesign direction — adapting the Fleet Dashboard (§3.7) directly:** sidebar + tabbed table (Vehicles/Trips/Fuel/Maintenance) + row-click slide-in inspector, told as one narrative per §2.5 — *"Truck 504. Currently in transit to Copperbelt, ETA 4:20 PM, 72% fuel, K18,400 revenue this month, next service in 6 days, driver score 91, last inspection Tuesday"* — rather than four separate tabs; the **Truck Health Ring** (§6) as the vehicle's single at-a-glance score, the **Profit Waterfall** (§6) for its revenue-minus-cost breakdown; one-click state transitions (available/in-transit/maintenance/breakdown); genuine live status (§3.0's caveat about DeployGuard's cosmetic-only "LIVE" label — here it should be real, since vehicle state changes are exactly the kind of event `deployfleet_event_bus` already fires and a dashboard can genuinely subscribe to); contextual actions always visible per §2.5 (assign load, schedule maintenance, contact driver, open route, view expenses, ask the Copilot, generate a report — never a dead end); in-browser CSV export retained from the source pattern.

**Current state (Phase C / Slice 3 — built), with the same transparency discipline applied to the Dispatch Board (§7.9):** a real, working screen — a status-filterable vehicle list (chips: All/Available/Assigned/Maintenance/Breakdown, each a live count) where tapping a card expands it into a genuine consolidated read across four models: current trip (`deployfleet.trip`), compliance documents (`deployfleet.compliance.document`, color-coded valid/expiring/expired), maintenance schedules (`deployfleet.maintenance.schedule`, due vs. on-schedule), and the last 5 fuel logs (`deployfleet.fuel.log`, anomalies flagged) — plus working one-tap status-transition actions (Mark Available / Send to Maintenance / Report Breakdown) wired to the vehicle's real `action_set_*` methods, not decorative buttons. **Workspace Layer**, same reasoning as the Dispatch Board: a fleet manager reviewing this screen needs sustained high-contrast readability, not Command-Layer glass.

**What's still a placeholder relative to the description above:** no sidebar + tabbed table layout — this ships as the same tap-to-expand accordion pattern the Dispatch Board established, since there is no Drawer/Inspector slide-in component yet (still "Not yet built" in doc 18's catalog) and building a one-off slide-in panel ahead of a real one seemed worse than reusing a pattern already shipped and verified; no Truck Health Ring or Profit Waterfall (both still "Aspirational" — no Fleet Score/revenue-per-vehicle computation exists yet to back them); no narrative one-sentence summary (*"Truck 504. Currently in transit..."*) — the consolidated data renders as labeled sections, not prose; no live event-bus-driven status updates (the screen reloads on action, it does not subscribe to `deployfleet_event_bus` yet); no CSV export.

### 7.11 Maintenance Center → Maintenance Intelligence
**Answers:** *what is about to fail?* (§2.4)
**Current state:** stock list/form for maintenance schedules; predictive-maintenance output from Phase 5 (`deployfleet.maintenance.prediction`) has only a standard Odoo view, disconnected visually from the schedules it's meant to inform. **Problems:** a maintenance manager cannot currently see "what's due soon, what's predicted, what's overdue" in one place — has to cross-reference two modules manually. **Missing dashboards:** entirely missing. **Redesign direction:** a Command-Layer summary (attention strip: overdue, due this week, AI-predicted-at-risk) built around the **Maintenance Planner** signature widget (§6, a calendar-plus-Gantt hybrid, not just a due-date list), with predictions visually distinguished via the violet AI-content convention so a manager can tell at a glance which entries are scheduled fact versus model prediction. **Ambient AI on this screen** (§8): *"Delay this service by 6 days — vehicle utilization is low this week and the part isn't due for replacement yet"* as an AI Recommendation Card, actioned or dismissed, never silently applied.

### 7.12 Workshop UI
**Current state:** stock list/form for job cards and job lines; no kanban-by-status, no visual job-card board. **Problems:** a workshop supervisor tracking multiple open jobs has no at-a-glance board of what's in diagnosis vs. repair vs. awaiting parts. **Redesign direction:** a job-card kanban board (diagnosis → repair → parts-wait → complete), each card showing vehicle, technician, elapsed time, and parts-line cost running total; no direct DeployGuard ancestor exists for this specific workflow, so this is new design, though it borrows the Fleet Dashboard's inspector-panel mechanic for a card's full detail.

### 7.13 Billing Workspace → Financial Intelligence
**Answers:** *where are we losing money?* (§2.4)
**Current state:** stock list/form for invoices; the accounting-integration work (this session's chart-of-accounts fix, ZRA submission) is entirely invisible in the UI beyond a status field. **Problems:** an AR-aging view, a "what's overdue" glance, and ZRA-submission status visibility are all currently absent. **Redesign direction — adapting the Billing Command Center + Revenue Dashboard (§3.3/§3.8) directly, including their flat Workspace-Layer treatment since this is precisely the dense-data context that visual language suits:** AR-aging KPI row, the **Revenue River** and **Profit Waterfall** signature widgets (§6) replacing the source's simple paired-bar chart where genuine drill-down is needed, a clear ZRA-submission-status color chip per invoice, and the **Proof-of-Delivery Gallery** (§6) surfaced per-invoice so a billing clerk can visually confirm delivery before chasing payment. **Ambient AI on this screen** (§8): *"Invoice #SHP00042 should be sent today — the customer's payment pattern suggests early submission improves collection speed"* as an AI Recommendation Card.

### 7.14 Driver Workspace
**Answers:** *which drivers need attention?* (§2.4)
**Current state:** driver records live inside `hr.employee` extensions with stock form views; no consolidated driver 360 exists in the backend UI (distinct from the mobile app). **Problems:** a dispatcher wanting a driver's compliance status, recent performance events, and current assignment together must open three modules. **Redesign direction:** a driver 360 card adapting the Attendance-History grouped-expandable-log pattern (§3.9) for trip/performance history, the **Driver Performance Radar** (§6) rather than a single gauge, since a driver's story is genuinely multi-dimensional (safety, on-time %, fuel efficiency, compliance, customer feedback), and compliance status as traffic-light chips (§6) inline. **Ambient AI on this screen** (§8): *"Driver fatigue probability is increasing for this driver based on recent hours-of-service patterns"* — framed constructively (§7.17's scorecard-not-surveillance tone), never punitive by default.

### 7.15 Customer Workspace
**Current state:** stock `res.partner`/`deployfleet.customer` form and list views; no consolidated view of a customer's contracts, active shipments, and billing status together. **Problems:** account management currently requires cross-referencing customer, shipment, and invoice modules separately. **Redesign direction:** adapting the Clients/Sites Mega Menu's tile-navigation concept (§3.1) into a customer 360 workspace — contract terms, active/recent shipments as a mini-board, outstanding balance, all one screen; customer-facing analytics exports use the **Insights** naming (§2.3), not "Reports."

### 7.16 AI Workspace → Copilot Console
**Answers:** *what should I do today?* (§2.4)
**Current state:** does not exist as a distinct surface at all — `deployfleet.ai.action.request` has only a standard list/form view; there is no agent catalog view, no usage/cost dashboard exposed to an operator, no natural-language query surface. **Problems:** this is the largest gap between backend sophistication (a full six-agent catalog, permission layer, and mandatory approval pipeline, per [08-ai-architecture.md](08-ai-architecture.md)) and frontend reality (nothing) anywhere in the product. **Redesign direction:** the **Copilot Rail** (§6) as the ambient, cross-app surface, plus a dedicated **Copilot Console** as its own command-center-class screen: an approval queue (pending action requests, ranked, one-click approve/reject with the reason field the backend already requires, rendered as **AI Recommendation Cards**, §6/§8), an agent catalog view (six agents, each showing recent output, confidence, and its on/off toggle per [CLAUDE.md](../../CLAUDE.md) §4's non-negotiable per-feature switch), and a usage/cost dashboard over `deployfleet.ai.usage` (tokens, cost, cache-hit rate, per company) that currently has no visual home despite being fully logged in the backend. This is the one area of §7 with no DeployGuard ancestor to adapt at all — genuinely new design, and arguably the second-highest-priority build after the Dispatch Board, since it's the only way the AI investment already made becomes visible and usable rather than backend-only. Detailed platform-wide strategy in §8.

**Current state (Phase C / Slice 4 — the Copilot Rail's ambient half is built, per this document's own §11 boundary call):** a persistent, collapsed-by-default docked tab (right edge, violet-accented Command Layer glass) present globally across every workspace, with a live badge count of `deployfleet.ai.action.request` records in `pending_approval` state. Expanding it opens a real approval queue — one card per pending request (which feature proposed it, the action type and target model, the full proposed-values payload) with working **Approve** and **Reject** buttons wired directly to the existing, unmodified `action_approve()`/`action_reject()` pipeline (§4/§8's mandatory suggestion → permission-check → human-approval → execute → audit chain — this UI adds no new execution path, it only calls the same two methods a human would otherwise reach via the standard list/form view). Reject requires a typed reason in this UI (the backend's own `reason` parameter is optional; requiring it here is a deliberate product decision for a better audit trail, not a backend constraint). New keybinding: `Alt+A`, chosen the same way as the Launcher's per-domain shortcuts, since it doesn't collide with anything already claimed (L, D, F, C, B, R, I, H).

**What's deferred to Phase D's Copilot Console, per this section's own boundary call above, not silently dropped:** per-record contextual awareness (the rail shows the same global queue regardless of which record is open — doc 16's original description of "contextually relevant agent output for whatever record is open" is not yet implemented); AI Recommendation Cards rendered inline on other flagship screens (Dispatch Board, Fleet Command Center, Billing); a natural-language question interface; the agent catalog view (six agents, output, confidence, per-feature on/off toggle); and the usage/cost dashboard over `deployfleet.ai.usage`. The approval queue itself — real, working data, not a mockup — is the one piece of the "destination" description above that shipped early, since it was already fully available or in the backend and gave immediate, genuine value as an ambient surface rather than waiting for the full dedicated console screen.

### 7.17 Mobile Experience
**Current state:** three React Native app scaffolds (driver/dispatcher/customer) per [MOBILE_ARCHITECTURE.md](../../MOBILE_ARCHITECTURE.md), with the glassmorphic-not-native-default intent stated but few real screens built against it yet. **Problems:** none of the desktop redesign work above automatically transfers to mobile — a driver's actual moment-to-moment need (today's trip, one-tap navigation handoff, POD capture, breakdown reporting) is a different information architecture from a shrunk desktop screen. **Redesign direction:** driver home = today's assigned trip as a single card, one-tap actions (navigate/inspect/report issue/capture POD), a Driver Scorecard (built on the Truck-Health-Ring/Driver-Performance-Radar lineage, §6) as a secondary, opt-in tab — framed constructively, a scorecard a driver checks themselves, not a surveillance tool, since that distinction is a real adoption factor, not an afterthought; the Roster Board's considered bottom-sheet breakpoint (§3.6) is the concrete pattern precedent for how DeployFleet's own mobile-web-adjacent surfaces (not the native app itself, but any web view surfaced on a phone) should collapse.

### 7.18 Customer Portal
**Current state:** `deployfleet_customer_portal` exists with basic shipment-status visibility; per Phase 4 build notes, functional but minimal. **Problems:** a customer currently sees status text, not the Proof-of-Delivery gallery, not a visual shipment timeline, not documents in one place. **Redesign direction:** shipment status via the Animated Route Timeline (§6) simplified for an external audience, POD Gallery (§6) attached per shipment, documents (invoices, PODs, compliance certificates where relevant) consolidated in one tab rather than scattered, all under the **Insights** naming (§2.3) for any exportable summary.

### 7.19 Driver Portal
**Current state:** no distinct web portal for drivers exists separate from the mobile app and the internal `hr.employee` form — this is currently a gap between "internal record" and "mobile app," with no web-accessible self-service surface. **Problems:** a driver without the mobile app installed (a real onboarding-day scenario) has no way to see their own schedule, documents, or payslips. **Redesign direction:** a lightweight self-service web portal (schedule, documents, payslips, leave requests) mirroring the Customer Portal's shape but scoped to a driver's own data — new territory, low DeployGuard precedent beyond the general portal-module pattern.

### 7.20 Tablet Experience
**Current state:** unaddressed as a distinct form factor anywhere in current design intent. **Problems:** a dispatcher's desk tablet and a warehouse check-in tablet are real, common hardware in trucking operations and neither phone-sized nor desktop-sized layouts serve them well by default. **Redesign direction:** the Dispatch Board and Fleet Command Center (§7.9/§7.10) should both be explicitly designed against a tablet breakpoint, not just "responsive desktop" — larger touch targets on drag-drop targets specifically, since a tablet's touch-drag precision is worse than a mouse's, directly affecting the Roster-Board-derived interaction model's usability.

---

## 8. Ambient AI strategy — AI everywhere, not another module

The most important correction to make relative to a first-pass reading of this document: **AI is not a destination, it's a texture.** The Copilot Console (§7.16) is where a human goes to *work* AI output in bulk (the approval queue, the agent catalog, the cost dashboard) — but the actual AI *value* should surface ambiently, inline, on whatever screen a user is already looking at, exactly the way §7.9–§7.14 illustrate with concrete examples:

- **Dispatch Board**: *"Swap Truck 12 with Truck 17. Save $240."*
- **Maintenance Intelligence**: *"Delay this service by 6 days."*
- **Financial Intelligence**: *"Invoice should be sent today."*
- **Driver Workspace**: *"Driver fatigue probability is increasing."*
- **Live Fleet Map**: *"Heavy rain expected on this route. Reroute?"*

Every one of these renders in the same component — the **AI Recommendation Card** (§6, cataloged in doc 18) — so a user learns the pattern once and recognizes it everywhere: a violet-accented card, the recommendation stated in plain language, a quantified impact where the backend can compute one, and exactly two actions, **Accept** or **Dismiss**, both of which are the same suggestion→approval→execute→audit pipeline [08-ai-architecture.md](08-ai-architecture.md) already mandates — never a third option that skips the human. This is what makes "AI is ambient, not a module" safe rather than reckless: ambient means *visible everywhere*, not *acting everywhere*.

Supporting infrastructure:

- **The violet-content convention (doc 17)** is the visual backbone — every AI touchpoint, everywhere, is visually identifiable as AI before a user reads a word.
- **The Copilot Rail (§6)** is the ambient, always-available surface for asking a question in natural language about whatever record is open; the **Copilot Console (§7.16)** is the destination for working the approval queue and understanding cost/usage in bulk.
- **Cost and permission visibility is a first-class screen, not an admin afterthought** — per [CLAUDE.md](../../CLAUDE.md) §4's non-negotiable per-feature toggles and cost tracking, the Copilot Console's usage dashboard is where a fleet owner actually sees what AI is costing them and switches off what they don't want, in one place.

---

## 9. Accessibility, performance & motion discipline

Full timing/easing specification lives in [19-animation-guidelines.md](19-animation-guidelines.md); the discipline-level rules that constrain that spec:

- **Contrast first.** Every Command-Layer glass surface must be checked against WCAG AA contrast for its text against the blurred background in both light and dark ambient conditions — a translucent card that reads beautifully in a design tool and poorly in truck-stop sunlight has failed its actual user.
- **`backdrop-filter` is expensive on low-end Android devices** common among driver-facing hardware in the target market — Command-Layer blur is acceptable on desktop/tablet dispatcher and manager surfaces; driver-facing mobile screens should default to a solid, high-contrast Workspace-Layer treatment even where the rest of the platform uses glass, per Principle 6 (§2.6).
- **Respect reduced-motion preferences** platform-wide; every animation named in this document and doc 19 needs a static equivalent.
- **Offline tolerance is a UX requirement, not just a backend one** for driver-facing mobile screens — trip data, POD capture, and inspection forms need to work and queue on poor connectivity, a real condition for the target market, not an edge case.

---

## 10. Success metrics & validation method

This document's claims are falsifiable; they should be checked, not assumed correct on aesthetic grounds alone:

- **Clicks-to-complete, per key workflow**, measured before/after: confirm a dispatch assignment (today: open kanban card → open form → read score → click confirm, ~4 steps); log a fuel entry; approve an AI action; find a specific shipment by number. The Command Palette (§6) and Dispatch Board (§7.9) redesigns should each show a measurable drop here.
- **Time-on-task** for the same workflows, not just click count — a design can reduce clicks while increasing time if each step is heavier.
- **Mobile task-completion rate** for the driver app's core loop (accept trip → navigate → POD capture) under realistic connectivity, not just simulator conditions.
- **A qualitative "does this feel like Tesla, Stripe, or Linear — or does it feel like Odoo" check** — literally showing the redesigned Dispatch Board and Fleet Command Center to someone outside the project (ideally a real trucking-company stakeholder, tying back to [CLAUDE.md](../../CLAUDE.md) §10's still-open domain-validation item) before broad rollout, since "premium" is this document's stated goal (§2.1's specific reference set) and it is a subjective judgment that deserves a real outside check, not just internal confidence.

---

## 11. Phased rollout recommendation

Sequenced for impact-per-effort, not enforced as a rigid schedule — a design/frontend planning aid, not a replacement for [05-implementation-roadmap.md](05-implementation-roadmap.md)'s phase gates. Five phases, lettered rather than numbered to keep them visually distinct from the five *implementation* phases already in flight:

**Phase A — Foundation.** [17-design-system.md](17-design-system.md) (tokens, palette, status-color rules, the violet AI convention, dark mode, accessibility baseline), [18-component-library.md](18-component-library.md) (the `deployfleet_ui` module's foundational atoms and composites), and [19-animation-guidelines.md](19-animation-guidelines.md) (the timing/easing system) — none of §7's screens should start construction before these three exist, per §3.0's central lesson about what DeployGuard didn't finish.

**Phase B — Core UI framework.** The `deployfleet_ui` module built out as real, importable OWL components (not yet the flagship screens themselves): shared theme application, the Launcher, Domain Mega Menus, and the Command Palette (§5) — global navigation has to exist before flagship destination screens are worth navigating to.

**Phase C — Flagship experiences.** Fleet Command Center (§7.10), Dispatch Board (§7.9), Mission Control (§5/§7.2), and the Copilot Rail (§6/§8) — the screens a demo lives or dies by, and the ones that establish the signature-widget visual language (Truck Health Ring, AI Recommendation Card) the remaining workspaces will reuse. **All four Phase C slices are now built** — Slice 1 (Mission Control), Slice 2 (Dispatch Board), Slice 3 (Fleet Command Center), and Slice 4 (the Copilot Rail's ambient half) — see §7.2, §7.9, §7.10, and §7.16 for what shipped in each, including Dispatch Board's three deliberate scope corrections (tap-to-assign over drag-drop, the real plain-`UserError` backend contract, and its intentional Workspace-Layer-not-Command-Layer treatment), Fleet Command Center's own scope corrections (the same accordion pattern instead of a not-yet-built slide-in Inspector, and no Truck Health Ring/Profit Waterfall yet), and the Copilot Rail's scope boundary (only the ambient approval-queue half; the destination Copilot Console — agent catalog, cost dashboard, per-record context-awareness — is Phase D by this document's own design, not a gap). Every Phase C slice is built mobile-first per CLAUDE.md's explicit instruction: touch targets checked against a 44px minimum, layouts designed single-column-first with wider breakpoints as the exception, not the default.

**Phase D — Operational workspaces.** Maintenance Intelligence (§7.11), Billing/Financial Intelligence (§7.13), Driver Workspace (§7.14), Customer Workspace (§7.15), Compliance areas, and Workshop UI (§7.12) — applying the now-proven design language rather than inventing it again per screen.

**Phase E — Premium experiences.** Live Fleet Map (§6/§7.7), Animated Route Timeline (§6), Load Builder (§6, gated on the multi-stop model per [12-ltl-freight-management-architecture.md](12-ltl-freight-management-architecture.md)), Fleet Heat Map, Driver Scorecards (§7.17), full analytics/Insights depth, and mobile refinement across all three apps (§7.17–§7.20) — layered in once the desktop/tablet flagship work has validated the patterns mobile and the more speculative signature widgets (Fleet Globe, Fleet Heat Map) will reuse.

The **Copilot Console** (§7.16) sits deliberately at the Phase C/D boundary: its ambient half (the Copilot Rail, AI Recommendation Cards appearing inline on flagship screens) belongs in Phase C alongside the screens it annotates — **the Copilot Rail's ambient half, specifically its live approval queue, is now built** (§7.16); its destination half (the full agent-catalog-and-cost-dashboard console, plus AI Recommendation Cards inline on the other flagship screens) can trail into Phase D without blocking the flagship screens' launch, since ambient AI delivers value before the dedicated console exists to manage it in bulk.

---

## 12. Governance

This document, together with [17-design-system.md](17-design-system.md), [18-component-library.md](18-component-library.md), and [19-animation-guidelines.md](19-animation-guidelines.md), is now the authoritative elaboration of [CLAUDE.md](../../CLAUDE.md) §5's UI/UX standards, the same relationship [08-ai-architecture.md](08-ai-architecture.md) has to §4. Before building any dashboard, board, or workspace named in §7, check it against this four-document set the same way AI work is checked against doc 08 — and if a real implementation constraint contradicts a recommendation here (a performance ceiling, an Odoo Community-edition limitation per the still-open edition question in [06-risks-and-recommendations.md](06-risks-and-recommendations.md)), update the relevant document in the same session, per [CLAUDE.md](../../CLAUDE.md) §8's own rule that architecture docs are living records, not write-once artifacts.
