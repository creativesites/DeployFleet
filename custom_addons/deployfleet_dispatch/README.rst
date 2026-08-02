====================
DeployFleet Dispatch
====================

Full design: ``docs/architecture/09-dispatch-module-design.md``.

``deployfleet.shipment`` (the cargo/load — a first-class entity, not just
trip metadata) and ``deployfleet.dispatch.assignment`` (the planning-time
driver+vehicle+shipment pairing, scored by a simple weighted heuristic —
not a constraint solver — that hard-disqualifies unavailable vehicles and
type-mismatched drivers, and hooks are already in place for Phase 3's
compliance-blocking and rest-hour rules to extend the same disqualify
mechanism).

Ships with kanban-by-state views rather than a custom OWL drag-drop board
— a deliberate Phase 1 scope call, not an oversight. See the design doc §1
and §5 for why.
