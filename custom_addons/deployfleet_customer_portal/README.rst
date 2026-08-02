===========================
DeployFleet Customer Portal
===========================

Read-only portal pages (``/my/shipments``, ``/my/shipments/<id>``) so a
customer can see their own shipment status and proof of delivery without
needing an internal DeployFleet login - the customer-facing proof this is
a real operations platform, not a WhatsApp group and a paper trip sheet
(see docs/architecture/05-implementation-roadmap.md Phase 4).

Access is restricted at the ORM level via ``ir.rule`` (not just hidden in
the UI): a portal user only ever sees ``deployfleet.shipment``,
``deployfleet.delivery``, and ``deployfleet.invoice`` records whose
customer is their own (or a child of their own) commercial partner.
``deployfleet.shipment`` gains ``portal.mixin`` here so it has the
access-token machinery a shareable portal link needs - the actual
row-level restriction is the ``ir.rule``, not the mixin.
