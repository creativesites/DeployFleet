========================
DeployFleet AI Agents
========================

Two things live here, per docs/architecture/08-ai-architecture.md §6 and
§11:

1. **The six-agent catalog** (Fleet Analyst, Dispatch Agent, Maintenance
   Agent, Finance Agent, Compliance Agent, Customer Agent) as data records
   on ``deployfleet.ai.agent``, each routed through a matching
   ``deployfleet.ai.feature`` so policy/permission/budget/cache checks in
   ``deployfleet_ai_core``/``deployfleet_ai_permissions`` apply to every
   agent uniformly. This module was originally scoped for Phase 0-1
   (§11's phase-mapping table) but was never actually built during those
   phases - closed here as part of Phase 5, alongside the capabilities
   that were always meant to live in it.

2. **Phase 5's advanced-intelligence slice** — four real, working
   statistical models, each distinct from a rule-based baseline that
   already shipped earlier:

   - ``deployfleet.maintenance.prediction`` — failure-risk scoring from a
     fuel-consumption trend (least-squares regression slope) plus recent
     workshop repair frequency. Distinct from ``deployfleet_maintenance``'s
     Phase 2 odometer/calendar rule-based scheduling.
   - ``deployfleet.fuel.anomaly`` — population z-score outlier detection
     per vehicle's own consumption history. Distinct from
     ``deployfleet_fuel``'s Phase 2 flat 30%-above-average threshold rule.
   - Dispatch scoring — ``deployfleet.shipment._score_candidate()`` is
     extended (not replaced) with a driver's historical on-time completion
     rate and a vehicle's recent breakdown frequency (sourced from the
     ``deployfleet.vehicle.breakdown`` event already on the event bus).
   - ``deployfleet.financial.forecast`` — least-squares trend projection
     over monthly invoice revenue and fuel cost.

**Read before treating any of these as production-grade ML**: this
module's own exit criteria in
docs/architecture/05-implementation-roadmap.md explicitly require "real
(not seeded-only) operational data from a pilot customer" and a
predictive feature "demonstrably outperforming the rule-based baseline it
augments." Neither exists yet - there is no pilot customer and no real
operational history at the time this was built. Everything here is
implemented with genuine, dependency-free closed-form statistics
(``lib/stats.py``: least-squares linear regression, population z-scores)
rather than a trained model, deliberately: the deployment stack runs the
stock ``odoo:19.0`` image with no custom Dockerfile, so a heavy ML
dependency (numpy/scikit-learn) would fail exactly like an unlisted
``requests`` install the moment it's assumed present. These are real,
correct statistical methods - not fabricated - but they are classical
statistics calibrated on seed data, not the validated predictive models
Phase 5's own exit criteria call for. Swap in real ML once real pilot
data exists; don't present the current numbers as more than they are.
