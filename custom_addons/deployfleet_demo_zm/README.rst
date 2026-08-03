=================================
DeployFleet Zambian Demo Data
=================================

A full demo dataset for a fictional Zambian trucking company,
**CreativeSites Logistics**, touching every module in this repository so
a fresh demo install has something real to look at end to end rather than
an empty shell.

Generated entirely through a Python ``post_init_hook`` (``hooks.py``),
not static XML records - the dataset is built the same way a real
company's data would be, calling each model's normal ``create()`` and
``action_*()`` methods (confirm shipments, confirm dispatch assignments,
depart/complete trips, confirm invoices, approve/reject AI actions, ...)
so the same constraints, computed fields, and event-bus side effects a
real customer would trigger are exercised here too - auto-generated
invoices, fired notifications, predictive-maintenance/fuel-anomaly/
financial-forecast records, the lot.

**What it covers**: company (renamed to CreativeSites Logistics, Zambia,
ZMW), 5 depots, 5 customers with contracts and rate cards, 8 vehicles
across 4 vehicle types (one deliberately in ``breakdown`` status - firing
the real event other modules subscribe to - one deliberately with an
expired insurance document), 7 drivers, 5 routes, insurance policies and
compliance documents (mostly valid, one expiring soon, one expired),
maintenance schedules and workshop job cards, parts and tyres, non-vehicle
assets, fuel logs across 3 months per vehicle with one deliberate
consumption anomaly, 5 shipments carried all the way through dispatch ->
trip -> delivery -> invoice -> (offline-safe, see below) ZRA submission
attempt, one shipment confirmed via the compliance-override path (audit
log included), one in-transit shipment, one still-pending shipment, leave
requests, driver advances (one reconciled against a load expense), an
employee loan, driver-performance events, two computed and confirmed
payslips, and three ``deployfleet.ai.action.request`` examples in
different pipeline states (executed, pending approval, rejected).

**Deliberately never calls** ``deployfleet.ai.core.complete()`` - doing so
would spend real tokens/cost against whatever AI provider key is actually
configured on the target database, which could be a real key on a live
server. The six-agent catalog is demonstrated by its presence and
permission configuration, not by an actual LLM call made during install.

**Deliberately leaves the ZRA config untouched** (blank ``base_url``, as
it ships by default) and registers no demo push-notification device
tokens, so installing this module makes no outbound network call at all.
The demo invoices' ZRA submissions will show up in ``error`` state with
"No ZRA API base URL configured" - that is the correct, honest, fast,
offline-safe outcome for a database with no real ZRA device registered,
not a bug in this generator. The WhatsApp config it does create uses
obviously-fake, clearly-labeled placeholder credentials
(``DEMO-...-NOT-REAL``) and is left ``enabled: False``.
