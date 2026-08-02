===============================
DeployFleet Driver Advance
===============================

Cash advances issued to drivers for fuel float, tolls/border fees, or
subsistence on a trip (``deployfleet.driver.advance``) — see
``docs/architecture/15-load-sheet-architecture.md`` §6, where this is
flagged as the strongest standalone idea in the load-sheet proposal it
reconciles: a real, underserved operational need for African long-haul
trucking, not previously modeled anywhere in DeployFleet.

Reconciles against ``deployfleet.load.expense`` records via the
``advance_id`` field this module adds to that model (one-way dependency,
mirroring how ``deployfleet_trip`` adds ``current_trip_id`` to
``deployfleet.vehicle``). An unreconciled outstanding balance can later
feed ``deployfleet_payroll``'s deduction pipeline (Phase 3) — the same
mechanism ``deployfleet_loans`` uses, not a second one. Until that module
exists, ``action_mark_deducted()`` is a manual state transition only.
