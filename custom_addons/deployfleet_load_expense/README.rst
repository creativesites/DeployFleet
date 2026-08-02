=============================
DeployFleet Load Expense
=============================

Records actual costs incurred on a shipment/trip — fuel, tolls,
loading/offloading fees, permits, weighbridge fees — with an optional
receipt photo attachment.

The actuals-tracking companion to ``deployfleet_freight_calculator``'s
estimates (see ``docs/architecture/15-load-sheet-architecture.md`` §5):
nothing before this module recorded what a load *actually* cost, only what
it was predicted to cost. Once enough of these records exist for a
lane/vehicle-type, they can inform better ``deployfleet.calculation.parameter``
values instead of the placeholder defaults shipped with the calculator.
