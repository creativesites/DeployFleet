=====================
DeployFleet Payroll
=====================

The country-neutral payroll rule engine — see
``docs/architecture/03-refactoring-roadmap.md``'s fix for the source
project's payroll/country-pack coupling bug: *"deployfleet_payroll
depends only on deployfleet_core/hr; country packs...
register their rule sets via data, not via a manifest dependency chain
between country packs."* This module owns the engine
(``deployfleet.payroll.rule``, ``deployfleet.payroll.payslip``,
``deployfleet.payroll.payslip.line``); it has zero knowledge of Zambia,
NAPSA, PAYE, or any other country-specific concept.

Same rule-engine shape as ``deployfleet_freight_calculator``'s
calculation-rule engine — a formula (fixed / percentage-of-another-rule
/ safe_eval formula) evaluated in sequence, each rule's result available
to later rules by code. A deliberate parallel design, not shared code:
payroll and freight costing are different bounded contexts.

``deployfleet_l10n_zm`` supplies the actual NAPSA/NHIMA/WCF/PAYE rule
*data* on top of this engine. ``deployfleet_loans`` extends the payslip
computation the same way every other cross-module extension in this
codebase works — via ``_inherit``, not by this module knowing about
loans.
