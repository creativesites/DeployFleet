==================
DeployFleet Driver
==================

Driver profile fields on ``hr.employee``: license class/number/expiry,
endorsements, qualified vehicle types, years of experience, and a risk
score (manually adjustable until ``deployfleet_driver_performance``,
Phase 3, starts computing it from real incidents).

**Deviation from the documented module structure**: ``docs/architecture/
04-module-structure.md`` lists a ``deployfleet_hr`` dependency for general
non-driver staff administration. It is not built — there is no content for
it yet, and an empty module solely to match a dependency diagram is
exactly the premature abstraction this project's own conventions warn
against. Add it once a real non-driver-staff need appears.
