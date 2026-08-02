===================
DeployFleet Loans
===================

Employee loans (``deployfleet.loan``) with automatic payslip deductions,
per ``docs/architecture/04-module-structure.md``: "Employee loans,
payslip deductions."

Extends ``deployfleet.payroll.payslip`` from this module (not from
``deployfleet_payroll`` itself, keeping the dependency one-way):
``action_compute()`` adds a fresh "LOAN" deduction line each time it
runs (capped at each active loan's remaining ``outstanding_balance``),
and ``action_confirm()`` — a one-time transition the base model already
enforces — is where the balance is actually reduced, so recomputing a
draft/computed payslip never double-drains a loan.

The "LOAN" ``deployfleet.payroll.rule`` seeded by this module is
deliberately inactive: it exists only so payslip lines have something
to point to; if it were active, ``deployfleet_payroll``'s own rule
search would create a second, always-zero line for it alongside the
real one this module creates directly.

Not wired here: ``deployfleet_driver_advance``'s (Phase 2)
``action_mark_deducted()`` transition. That remains a manual step —
bridging an unreconciled driver cash advance into this module's
deduction pipeline is a real, useful integration, but it's additional
scope beyond what this module builds, not something to add
speculatively.
