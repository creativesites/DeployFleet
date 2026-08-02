==================================
DeployFleet Vehicle Compliance
==================================

The vehicle-side application of ``deployfleet_compliance``'s polymorphic
document engine — insurance, roadworthiness, permits, registration/licensing
— per ``docs/architecture/04-module-structure.md``.

Adds ``has_expired_compliance_documents`` to ``deployfleet.vehicle`` from
this module (not from ``deployfleet_vehicle`` itself, keeping the
dependency one-way) and a smart button opening the vehicle's compliance
documents, scoped by ``res_model``/``res_id``. This is exactly the query
``deployfleet_dispatch_compliance`` will call to block dispatch against
a vehicle with expired documents.
