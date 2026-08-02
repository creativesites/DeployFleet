=======================
DeployFleet Insurance
=======================

Insurance policies (``deployfleet.insurance.policy``), premiums, and
claims (``deployfleet.insurance.claim``) per
``docs/architecture/04-module-structure.md``: "Policy, premium, claims."

**Deviation from the documented module structure**: that document lists
``deployfleet_compliance``/``deployfleet_vehicle`` as this module's
dependencies. This module depends on ``deployfleet_vehicle_compliance``
instead (which already depends on both), specifically so it can reuse
the ``doc_type_vehicle_insurance`` document type that module already
seeds, rather than seeding a second, competing "insurance" document
type. Creating a policy automatically creates a linked
``deployfleet.compliance.document`` (kept in sync on ``end_date``
changes) — this is what makes an expired policy actually block dispatch
via ``deployfleet_dispatch_compliance``, not just a record sitting in
this module unconnected to the rest of the compliance chain.
