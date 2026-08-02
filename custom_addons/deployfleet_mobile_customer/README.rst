================================
DeployFleet Mobile Customer API
================================

REST API backing the customer mobile app: shipment tracking (list and
detail, including proof-of-delivery presence flags), and invoices - see
docs/architecture/04-module-structure.md's per-role mobile app table.

Row-level access is enforced entirely by the ``ir.rule`` records already
declared in ``deployfleet_customer_portal`` (a customer only ever sees
records for their own commercial partner) - every query in this
controller runs as the logged-in user, never ``sudo()``, specifically so
that restriction always applies. This module adds no security rules of
its own; it depends on ``deployfleet_customer_portal`` for them.

Uses ``deployfleet_core``'s shared ``require_authenticated()`` decorator
(any logged-in user, not gated by a ``deployfleet_security`` group the
way the dispatcher API is - customer portal users hold none) and the same
``{"success", "data"/"error"}`` response envelope as
``deployfleet_mobile_dispatcher``.
