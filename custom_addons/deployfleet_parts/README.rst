===================
DeployFleet Parts
===================

Parts categories (``deployfleet.part.category``) and stocked items
(``deployfleet.part``) with a low-stock alert (``is_low_stock``, computed
against a configurable reorder level) and ``action_receive_stock()``/
``action_consume_stock()`` helpers for other modules to call.

A lightweight stock tracker, not an Odoo Inventory integration — the
workshop/tyre use case (``deployfleet_workshop``, ``deployfleet_tyres``,
both depend on this module) only needs quantity-on-hand and a reorder
alert, not multi-warehouse routing. Per
``docs/architecture/04-module-structure.md``: parts before tyres before
workshop, in that dependency order.
