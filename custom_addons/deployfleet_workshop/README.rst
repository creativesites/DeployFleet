======================
DeployFleet Workshop
======================

Job cards (``deployfleet.workshop.job.card``) riding the
open -> diagnosis -> repair -> approval -> closed state machine per
``docs/architecture/04-module-structure.md``, with labor/parts lines
(``deployfleet.workshop.job.line``).

Starting repair puts the vehicle into ``maintenance`` status
(``deployfleet_vehicle``'s ``action_set_maintenance()``); closing the job
card consumes tracked parts from stock (``deployfleet_parts``'
``action_consume_stock()``) and returns the vehicle to ``available``.
