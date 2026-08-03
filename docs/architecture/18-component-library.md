# 18 — Component Library

**Status:** Specification, not code. This document catalogs the components a future `deployfleet_ui` OWL module should provide — purpose, variants, states, and which DeployFleet models/data sources each one draws from — specified precisely enough that building the actual components is an implementation exercise against a known spec, not a design exercise. Sibling to [16-experience-architecture.md](16-experience-architecture.md) (the why/what/in-what-order this catalog serves) and [17-design-system.md](17-design-system.md) (the tokens every component here must consume by reference, never by literal value, per doc 17 §12).

**The point of this document, stated once:** once `deployfleet_ui` exists as a real module, **every other module imports from it — none of them hand-roll a button, a card, or a badge again.** This is the mechanical fix to the exact failure mode doc 16 §3.0 diagnosed in DeployGuard: a design-system file existed but nothing downstream consumed it, so every dashboard re-implemented the same component with a slightly different two-letter CSS prefix. Naming a component here and having a module reinvent it anyway is the one thing this document exists to prevent.

---

## 1. Organization

Four tiers, ordered by how foundational they are — later tiers are built from earlier ones, never the reverse:

1. **Foundational atoms** (§2) — the smallest reusable units; almost every other component is built from these.
2. **Composite components** (§3) — assembled from atoms, still generic across any module.
3. **Layout & navigation shells** (§4) — the structural chrome (sidebars, modals, drawers, inspectors) every workspace and command-center screen is built inside.
4. **Signature widgets** (§5) — the "wow" data-visualization components specific to DeployFleet's domain, cataloged in [16-experience-architecture.md](16-experience-architecture.md) §6 and detailed here with concrete data sources.

---

## 2. Foundational atoms

| Component | Purpose | Key variants | States required (per doc 17 §12) |
|---|---|---|---|
| **Button** | The one button implementation, platform-wide | Primary (amber accent), secondary, ghost, destructive | default, hover, active, focus, disabled, loading (inline spinner replaces label, doesn't resize the button) |
| **Card** | The base surface for any grouped content | Workspace (flat) / Command (glass) per doc 17 §6 | default, hover-lift (Workspace only), selected |
| **Avatar** | Person/entity representation (driver, dispatcher, customer contact) | Initials fallback, photo, small/medium/large | default, with-status-dot (online/offline, on-duty/off-duty) |
| **Status Badge** | A labeled pill conveying one of doc 17 §2.2's five semantic colors | Solid, outline | default only — badges don't have interactive states, they're informational |
| **Status Pill** | The clickable variant of Status Badge, used in attention strips (doc 16 §3.3) — a count plus a label that jumps to the underlying record set on click | Per status color | default, hover, active |
| **AI Badge** | The compact, inline marker for AI-authored content (doc 17 §2.3/§10) — a small violet badge with a distinct icon, used next to a single field rather than a whole card | — | default; disappears entirely once the suggestion is accepted (this is a behavior contract, not just a visual state) |
| **Toast** | Transient confirmation/error feedback after an action | Success, error, info, warning (doc 17 §2.2 colors) | enter, visible, exit — timing per [19-animation-guidelines.md](19-animation-guidelines.md) |
| **Alert** | Persistent, dismissible inline banner (distinct from Toast's transience) | Same four semantic variants as Toast | default, dismissed |

---

## 3. Composite components

| Component | Purpose | Notes |
|---|---|---|
| **MetricCard** | The standardized KPI card — label+icon header, one large number, a short colored caption, left-border-stripe status color (doc 16 §3.4's chosen variant, replacing DeployGuard's five inconsistent hand-rolled versions) | Every "Intelligence" screen (doc 16 §7.3) is built from a grid of these; the trend-arrow convention (doc 17 §2.2) is a `MetricCard` sub-prop, not a separate component |
| **KPI Grid** | A responsive grid container for a set of `MetricCard`s, collapsing column count per breakpoint | Used on every Command-Layer summary screen |
| **Progress Ring** | The SVG circular gauge (doc 16 §3.10's direct DeployGuard-widget port) — band-colored (green/amber/red) with a centered numeric value and label | Base of the **Truck Health Ring** and **Fleet Score** signature widgets (§5) |
| **Search Box** | A single, consistent search input used in the Launcher, Mega Menus, and Command Palette | Client-side instant-filter for small local datasets (mirroring DeployGuard's Mega Menu behavior), server-backed for large record sets (the Command Palette's record search) |
| **Filters** | A consistent filter-chip/panel component for list and Intelligence screens | Replaces Odoo's default filter UI only where it materially improves scanability; standard Odoo filter chrome is acceptable on genuinely standard CRUD lists (doc 16's own "use judgment" rule, [CLAUDE.md](../../CLAUDE.md) §5) |
| **Tables** | An enhanced list/table component with row-left-border status striping (doc 16 §7.4) and inline row-level contextual actions | Not a replacement for every Odoo list view — used where doc 16 §7.4 specifically calls for richer rows |
| **Skeleton Loaders** | Content-shaped loading placeholders (doc 17 §9) | One skeleton variant per composite/signature component that has one — a `MetricCard` skeleton, a `Table` skeleton, etc., not a single generic gray box |
| **Context Menu** | Right-click secondary-action menu | Direct port of the Roster Board's context-menu mechanic (doc 16 §3.6), generalized for any record card across the product (Dispatch Board, Fleet Command Center inspector rows) |
| **Command Panel** | The generic "type to search/act" input-plus-results-list primitive | Scoped-search use only (e.g., searching within a Mega Menu) — the global Command Palette itself is realized differently, see note below |
| **Quick Action Bar** | The contextual, docked (not modal) action rail that changes its button set based on the currently open record (doc 16 §3.5) | The mechanical implementation of doc 16 §2.5's "no dead ends" principle — every record-detail screen mounts one |
| **AI Recommendation Card** | The single, consistent format every ambient AI suggestion renders in, platform-wide (doc 16 §8) | Violet left-border per doc 17 §2.3; contains: recommendation text, a quantified-impact line where the backend can compute one, and exactly two actions (Accept / Dismiss) wired to the mandatory suggestion→approval→execute→audit pipeline ([08-ai-architecture.md](08-ai-architecture.md)) — never a third action that bypasses human approval |

**Implementation note on the global Command Palette (Phase B / Slice 1):** Odoo's web client already ships its own Ctrl+K command palette (`@web/core/commands/`), with its own overlay, focus trap, and keyboard navigation already built and battle-tested. Building a second, competing overlay bound to the same shortcut would be redundant and risk a hotkey conflict. `deployfleet_ui` instead registers a `command_provider` into Odoo's existing palette (searching shipment/vehicle/driver records and opening the selected record's form view) rather than reimplementing the overlay this table's "Command Panel" entry describes. The Command Panel atom remains the right primitive for future *scoped* search (e.g., inside a Mega Menu), where there's no existing Odoo surface to extend.

---

## 4. Layout & navigation shells

| Component | Purpose | DeployGuard ancestor (doc 16 §3) |
|---|---|---|
| **Sidebar** | The fixed left-hand navigation/filter panel used in Command-Layer screens (Fleet Command Center, Dispatch Board) | Roster Board / Fleet Dashboard's shell (§3.6/§3.7) |
| **Modal** | Centered, focused single-task dialog (quick-create forms, the override-reason dialog) | Fleet Dashboard's quick-create modals (§3.7), Roster Board's override dialog (§3.6) |
| **Drawer** | Full-height slide-in panel from the screen edge (distinct from Modal — used for secondary, longer-form content that doesn't need to fully block the underlying screen) | Roster Board's batches-manager drawer (§3.6) |
| **Inspector** | The row-click slide-in detail panel that re-grids the surrounding layout to make room, rather than navigating away | Fleet Dashboard's inspector panel (§3.7) — the Fleet Command Center's (doc 16 §7.10) direct mechanic |
| **Search Box overlay** | (see Composite Components §3) | — |
| **Bottom Sheet** | Mobile/tablet-narrow-viewport equivalent of a side panel, sliding up from the bottom with a drag handle | Roster Board's considered mobile breakpoint (§3.6) — the concrete precedent for every DeployFleet mobile-web-adjacent collapse (doc 16 §7.17/§7.20) |
| **Split View** | A two-pane layout (list + detail) that collapses to single-pane (Bottom Sheet) below a breakpoint | Generalization of the Fleet Dashboard's table+inspector layout for any master/detail screen |
| **Master Detail** | The specific list-selects-a-record-shows-its-detail pattern, built from Split View + Inspector | Driver Workspace, Customer Workspace (doc 16 §7.14/§7.15) |
| **Floating AI Panel (Copilot Rail)** | The persistent, collapsed-by-default, expand-on-demand docked panel present across every workspace (doc 16 §6/§8) | No DeployGuard ancestor — genuinely new, since DeployGuard's AI engine never had a UI |

---

## 5. Signature widgets — the "wow" set

Full rationale and priority tags in [16-experience-architecture.md](16-experience-architecture.md) §6; this table adds the concrete data source each one draws from, since that's the detail an implementer actually needs.

| Widget | Data source (DeployFleet models) | Visualization approach |
|---|---|---|
| **Live Fleet Map** | `deployfleet.vehicle` (current position, status), `deployfleet.trip` (route, ETA), `deployfleet.depot` (markers) | Real map (pins + breadcrumb trail + route lines) — the one component in this catalog that justifies a mapping-library dependency; evaluate for bundle size and licensing, don't default to the heaviest option |
| **Animated Route Timeline** | `deployfleet.trip`, `deployfleet.dispatch.assignment`, multi-stop shipment data (per [12-ltl-freight-management-architecture.md](12-ltl-freight-management-architecture.md)) | A genuine time-axis rendering — the thing doc 16 §3.9 confirms DeployGuard's "Timeline Views" never actually was |
| **Truck Health Ring** | `deployfleet.vehicle` + `deployfleet.maintenance.schedule` + `deployfleet.vehicle_compliance` document status, rolled into one score | Progress Ring atom (§3), band-colored |
| **Fleet Score** | Aggregate roll-up across all vehicles' Truck Health Rings plus fleet-wide on-time percentage | Progress Ring atom (§3), the Mission Control hero metric |
| **Driver Performance Radar** | `deployfleet.driver.performance` events, on-time delivery history, fuel efficiency, compliance status, customer feedback (where captured) | Multi-axis radar/spider chart — one of the few places doc 18 recommends a real charting-library primitive (doc 16 §3.8) rather than a hand-rolled DIY visual |
| **AI Recommendation Card** | (see Composite Components §3) | — |
| **Revenue River** | `deployfleet.invoice`, `deployfleet.shipment`, payment records — cash moving from shipment → invoice → payment | An animated flow/Sankey-style visualization surfacing where cash is stuck between stages |
| **Profit Waterfall** | `deployfleet.accounting` revenue records minus `deployfleet.fuel`/`deployfleet.maintenance`/`deployfleet.driver_advance`/`deployfleet.payroll` cost records, per vehicle or per route | A waterfall/bridge chart walking from revenue down to net profit |
| **Fleet Heat Map** | `deployfleet.trip`/`deployfleet.route` geographic density over time | Geographic heat-map overlay on the Live Fleet Map's base map layer, not a separate map instance |
| **Risk Matrix** | `deployfleet.dispatch_compliance` override logs, `deployfleet.vehicle_compliance`/driver compliance document expiry, `deployfleet.driver_performance` incidents | Two-axis (likelihood × impact) scatter/quadrant plot |
| **Maintenance Planner** | `deployfleet.maintenance.schedule`, `deployfleet.maintenance.prediction` (Phase 5 output) | Calendar-plus-Gantt hybrid, not a plain due-date list |
| **Fleet Calendar** | Maintenance schedules, leave requests (`deployfleet.leave`), compliance-document expiry dates | The signature, color-coded (doc 17 §2.2) elevation of doc 16 §7.8's plain calendar view |
| **Load Builder** | `deployfleet.shipment` cargo data against `deployfleet.vehicle` capacity fields (weight/volume) | Truck-silhouette capacity-fill visualization; explicitly gated on the multi-stop/consolidated-shipment model maturing per [12-ltl-freight-management-architecture.md](12-ltl-freight-management-architecture.md) — do not build against the current 1:1 assignment model |
| **Proof-of-Delivery Gallery** | Driver mobile app's captured POD photos/signatures, attached to `deployfleet.delivery` | A visual gallery grid, not a form-view attachment list |
| **Fleet Globe** | Same sources as Live Fleet Map, aggregated for multi-region operators | Aspirational — explicitly gated on real multi-region customer demand existing before any build effort, per doc 16 §6's own caution against speculative building |

**On charting-library choice:** doc 16 §3.8 and this document both flag the same handful of components (Driver Performance Radar, Revenue River, Profit Waterfall) as the honest exception to "no charting library, DIY div/SVG is fine" — these need genuine multi-series comparison and drill-down a hand-rolled div chart can't cleanly express. The concrete recommendation is a **single small, actively maintained charting primitive**, evaluated for bundle size and license compatibility at implementation time — not five different libraries for five different chart types, and not a heavyweight full-featured charting suite for what is, in the end, a handful of chart types used consistently.

---

## 6. Component contract checklist

Every component in this catalog, before it's considered complete:

- [ ] Consumes doc 17 tokens by reference only — zero literal hex/px/duration values in its implementation.
- [ ] Implements every state doc 17 §12 requires for its category (interactive atoms need all seven; purely informational atoms like Status Badge need only "default").
- [ ] Has a documented empty state, not just a documented populated state.
- [ ] Has a Skeleton Loader variant if it's ever populated asynchronously.
- [ ] Respects reduced-motion preferences for any animation it uses ([19-animation-guidelines.md](19-animation-guidelines.md)).
- [ ] Is keyboard-navigable if it's interactive (doc 17 §11).
- [ ] Ships once, in `deployfleet_ui`, and is imported everywhere it's needed — never copy-pasted into a consuming module's own `static/src/`.

---

## 7. Governance

No module ships a hand-rolled version of anything cataloged here. If a screen genuinely needs a visual element not yet in this catalog, the correct action is to add it here first (extending `deployfleet_ui`), not to write module-scoped CSS/JS — the exact discipline failure [16-experience-architecture.md](16-experience-architecture.md) §3.0 diagnosed in DeployGuard's own history. Update this document in the same session a new shared component is added, per [CLAUDE.md](../../CLAUDE.md) §8.
