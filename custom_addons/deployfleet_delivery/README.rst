=====================
DeployFleet Delivery
=====================

``deployfleet.delivery`` — proof of delivery (signature, photo, recipient,
GPS stamp placeholder) keyed to (trip, shipment) rather than just trip, so
a multi-drop trip produces one delivery per shipment.

Creating a delivery record is itself the completion event: it marks the
shipment ``delivered`` and publishes ``deployfleet.delivery.completed``.
It does not complete the trip — a multi-stop trip may still have other
shipments in transit; the driver/dispatcher completes the trip separately
once the whole run is done.

``gps_stamp`` is free text for Phase 1. Real GPS integration is an
explicitly later phase — see ``docs/architecture/05-implementation-roadmap.md``,
"Beyond Phase 5."
