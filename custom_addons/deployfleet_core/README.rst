==============
DeployFleet Core
==============

Foundation module for DeployFleet: the ``DeployFleet`` module category, the
root application menu every other DeployFleet module attaches to, and a
shared reference-sequence mixin used by operational modules that need
human-readable auto-generated codes (trip codes, shipment codes, etc.).

No business logic lives here — see ``docs/architecture/04-module-structure.md``
in the repository root for how this fits into the rest of the product.
