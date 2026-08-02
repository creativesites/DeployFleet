============================
DeployFleet AI Permissions
============================

The "genuinely new subsystem" per docs/architecture/08-ai-architecture.md
§9: nothing in ``deployfleet_ai_core`` on its own enforces which *role*
may use which AI feature - that's a coarser, different concern from
Odoo's model-level ACLs ("can this role ask this kind of question," not
"can this role read this model").

``deployfleet.ai.permission`` is opt-in per feature: a
``deployfleet.ai.feature`` with no permission rows is open to every
authenticated user (matching pre-existing ``deployfleet_ai_core``
behavior). Creating even one row for a feature turns it into an explicit
allow-list for that feature's group(s) only. Wired into
``deployfleet.ai.core.complete()`` via ``_inherit`` (see
``models/deployfleet_ai_core.py``), so the check runs before policy,
provider, budget, or cache - a user without permission never reaches any
of those.

**Deliberately not implemented**: a generic row-level query-scoping
engine (the doc's "a driver may query the Dispatch Agent about their own
trips, not the whole company's" example). That's enforced per-feature by
whatever code builds that feature's query running as the logged-in user
rather than sudo() - the same mechanism deployfleet_mobile_dispatcher and
deployfleet_mobile_customer already rely on for their own row-level
scoping - not a capability this module adds generically. Per-user AI
token/cost budgets (the doc's "optionally per user") are also deferred;
only the existing per-company budget in deployfleet_ai_core applies.
