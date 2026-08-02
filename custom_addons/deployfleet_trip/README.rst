=================
DeployFleet Trip
=================

``deployfleet.trip`` — planned vs. actual execution (departure/arrival,
odometer, delay reason). Created automatically when a
``deployfleet.dispatch.assignment`` is confirmed, via an event bus
subscription (``data/deployfleet_trip_event_subscriptions.xml``), not a
direct dependency of ``deployfleet_dispatch`` on this module — that would
invert the dependency direction.

Also adds ``current_trip_id`` to ``deployfleet.vehicle`` via ``_inherit``,
kept out of ``deployfleet_vehicle`` itself for the same reason.

``deployfleet.trip.shipment.line`` is the many-to-many join between trip
and shipment described in ``docs/architecture/07-domain-model-erd.md`` —
built as a join from day one even though Phase 1's common case is exactly
one line per trip, so multi-shipment trips don't require a schema change
later.
