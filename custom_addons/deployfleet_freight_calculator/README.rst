===============================
DeployFleet Freight Calculator
===============================

The company-configurable calculation-rule engine
(``deployfleet.calculation.rule`` / ``deployfleet.calculation.variable`` /
``deployfleet.calculation.parameter``) plus a wizard covering the Phase 2
calculators recommended in ``docs/architecture/14-freight-calculator-engine.md``:
Load Profit, Cost per Km, Break-even Trips per Month, Fuel Cost, Trip Time,
and Tyre Cost.

Formulas are company-editable data, evaluated exclusively via
``odoo.tools.safe_eval`` — never a bare ``eval()``/``exec()``. Company-specific
*values* (fuel price, driver cost, maintenance rate, ...) live on
``deployfleet.calculation.parameter``, separate from the formula itself, so an
admin can tune assumptions without anyone reviewing a code change.

Seed data ships placeholder parameter values (``data/deployfleet_calculation_parameter_data.xml``)
— every one of them should be reviewed and adjusted per company under
DeployFleet > Freight Calculator > Calculation Parameters before the
calculator is relied on for real pricing decisions.

**Not in this module**: the Rate and Empty Miles calculators (doc 14 §4,
items #3–#4) need market-rate benchmarking and backhaul-probability data that
don't exist yet — see ``deployfleet_rate_intelligence`` in
``docs/architecture/13-freight-intelligence-architecture.md``. The Container
Calculator (#9) and AI Calculator Assistant (#11) are explicitly lower
priority per doc 14 §8 and are not built here either.
