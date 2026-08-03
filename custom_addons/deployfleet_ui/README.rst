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

Not yet built
=============

See ``docs/architecture/18-component-library.md`` for the full catalog:
Toast, Alert, Search Box, Filters, Tables, Skeleton Loaders, Context Menu,
Progress Ring, Command Panel, Quick Action Bar, AI Recommendation Card, the
layout/navigation shells (Sidebar, Modal, Drawer, Inspector, Bottom Sheet,
Split View, Master Detail, Copilot Rail), and every signature "wow" widget
(Live Fleet Map, Truck Health Ring, Driver Performance Radar, Revenue River,
Profit Waterfall, Fleet Score, Risk Matrix, Maintenance Planner, Fleet
Calendar, Load Builder, Fleet Heat Map, Fleet Globe). These land in
subsequent slices per doc 16 §11's phased rollout.

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
