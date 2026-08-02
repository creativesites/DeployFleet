====================
DeployFleet Assets
====================

Non-vehicle trackable assets (``deployfleet.asset``) — trailers,
containers, GPS trackers, tools, safety equipment — per
``docs/architecture/04-module-structure.md``.

Deliberately independent of ``deployfleet_vehicle`` (depends only on
``deployfleet_core``, matching the documented dependency list):
``location`` is free text rather than a vehicle reference, so this
module doesn't need to couple to the vehicle domain to be useful, and
can be built/installed independently of the rest of the fleet-assets
chain per that document's own note that this module "can be built in
parallel."
