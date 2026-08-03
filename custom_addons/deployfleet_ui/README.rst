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
the Fleet Command Center). Still open: per-record contextual awareness
for the Rail/Console, and AI Recommendation Cards on the remaining
flagship screens (Dispatch Board, Billing) — see doc 16 §11's phased
rollout.

A note on verification
=======================

Every OWL/JS/XML file in this module was written against standard Odoo
17-19 OWL conventions and checked for syntax validity (``node --check`` on
every ``.js`` file, XML well-formedness on every ``.xml`` file) — but,
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
