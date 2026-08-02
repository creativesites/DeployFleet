====================
DeployFleet Tyres
====================

Per-position tyre records (``deployfleet.tyre``) with tread-depth history
(``deployfleet.tyre.reading``) and rotation/retread/scrap history
(``deployfleet.tyre.event``) — per
``docs/architecture/04-module-structure.md``: "tread depth readings,
position tracking, rotation/retread/scrap history."

Only one active (fitted/retreaded) tyre may occupy a given
(vehicle, position) pair at a time — enforced by a Python constraint, not
a SQL unique index, specifically so a scrapped tyre never blocks
recording its replacement at the same position.
