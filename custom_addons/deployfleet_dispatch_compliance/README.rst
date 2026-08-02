====================================
DeployFleet Dispatch Compliance
====================================

Blocks dispatch against expired driver/vehicle compliance documents and
driver rest-hour / consecutive-driving-day limits — per
``docs/architecture/06-risks-and-recommendations.md`` risk #3, core
scope here given the safety/regulatory stakes of trucking, not a
deferred nice-to-have.

Two layers, per that risk's own framing:

- ``deployfleet.shipment._score_candidate()`` is extended to hard-disqualify
  a vehicle/driver pair with an expired compliance document or a rest-hour/
  consecutive-driving-day violation — this keeps non-compliant candidates
  out of ``action_suggest_assignments()`` entirely.
- ``deployfleet.dispatch.assignment.action_confirm()`` still allows an
  emergency override (``compliance_override_reason``) for the rare case a
  dispatcher must confirm one anyway, but every override is logged to
  ``deployfleet.dispatch.compliance.override.log`` — a dedicated,
  queryable audit trail, not just a generic event-bus entry, given the
  regulatory stakes.

Rest-hour (``MIN_REST_HOURS``) and consecutive-driving-day
(``MAX_CONSECUTIVE_DRIVING_DAYS``) limits are simple constants for now —
promote them to a per-company setting if a real customer's regional
rules differ from these defaults. Also seeds driver-scoped document
types (Driver's License, Medical Certificate) — this module owns that
seeding since no dedicated driver-compliance module exists in the
current module structure.
