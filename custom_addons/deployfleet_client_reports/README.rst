============================
DeployFleet Client Reports
============================

A wizard (``deployfleet.client.report.wizard``) that prints a per-customer
PDF summary over an explicit date range: shipments delivered, on-time trip
performance (completed trips that arrived on or before their planned
arrival), and billing (``deployfleet_billing`` invoices and their total).

Deliberately a wizard rather than a stored, schedulable report
configuration - there is nothing here worth persisting between runs; if a
recurring emailed report ever becomes a real requirement, that's a
`deployfleet_notifications`-style scheduled job wrapping this wizard's
query methods, not a rebuild of them.
