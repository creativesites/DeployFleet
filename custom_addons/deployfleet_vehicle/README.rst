===================
DeployFleet Vehicle
===================

``deployfleet.vehicle`` — the DeployFleet operational layer over Odoo's
native ``fleet.vehicle``, joined via delegation inheritance (``_inherits``)
rather than a standalone reinvention or a plain field-bolt-on
``_inherit``. See ``docs/architecture/03-refactoring-roadmap.md`` §A.2 and
``docs/architecture/06-risks-and-recommendations.md`` risk #2 for why.

Adds: operational ``status`` (available/assigned/maintenance/breakdown/
retired), ``current_driver_id``, and ``vehicle_type_id``. Everything else
(license plate, model, brand, odometer, ...) is Odoo Fleet's own data,
reachable directly on this model thanks to delegation.

``current_trip_id`` is intentionally not defined here — ``deployfleet_trip``
adds it via ``_inherit`` once that module exists, so the dependency only
ever points one way (trip depends on vehicle, never the reverse).
