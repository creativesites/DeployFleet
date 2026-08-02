================================
DeployFleet Driver Performance
================================

Driver safety/performance events (``deployfleet.driver.performance.event``)
— accidents, violations, harsh braking, speeding, fuel-abuse patterns,
late deliveries — reframed from "discipline" per
``docs/architecture/04-module-structure.md``: this is a safety/
performance signal, not an HR conduct write-up.

Adds ``deployfleet_reliability_score`` to ``hr.employee`` from this
module (the same classical-extension pattern ``deployfleet_driver``
itself uses), starting at 100 and reduced by each event's
``score_impact`` over a trailing 365-day window — non-stored and
computed fresh on every read, the same reasoning as
``deployfleet_leave``'s balance fields: derived from records with no
direct FK back to ``hr.employee``, so automatic dependency tracking
can't fire.

Optional payroll deduction extends ``deployfleet.payroll.payslip`` the
same way ``deployfleet_loans`` does: ``action_compute()`` previews a
"DRIVER_PERF" deduction line for any unpaid event with a
``payroll_deduction_amount`` in the payslip's period, and
``action_confirm()`` — a one-time transition — is what marks those
events ``payroll_deduction_applied`` so they're never charged twice
across periods.

**Deviation from the documented module structure**: adds
``deployfleet_driver`` as an explicit dependency (that document lists
only ``deployfleet_loans``/``mail``) — this module's whole domain is
driver-specific (`domain=[("deployfleet_is_driver", "=", True)]`), which
only exists once ``deployfleet_driver`` is installed.
