===============
DeployFleet UI
===============

Shared OWL component library and design-system token set for DeployFleet's
frontend, per ``docs/architecture/16-experience-architecture.md``,
``17-design-system.md``, ``18-component-library.md``, and
``19-animation-guidelines.md``.

**No business module should hand-roll a button, card, badge, or modal —
import from here instead.** This is Phase A / Slice 1 of the Experience
Architecture rollout: the design-system tokens (colors, spacing, typography,
elevation, glass, motion) and a first tranche of foundational atoms plus one
composite, not the full doc 18 catalog yet.

Implemented so far
===================

- **Design tokens**: ``static/src/scss/tokens.scss`` (color incl. the
  AI-content violet convention and dark mode via
  ``prefers-color-scheme``/``data-theme``), ``static/src/scss/animations.scss``
  (timing/easing/keyframes per doc 19).
- **Atoms**: Button, Card (Workspace/Command layer variants), Avatar,
  StatusBadge, StatusPill, AiBadge.
- **Composites**: MetricCard.
- A **UI Component Showcase** client action (visible only to
  ``base.group_no_one`` — debug-mode users, not part of the real product
  navigation) that renders one of each component with its documented
  variants, as a living reference and the practical way to visually QA an
  OWL component library given this repository's CI has no headless-browser
  test step.
- **Command Palette record search** (Phase B / Slice 1): extends Odoo's own
  built-in Ctrl+K command palette — rather than building a second, competing
  overlay on the same shortcut — with DeployFleet record search. Typing 2+
  characters searches shipment reference numbers, vehicle license
  plates/names, and driver names; selecting a result opens that record's
  form view directly. See ``docs/architecture/18-component-library.md``'s
  "Implementation note on the global Command Palette" for why this extends
  Odoo's palette instead of reimplementing one.
- **Domain Mega Menus** (Phase B / Slice 2): one real shared ``MegaMenu``
  OWL component (``static/src/mega_menu/mega_menu.js``) — full-screen
  Command-Layer glass, client-side instant search, a responsive tile grid —
  parameterized by six curated domain content sets (``domain_content.js``):
  Fleet & Vehicles, Dispatch & Trips, Compliance, Billing & Finance, Driver
  & HR, and AI & Intelligence. All six domains share one
  ``ir.actions.client`` tag distinguished only by a ``params.domain`` key,
  fixing the exact fragility found in DeployGuard's own five copy-pasted
  mega-menu files (doc 16 §3.1). Content is a deliberate curation of each
  domain's ~4-8 main workflow screens, grounded in the actual 65-menu-item
  inventory across all 43 backend modules — not every menu item is
  promoted to a tile; admin/config-only screens stay reachable through the
  standard menu. Reachable today as six new top-level menu entries (placed
  ahead of the existing granular items, nothing removed or reparented);
  becomes overlay-triggered from the DeployFleet Launcher once Slice 3
  builds it.
- **DeployFleet Launcher** (Phase B / Slice 3): a full-screen Command-Layer
  overlay (``static/src/launcher/launcher.js``) — priority-workspace strip
  with ``Alt+<letter>`` shortcuts to each of the six Mega Menu domains, a
  destination grid, localStorage-backed recents and favorites, and a
  persistent corner trigger button, opened globally with ``Alt+L`` or the
  corner button, closed with ``Esc`` or a click outside. **Deliberately not
  a ``web.NavBar`` patch** — doc 16 §3.2 explains why: a bad xpath match
  against this exact Odoo 19 nightly's NavBar template could break the top
  navigation bar across the *entire product*, not just this feature, and
  that template's current structure can't be verified against a live
  instance from this development environment. Every other part of the
  spec (glass, priority strip, keyboard shortcuts, destination grid,
  recents/favorites) ships anyway via a self-contained, always-mounted
  overlay instead. The destination grid is populated from the six curated
  Mega Menu domains rather than Odoo's own ``getApps()`` — DeployFleet
  nests all 43 modules under one single app menu rather than many
  distinct top-level apps, so a literal Odoo-app grid would be nearly
  empty; Odoo's own real top-level apps (Settings, Discuss, ...) render
  separately below as "Other Apps."
- **Mission Control** (Phase C / Slice 1): the owner/manager Home Dashboard
  (``static/src/mission_control/mission_control.js``), reachable at menu
  sequence 0 (ahead of the six Mega Menu domains) and via the Launcher's
  ``Alt+H`` shortcut, which was deliberately left unassigned in Slice 3
  for exactly this. A silent-unless-nonzero attention strip built from
  five genuine parallel ``searchCount`` queries against field-verified
  models (unassigned shipments, expired/expiring-soon compliance
  documents, vehicles in breakdown, pending AI approvals — the last
  using the ``ai`` StatusPill variant, since that pill is literally about
  AI-suggested actions awaiting review), three real KPI cards (Active
  Vehicles, Active Shipments, Confirmed Revenue), and quick links to all
  six domains. **Every count is a genuine ORM query, not a placeholder
  number** — field names (``deployfleet.shipment.state``,
  ``deployfleet.compliance.document.state``, ``deployfleet.vehicle.
  status``, ``deployfleet.ai.action.request.state``) were read directly
  from each model's source before writing these domains, not guessed.
  This slice also retroactively bumped the shared Button and StatusPill
  atoms' touch targets to 44px (previously 36px and ~20px respectively)
  per CLAUDE.md's explicit mobile-first instruction — both are reused
  everywhere, so this is the highest-leverage place to fix it. Phase B's
  Launcher/Mega Menu screens were not audited for touch-target sizing in
  this same pass; that remains a worthwhile follow-up.
- **Dispatch Board** (Phase C / Slice 2): the dispatcher's primary
  workspace (``static/src/dispatch_board/dispatch_board.js``) — confirmed
  shipments awaiting a driver/vehicle assignment, tap-to-expand for a
  ranked candidate list sourced from the existing
  ``action_suggest_assignments()`` scoring engine, and one-tap Confirm.
  **Three deliberate scope corrections**, all documented in doc 16 §7.9:
  (1) **tap-to-assign, not drag-and-drop** — HTML5 drag-drop has poor
  touch support and CLAUDE.md's mobile-first mandate applies to every
  Phase C screen without exception; (2) the real backend contract is a
  plain ``UserError`` from ``deployfleet.dispatch.assignment.
  action_confirm()`` (in both ``deployfleet_dispatch`` and
  ``deployfleet_dispatch_compliance``), not the structured three-way
  ``{success, hard_block, override_required}`` response doc 16 originally
  described from DeployGuard's Roster Board — the shipped override dialog
  catches the error, shows its message, and writes one operator-supplied
  reason to both ``override_reason`` and ``compliance_override_reason``
  before retrying, rather than the frontend trying to parse which check
  fired; (3) **Workspace Layer, not Command Layer** — the one deliberate
  exception among every screen shipped so far, since doc 16 Principle 1
  requires sustained-work screens to stay flat and high-contrast rather
  than fight a translucent card for contrast across an 8-hour shift. An
  urgency indicator (left-border color stripe, plus a pulsing animation
  on overdue shipments reusing the existing ``df-pulse-ambient`` keyframe)
  flags shipments approaching or past their pickup window. Not yet built:
  the persistent candidate side-panel, bulk auto-assign, right-click
  context actions, and the ambient AI Recommendation Card doc 16 describes
  alongside the rule-based suggestions (gated on the Copilot Rail/Console
  work).
- **Fleet Command Center** (Phase C / Slice 3): the fleet manager's
  consolidated vehicle view (``static/src/fleet_command_center/
  fleet_command_center.js``) — a status-filterable vehicle list (chips
  with live counts: All/Available/Assigned/Maintenance/Breakdown), each
  card expanding on tap into a genuine consolidated read across four
  models: current trip, compliance documents (color-coded valid/
  expiring/expired), maintenance schedules (due vs. on-schedule), and the
  last 5 fuel logs (anomalies flagged) — plus working one-tap status
  actions (Mark Available / Send to Maintenance / Report Breakdown)
  wired to the vehicle's real ``action_set_*`` methods. Same transparency
  discipline as the Dispatch Board: this reuses the same tap-to-expand
  accordion pattern rather than doc 16's originally-described sidebar +
  tabbed table + slide-in Inspector, since no Drawer/Inspector component
  exists yet; no Truck Health Ring or Profit Waterfall yet either (both
  still "Aspirational" in doc 18 — no Fleet Score/per-vehicle revenue
  computation exists yet to back them). Workspace Layer, same reasoning
  as the Dispatch Board (sustained-work screen, not a launch screen).
- **Copilot Rail** (Phase C / Slice 4 — the ambient half only, by design):
  a persistent, collapsed-by-default docked tab on the right edge
  (``static/src/copilot_rail/copilot_rail.js``), violet-accented Command
  Layer glass, present globally across every workspace via
  ``main_components`` (like the Launcher), toggled with ``Alt+A`` or the
  tab itself. Shows a live badge count of pending
  ``deployfleet.ai.action.request`` records; expanding it opens a real
  approval queue with working Approve/Reject buttons wired directly to
  the existing, unmodified ``action_approve()``/``action_reject()``
  pipeline — this UI adds no new execution path, it only calls the same
  methods a human could otherwise reach via the standard list/form view.
  Reject requires a typed reason in this UI (a deliberate product
  decision for a better audit trail — the backend's own ``reason``
  parameter is optional). Doc 16 §11 places the Copilot Console
  deliberately at the Phase C/D boundary: the *ambient* half (this rail)
  is Phase C; the *destination* half — a dedicated Copilot Console
  screen with an agent catalog, a usage/cost dashboard over
  ``deployfleet.ai.usage``, per-record contextual awareness, a
  natural-language query interface, and AI Recommendation Cards inline
  on other flagship screens — is explicitly Phase D, not a gap in this
  slice.

**Command Layer retrofitted from dark glass to light glass** (mid-Phase-D
design-system revision, applied retroactively): the Launcher, Mega Menus,
Mission Control, and the Copilot Rail all originally shipped with a dark
translucent gradient panel (light text on near-black glass). An explicit
product decision — "only light backgrounds, as much as possible" —
retrofitted all four, plus the shared ``Card`` atom's ``command`` variant,
to a light, near-white translucent panel (``--df-glass-panel-bg``) with
dark text, keeping the rest of the glass recipe (scrim, blur, saturation
boost, hairline border) unchanged. Two new theme-aware tokens now live in
``tokens.scss``: ``--df-glass-panel-bg`` and a lightened ``--df-glass-
border``, both flipping back to their original dark-panel values under
``prefers-color-scheme: dark``/``data-theme="dark"``, the same way the
rest of the neutral scale already does. Also fixed in the same pass: a
latent bug where ``--df-color-neutral-600`` was already referenced
throughout the Dispatch Board and Fleet Command Center's SCSS but was
never actually defined in ``tokens.scss`` — added to the neutral scale.
See doc 16 Principle 1 / doc 17 §6's changelog notes for the full
rationale.

**Launcher/Copilot Rail glassmorphism and mobile polish pass** (following
user feedback that the light retrofit above needed to look genuinely
"glassy," not just like a light modal, and be more mobile-friendly): the
Launcher and Copilot Rail are the only two true overlay surfaces in this
module (scrim + panel on top of other page content, as opposed to
Mission Control/Mega Menus/Copilot Console, which are full-page screens
with nothing behind them to blur). Both previously applied
``backdrop-filter`` only to the full-screen scrim, never to the panel
itself, so the panel read as a mostly-opaque light card rather than
frosted glass. Fixed by giving both panels their own
``backdrop-filter`` (plus the ``-webkit-backdrop-filter`` prefix Safari/
iOS still requires — without it, blur silently does nothing on a large
share of the mobile-first target market), an inset top/edge highlight
for the light-catching-glass look, and lowering ``--df-glass-panel-bg``
from 0.92 to 0.82 opacity (0.85 → 0.78 in dark mode) so the blur
actually reads through instead of being nearly opaque. Also fixed a
real mobile *functional* bug, not just a visual one: the Launcher's
per-tile favorite-star button was hidden behind ``:hover``, with no
fallback — on a touchscreen there is no hover state, so the button was
permanently unreachable on the phones/tablets this product is built
mobile-first for. Now scoped to ``@media (hover: hover)`` so the
hover-to-reveal behavior only applies on genuinely hover-capable
pointers, and the star is always visible by default on touch. Other
mobile fixes in the same pass: the search input, close button, chips,
and priority-strip pills were all bumped to the established 44px touch
target minimum (previously as small as 26–36px); the header forces the
search box onto its own full-width row below 640px instead of an
arbitrary flex-wrap point; the destination grid drops to a single
column below 400px, since two 160px-minimum columns don't comfortably
fit a narrow phone; and the overlay's padding tightens on mobile with a
``env(safe-area-inset-bottom)`` allowance for notched devices.

- **Copilot Console** (Phase D / Slice 1): the destination screen for
  working the AI investment in bulk
  (``static/src/copilot_console/copilot_console.js``), complementing the
  Copilot Rail's ambient approval queue. An **Agent Catalog** (all six
  ``deployfleet.ai.agent`` personas, each showing description, related
  models, model tier, and data category, plus a real, working
  Enable/Disable toggle wired to the underlying ``deployfleet.ai.
  feature.enabled`` field) and a **Usage & Cost Dashboard** over
  ``deployfleet.ai.usage`` (this month's cost/tokens via the model's own
  ``total_cost_this_month()``, an all-time cache-hit rate, a per-feature
  cost/token breakdown via ``read_group``, and a recent-calls log) — real
  ORM queries and a real field write, not mockup data. **The
  natural-language query interface is also built**, scoped per-agent
  rather than one generic global query box: each agent card has a real
  "Ask" box that calls ``deployfleet.ai.core.complete(feature.key, agent.
  system_prompt_template, question)`` — the same mandatory-pipeline entry
  point (policy/permission/budget checks, response cache, provider call,
  usage logging) every other AI feature goes through, not a shortcut
  around it. Command Layer, light glass per the retrofit above, since doc
  16 §7.16 calls this a command-center-class destination screen, the same
  category as Mission Control. **Deferred, same transparency discipline
  as every prior slice:** per-agent "recent output"/"confidence" in the
  catalog itself (the four Phase 5 prediction models each use a different
  schema for their own risk/confidence metric — unifying that into one
  generic display needs per-agent custom rendering logic, not a generic
  read) and per-record contextual awareness (neither the Rail nor the
  Console yet knows which record the user has open elsewhere in the app —
  deliberately not attempted against an unverified internal action-manager
  API, the same risk-aversion reasoning that kept the Launcher off a
  ``web.NavBar`` patch).
- **AI Recommendation Card** (Phase D / Slice 1, new atom): the full
  ambient-AI suggestion surface (``DeployfleetAiRecommendationCard``),
  distinct from the existing inline ``AiBadge`` marker. First real
  consumer wired into the Fleet Command Center's expanded vehicle detail,
  surfacing ``deployfleet.maintenance.prediction``'s risk score/level/
  basis — silent when ``risk_level`` is "low," the same
  silent-unless-actionable discipline as Mission Control's attention
  strip. One deliberate deviation from doc 18's "exactly two actions
  (Accept / Dismiss)" description: this component ships ``actionLabel``/
  ``onAction`` (an open-ended caller-supplied action) plus ``onDismiss``,
  not a hardcoded Accept/Dismiss pair, since a maintenance risk score has
  no single concrete "accept" write the way a Dispatch Board suggestion
  does — see doc 18's own implementation note for the full reasoning.
  Not yet wired into the Dispatch Board or Billing — Fleet Command Center
  is the first consumer, not the last.
- **Driver Scorecards** (Phase E / Slice 1): a score-filterable driver
  review list (``static/src/driver_scorecards/driver_scorecards.js`` —
  chips: All/Good 80+/Watch 50-79/At Risk <50, live counts), ordered
  worst-score-first. Tapping a driver reuses the same accordion pattern
  as the Dispatch Board and Fleet Command Center to show their real
  recent ``deployfleet.driver.performance.event`` history alongside
  ``deployfleet_driver_performance``'s genuine computed
  ``hr.employee.deployfleet_reliability_score``, years of experience,
  accident count, and license-expiry status — all real fields, not
  placeholders. Workspace Layer, same reasoning as the Dispatch Board and
  Fleet Command Center (sustained review work, not a launch screen).
  Chosen as the first Phase E deliverable after checking which of doc 16
  §11's Phase E items are actually backed by real data today: Live Fleet
  Map/Fleet Heat Map need a GPS/position feed that doesn't exist anywhere
  in ``deployfleet.vehicle``/``deployfleet.trip``; Load Builder is
  explicitly gated on a multi-stop shipment model that hasn't matured yet;
  "mobile refinement across all three apps" belongs to the separate React
  Native codebase in the root ``MOBILE_ARCHITECTURE.md``, not this module.
  Driver Scorecards is the one item with a complete backend already
  built. **Deliberately not the full driver-360** doc 16 §7.14 describes:
  no consolidated trip/current-assignment view, no compliance
  traffic-light chips beyond the license-expiry badge, and no Driver
  Performance Radar multi-axis chart (that needs a real charting-library
  evaluation, one of the few places doc 18 itself calls for a real
  charting primitive over a hand-rolled visual).
- **Workshop Board** (Phase E, Fleet & Vehicles custom-views work): a
  filter-chip-plus-tap-to-expand review workspace for
  ``deployfleet.workshop.job.card``/``deployfleet.workshop.job.line``
  (``static/src/workshop_board/workshop_board.js`` — chips: All Active/
  Open/Diagnosis/Repair/Approval/Closed, defaulting to Active). Expanding
  a card shows its real job lines (labor/part, description, subtotal)
  and a one-tap state-advance button wired to the card's actual next
  action method for its current state (``action_start_diagnosis`` →
  ``action_start_repair`` → ``action_submit_for_approval`` →
  ``action_close``). Replaces the Fleet & Vehicles Mega Menu's "Workshop"
  tile, which previously opened the stock job-card list view. **Not a
  literal drag-drop kanban** — the same mobile-first reasoning as the
  Dispatch Board (§7.9): HTML5 drag-drop has poor touch support. Workspace
  Layer. See ``docs/architecture/16-experience-architecture.md`` §7.12
  for the full scope-correction reasoning versus the original kanban
  description.
- **Fleet Command Center deepened into a "Vehicle 360"** (Fleet &
  Vehicles custom-views work, second deliverable after the Workshop
  Board): three new sections joined the existing Trip/Compliance/
  Maintenance/Fuel detail per the agreed screen-structure decision
  (Tyres/Insurance/Parts-and-Workshop-summary fold into this screen
  rather than each getting its own). **Tyres** — every non-scrapped
  ``deployfleet.tyre`` (position, tread depth, fitted/retreaded state).
  **Insurance** — the vehicle's latest ``deployfleet.insurance.policy``
  plus an open-claims count from ``deployfleet.insurance.claim``.
  **Workshop** — open (non-closed) ``deployfleet.workshop.job.card``
  records with running cost. Parts stays out of this screen entirely —
  confirmed by source read that it has no ``vehicle_id`` — and remains a
  separate registry screen, per the same agreed decision. Also
  **reconciles the two independent fuel-anomaly signals into one
  indicator**: ``deployfleet.fuel.log.is_anomaly`` (flat 30%-above-
  trailing-average threshold, always present) and the separate, stricter
  ``deployfleet.fuel.anomaly`` z-score model (Phase 5's AI layer, needs
  3+ prior logs, z >= 2.0) previously showed as two disconnected sources
  — a fuel-log row now flags anomalous if either signal fires, showing
  the z-score when the AI model has scored that log
  (``Anomaly (z=2.4)``) or a plain ``Anomaly`` badge otherwise. See
  ``docs/architecture/16-experience-architecture.md`` §7.10 for the full
  writeup.
- **Parts Registry and Asset Registry** (Fleet & Vehicles custom-views
  work, third and fourth deliverables): ``deployfleet.part`` and
  ``deployfleet.asset`` both have zero ``vehicle_id`` (confirmed by
  source read), so per the agreed decision both stay dedicated screens
  rather than folding into the Fleet Command Center — but styled as a
  dense **registry ledger** (header row, table rows, right-aligned
  tabular-nums figures) rather than the floating-card/accordion pattern
  every other Fleet & Vehicles screen uses, a deliberate second visual
  dialect within Workspace Layer for "a ledger to scan" vs. "a queue to
  work." **Parts Registry**
  (``static/src/parts_registry/parts_registry.js``): every part with
  quantity on hand/reorder level/unit cost, filterable to Low Stock (a
  live count chip); a "Low Stock" badge only when ``is_low_stock`` is
  true. Tapping a row reveals a real "Receive Stock" quick-action wired
  to ``action_receive_stock()`` — the one genuine manual workflow this
  screen adds, since stock consumption already happens as a side effect
  of Workshop/Tyres closing out their own records. **Asset Registry**
  (``static/src/asset_registry/asset_registry.js``): every asset
  filterable by status (All/In Service/In Storage/Under Repair/Retired,
  live counts); tapping a row reveals its acquisition date plus one-tap
  status-transition actions wired to the asset's real ``action_set_*``
  methods. Both replace their Fleet & Vehicles Mega Menu tile's previous
  target (the stock list view). See
  ``docs/architecture/16-experience-architecture.md`` §7.12a for the
  full writeup.

Not yet built
=============

See ``docs/architecture/18-component-library.md`` for the full catalog:
Toast, Alert, Search Box, Filters, Tables, Skeleton Loaders, Context Menu,
Progress Ring, Quick Action Bar, the layout/navigation shells (Sidebar,
Modal, Drawer, Inspector, Bottom Sheet, Split View, Master Detail), and
every signature "wow" widget (Live Fleet Map, Truck Health Ring, Driver
Performance Radar, Revenue River, Profit Waterfall, Fleet Score, Risk
Matrix, Maintenance Planner, Fleet Calendar, Load Builder, Fleet Heat Map,
Fleet Globe). Phase B (Foundation navigation) and Phase C (flagship
screens) are both complete; **the Phase D Copilot Console is also built**
(agent catalog, usage/cost dashboard, natural-language query interface,
and the AI Recommendation Card atom with its first consumer wired into
the Fleet Command Center). Still open from Phase D: per-record
contextual awareness for the Rail/Console, and AI Recommendation Cards
on the remaining flagship screens (Dispatch Board, Billing). **Phase E
is now underway**: Driver Scorecards (Slice 1) is built; Live Fleet Map,
Fleet Heat Map, Load Builder, and Animated Route Timeline all remain
genuinely blocked on backend capabilities that don't exist yet (a GPS/
position feed, a matured multi-stop shipment model) rather than simply
unbuilt — see doc 16 §11's phased rollout and CLAUDE.md's Phase E status
note for the full reasoning on what's buildable now versus blocked.
Alongside Phase E, a Fleet & Vehicles custom-views initiative is also
underway at explicit user direction ("we want to use custom views as
much as possible") — the Workshop Board above is its first deliverable;
next up is deepening the Fleet Command Center into a fuller "Vehicle
360" (folding in Tyres, Insurance, and a Parts/Workshop summary) and
distinct registry-style screens for Parts and Assets.

A note on verification
=======================

Every OWL/JS/XML file in this module was written against standard Odoo
17-19 OWL conventions and checked for syntax validity (``node --check`` on
every ``.js`` file, XML well-formedness on every ``.xml`` file, and every
``.scss`` file compiled — both individually and as the full concatenated
``web.assets_backend`` bundle in manifest order, which is what actually
catches cross-file/bundle-level failures — via ``libsass``
(``pip install libsass``; ``python3 -c "import sass; sass.compile(...)"``))
— but,
unlike this project's Python modules, **none of it has been verified by
actually rendering it in a running Odoo web client**, since this
development environment has no browser or live Odoo instance to load one
in. The Component Showcase screen above exists specifically so a human can
do that check on the first real install, the same way every other module
this session was validated by installing on the live demo server and
reading the resulting log. Report back anything the showcase screen
doesn't render or style correctly — that is expected of a first frontend
slice, not a sign anything was done carelessly.

That check already caught one real bug: the showcase screen didn't scroll
on mobile. Odoo's mobile action-manager layout gives a client action a
fixed-height slot and expects the action's own root element to provide its
own scroll, rather than the page/body scrolling — the original
``.df-showcase`` container had no explicit ``height``/``overflow``, which
worked on desktop (where there's usually enough viewport height that no
scrolling is needed at all) and silently clipped content on mobile's
shorter viewport instead. Fixed with an explicit ``height: 100%; overflow-y:
auto`` on the container — every future client-action-rooted screen
(Launcher, Mega Menus, flagship command centers) needs this same treatment,
not just this one.

A second real bug, caught the same way (click-testing on a real device, not
by the syntax-only checks above): Mission Control, the Dispatch Board, and
the Fleet Command Center all crashed immediately on open with
``OwlError: Invalid props ... unknown key 'action', unknown key 'actionId',
unknown key 'updateActionState', unknown key 'className'``. All three
declared ``static props = {};``, which tells OWL "this component accepts
zero props" and enables strict validation — but Odoo's action manager
always injects standard props (``action``, ``actionId``,
``updateActionState``, ``className``, ...) into any ``ir.actions.client``
root component it mounts, regardless of what that component declares. The
Component Showcase and the Domain Mega Menu action never hit this because
neither declares ``static props`` at all — omitting it skips prop
validation entirely, rather than declaring an empty schema that rejects
everything. Fixed by removing the ``static props = {};`` line from all
three files. The Launcher and Copilot Rail keep their own ``static props =
{};`` unchanged and correctly, since both are ``main_components`` mounted
with the literal ``{}`` props their registry entry specifies, not the
action manager's injected props — this bug is specific to
``ir.actions.client`` root components. Neither ``node --check`` nor XML
well-formedness would ever catch this class of bug, since the code is
syntactically valid OWL; only rendering it against Odoo's real action
manager surfaces it. Any future ``ir.actions.client`` component in this
module should either omit ``static props`` entirely or declare it with the
actual injected keys marked optional — never an empty object.

A third real bug, this one a database-wide failure rather than a single
screen: the user reported ``Style error. The style compilation failed``
blocking every screen, not just the one they were looking at (Odoo compiles
``web.assets_backend``'s SCSS as one bundle, so a syntax error in any one
file breaks every screen sharing that bundle). Root cause: ``launcher.scss``
used ``max(var(--df-space-1), env(safe-area-inset-bottom))`` for mobile
safe-area padding — but (lib)sass ships its own built-in ``max()`` math
function under the same name as the CSS one, shadowing it and trying to
evaluate ``var(--df-space-1)`` as a literal Sass number, which fails with
``"var(--df-space-1)" is not a number for 'max'`` and takes the whole
bundle down with it. This is exactly the class of bug the brace-balance
check this module previously relied on (``grep -o '{' | wc -l`` vs.
``grep -o '}' | wc -l``) cannot catch — the braces were perfectly balanced;
the file just wasn't valid Sass. Fixed by switching to
``calc(var(--df-space-1) + env(safe-area-inset-bottom, 0px))`` — ``calc()``
has no such name collision (already used safely elsewhere in this module,
e.g. ``metric_card.scss``) and additive stacking is the more common
safe-area-inset pattern anyway. Caught only once a real ``libsass``
compile was run against every file, individually and as the full
concatenated bundle — the verification step this section's opening
paragraph now documents as standard for every future SCSS change in this
module, not just brace-balance checking.

A fourth real bug, reported by the user via screenshot: the Copilot
Console crashed on open with ``OwlError: ... "this.orm.readGroup is not a
function"``. Another instance of this exact Odoo 19 nightly's version
drift (the same class as the ``res.groups.category_id``/``res.users.
groups_id`` renames documented in CLAUDE.md) — the JS ORM service's
convenience wrapper for ``read_group`` isn't exposed under that name on
this build. Rather than guess the current correct name, fixed by removing
the dependency on it entirely: the per-feature cost/token breakdown in
``copilot_console.js`` now fetches up to 2000 ``deployfleet.ai.usage``
records via ``searchRead`` (already confirmed working elsewhere in this
module) and aggregates them client-side with a plain JS reduce, producing
the exact same ``{feature, __count, estimated_cost_usd, tokens_in,
tokens_out}`` row shape the template already expected — no XML changes
needed. Worth carrying forward: prefer ``searchRead``/``search``/``read``/
``write``/``call`` (all confirmed working against this live server) over
less-common ORM service convenience methods whose exact name or
availability hasn't been verified against a live instance.

A fifth real bug, reported by the user via screenshots: Driver
Scorecards crashed on open with ``ValueError: Cannot convert
hr.employee.deployfleet_reliability_score to SQL because it is not
stored``. Root cause was in this module's own code, not version drift:
``driver_scorecards.js``'s ``loadDrivers()`` called ``searchRead`` with
``order: "deployfleet_reliability_score asc"``, but that field is a
plain computed ``Float`` (``compute="_compute_deployfleet_reliability_
score"``, no ``store=True``) on ``hr_employee.py`` — this Odoo build
refuses to build a SQL ``ORDER BY`` against an unstored computed field.
Fixed entirely client-side, no backend change: dropped the ``order``
param from the ``searchRead`` call and sort the returned array
worst-score-first with a plain JS ``.sort()`` after mapping in each
driver's score band — identical resulting order, no backend model
change needed for what is purely a frontend display concern. Worth
carrying forward: an ``order`` param in any ``searchRead`` call in this
module must name a stored field (plain or ``store=True`` computed) —
grepped every other ``order:`` usage in this module after this fix and
confirmed no other screen has the same class of bug.
