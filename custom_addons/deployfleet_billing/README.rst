===================
DeployFleet Billing
===================

Customer-facing pricing (``deployfleet.rate.card``, scoped per contract and
optionally per vehicle type) and the domain-level billable document it
produces (``deployfleet.invoice``). Deliberately separate from
``deployfleet.calculation.rule`` (``deployfleet_freight_calculator``), which is
the company's internal cost estimate — margin is the difference between the
two, not something either model computes on its own.

An invoice is generated automatically, in draft, when a
``deployfleet.trip.completed`` event fires on the event bus — one invoice per
customer, covering every shipment on that trip whose contract has a matching
rate card. A shipment with no contract, or a contract with no rate card yet,
is a spot load or an incomplete pricing setup — it's silently left off the
auto-generated invoice rather than blocking trip completion.

``deployfleet_accounting`` (a separate module, depending on this one) is what
turns a confirmed ``deployfleet.invoice`` into a real ``account.move`` — this
module has no knowledge of Odoo accounting at all, so the pricing domain
stays usable even for a company that hasn't wired up accounting yet.
