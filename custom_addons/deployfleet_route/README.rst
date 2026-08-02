==================
DeployFleet Route
==================

Named, reusable routes (``deployfleet.route``) between depots, with
ordered stops (``deployfleet.route.stop``).

**Deviation from the documented module structure**: ``docs/architecture/
04-module-structure.md`` lists ``deployfleet_vehicle`` as a dependency of
this module. Nothing in the Phase 1 route/stop design actually needs a
vehicle reference, so that dependency is dropped here rather than carried
as an unused import — add it back if a later feature genuinely needs it
(e.g. per-vehicle-type route restrictions).
