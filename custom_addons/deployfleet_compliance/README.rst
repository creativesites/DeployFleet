========================
DeployFleet Compliance
========================

The polymorphic document-type/expiry/verification engine — see
``docs/architecture/02-reuse-strategy.md`` §1: "both driver documents
(license, medical) and vehicle documents (registration, insurance,
roadworthiness) build on the same base." ``deployfleet.compliance.document``
attaches to any owner record via ``res_model``/``res_id`` (the same
pattern ``ir.attachment`` uses), not a hardcoded ``vehicle_id``/``driver_id``
pair.

``state`` (valid / expiring_soon / expired) is a plain stored field, not
a ``compute=`` — a field that depends on "today" can't be kept correct
by declarative ``@api.depends`` alone, so it's set explicitly on
create/write and refreshed by a daily cron
(``_cron_refresh_states``), the same pattern already used by
``deployfleet.license``.

``has_expired_documents(res_model, res_id)`` is the query
``deployfleet_vehicle_compliance`` and ``deployfleet_dispatch_compliance``
(both depend on this module) call to block dispatch against expired
documents.
