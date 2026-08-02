==================
DeployFleet Fuel
==================

Fuel fill-up logs (``deployfleet.fuel.log``) per vehicle, with computed
distance-since-last-fill and consumption (L/100km), and a simple
threshold-based anomaly flag (more than 30% above the vehicle's own
trailing average) — per
``docs/architecture/05-implementation-roadmap.md`` Phase 2: *"even a
simple threshold rule is worth shipping before the predictive version
lands in Phase 5."*

Deliberately does not depend on ``deployfleet_freight_calculator`` —
fuel logging has standalone value independent of the cost-estimation
engine; the two can be connected later (real consumption informing
calculator parameters) without this module needing to change.
