======================================
DeployFleet Localization - Zambia
======================================

Zambian NAPSA/NHIMA/PAYE payroll rule *data* on top of
``deployfleet_payroll``'s country-neutral engine. Depends only on
``deployfleet_payroll`` — the payroll module itself has zero knowledge
of this module or any other country pack, per
``docs/architecture/03-refactoring-roadmap.md``'s fix for the source
project's payroll/country-pack coupling bug.

**These rates are illustrative placeholders** — review and correct
against the current official NAPSA/NHIMA/ZRA tables before relying on
them for a real payroll run, the same caveat
``deployfleet_freight_calculator``'s seed parameters carry.

**WCF (Workers Compensation Fund) is deliberately not seeded here**: it
is an employer-borne contribution in Zambia, not a deduction from the
employee's own pay, so it has no payslip line in this employee-facing
engine — track it separately as an employer-cost concern if that's
ever needed, rather than modeling it as a payroll rule it isn't.

PAYE is computed via a single ``formula``-type rule implementing a
simplified four-band progressive tax over taxable income
(``BASIC - NAPSA``), evaluated through ``safe_eval`` like every other
formula in this rule engine.
