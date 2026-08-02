===================
DeployFleet Leave
===================

Leave types (``deployfleet.leave.type``), balances
(``deployfleet.leave.balance``), and requests
(``deployfleet.leave.request``, draft -> submitted -> approved/rejected/
cancelled) per ``docs/architecture/04-module-structure.md``.

Depends on ``deployfleet_trip`` (not just core HR) because
``action_approve()`` checks for scheduled trips during the requested
period and blocks approval if any exist — this is the reason leave
isn't a pure HR-only feature here.

``used_days``/``remaining_days`` on the balance model are deliberately
non-stored computed fields: they're derived from
``deployfleet.leave.request`` records matched only by
employee/type/year (no direct FK), so Odoo's automatic
``@api.depends`` tracking can't fire when a request's state changes.
Computing fresh on every read is simpler and correct.
