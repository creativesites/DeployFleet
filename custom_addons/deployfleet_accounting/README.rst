======================
DeployFleet Accounting
======================

Extends ``deployfleet.invoice`` (from ``deployfleet_billing``) so confirming
one also creates and posts a real ``account.move`` (a customer invoice) -
one line per ``deployfleet.invoice.line``, all posted against a single
generic "Freight Transport Service" product so Odoo can derive the income
account without DeployFleet needing its own product catalog.

``deployfleet_billing`` has no knowledge of ``account.move`` at all; this
module owns the entire translation from "what the customer owes" to "a
posted accounting document," and fires ``deployfleet.invoice.posted`` on the
event bus once the move is posted - ``deployfleet_zra`` (next) subscribes to
that event to submit the invoice to ZRA's Smart Invoice / VSDC system.
