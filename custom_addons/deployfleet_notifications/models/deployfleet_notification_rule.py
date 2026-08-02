from odoo import fields, models


class DeployfleetNotificationRule(models.Model):
    """Data-driven mapping from an event-bus event to who gets notified and
    what they're told - a new module adding a notification for its own
    events registers one of these, it never requires editing this module
    (the same lesson the event bus itself already applies, see
    docs/architecture/06-risks-and-recommendations.md risk #4).

    Reuses Odoo's own notification engine (`res.partner.message_post()`,
    i.e. the Discuss inbox / mail notification system already built into
    Odoo core) rather than building a parallel one - per CLAUDE.md §1's
    "reuse everything generic" guidance.
    """

    _name = "deployfleet.notification.rule"
    _description = "DeployFleet Notification Rule"
    _order = "sequence, id"

    name = fields.Char(required=True)
    event_pattern = fields.Char(
        required=True,
        help="fnmatch-style pattern against the event-bus event name, e.g. 'deployfleet.trip.delayed'.",
    )
    recipient_type = fields.Selection(
        [
            ("shipment_customer", "Shipment's Customer"),
            ("assigned_driver", "Assigned Driver"),
            ("dispatchers", "All Dispatchers"),
        ],
        required=True,
    )
    message_template = fields.Char(
        required=True,
        help="Python str.format() template. Available keys depend on the source model - "
             "see deployfleet.notification.log._resolve_recipients() for what each "
             "recipient_type/source_model combination provides.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
