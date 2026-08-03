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

Not yet built
=============

See ``docs/architecture/18-component-library.md`` for the full catalog:
Toast, Alert, Search Box, Filters, Tables, Skeleton Loaders, Context Menu,
Progress Ring, Quick Action Bar, AI Recommendation Card, the layout/
navigation shells (Sidebar, Modal, Drawer, Inspector, Bottom Sheet, Split
View, Master Detail, Copilot Rail), the Domain Mega Menus and DeployFleet
Launcher (Phase B, Slices 2-3), and every signature "wow" widget (Live Fleet
Map, Truck Health Ring, Driver Performance Radar, Revenue River, Profit
Waterfall, Fleet Score, Risk Matrix, Maintenance Planner, Fleet Calendar,
Load Builder, Fleet Heat Map, Fleet Globe). These land in subsequent slices
per doc 16 §11's phased rollout.

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
