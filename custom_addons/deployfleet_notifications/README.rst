===========================
DeployFleet Notifications
===========================

A data-driven event-bus subscriber: ``deployfleet.notification.rule``
declares which event pattern notifies which kind of recipient
(``shipment_customer``, ``assigned_driver``, ``dispatchers``) with what
message template - adding a notification for a new event never means
editing this module's code, only adding a data record.

Subscribed once, generically, to ``deployfleet.*`` on the event bus;
matching individual rules against the fired event name is this module's
own concern, so it never needs another ``deployfleet.event.subscription``
record per notification.

Delivery reuses Odoo's own notification engine
(``res.partner.message_post()``, i.e. the Discuss inbox / mail
notification system already built into Odoo core) rather than building a
parallel one, per CLAUDE.md's "reuse everything generic" guidance.
``deployfleet.notification.log`` is the audit trail - every attempt,
sent or failed, with the rendered message and recipient.
