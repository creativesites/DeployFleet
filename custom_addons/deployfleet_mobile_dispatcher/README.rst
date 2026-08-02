==================================
DeployFleet Mobile Dispatcher API
==================================

REST API backing the dispatcher/fleet-manager mobile app: a live
operations dashboard (active trip/pending shipment/vehicle counts), trip
monitoring, pending-shipment lookup, dispatch-assignment approval, and a
recent-events feed - see docs/architecture/04-module-structure.md's
per-role mobile app table.

Every endpoint is gated by ``deployfleet_security.group_deployfleet_dispatcher``
via ``deployfleet_core``'s shared ``require_group()`` decorator, and every
response uses the same ``{"success": true/false, "data"/"error": ...}``
envelope shared with ``deployfleet_mobile_customer`` - both reuse
``deployfleet_core/controllers/mobile_api.py`` rather than each
reimplementing this auth-relevant plumbing (per
docs/architecture/02-reuse-strategy.md §5).

Session-cookie auth is standard Odoo (``/web/session/authenticate``) -
this module adds no auth mechanism of its own.
