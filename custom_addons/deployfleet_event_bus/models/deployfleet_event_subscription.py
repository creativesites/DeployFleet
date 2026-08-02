from odoo import fields, models


class DeployfleetEventSubscription(models.Model):
    """The subscriber registry that replaces DeployGuard's hardcoded
    dispatch if-chain (see docs/architecture/06-risks-and-recommendations.md
    risk #4). A module that wants to react to an event declares one of these
    as a data record — it never requires touching this module or any other
    subscriber's code.

    Example (a module's data/*.xml):

        <record id="subscription_mobile_push_on_breakdown" model="deployfleet.event.subscription">
            <field name="event_pattern">vehicle.breakdown.*</field>
            <field name="model_name">deployfleet.mobile.push.bridge</field>
            <field name="method_name">_handle_bus_event</field>
        </record>

    `event_pattern` supports simple fnmatch-style wildcards (`*`, `?`), so a
    subscriber can listen to a whole family of events (`vehicle.*`) or one
    exact event name.
    """

    _name = "deployfleet.event.subscription"
    _description = "DeployFleet Event Bus Subscriber Registry Entry"
    _order = "sequence, id"

    name = fields.Char(compute="_compute_name", store=True)
    event_pattern = fields.Char(
        required=True,
        index=True,
        help="Event name or fnmatch-style pattern this subscription reacts to, "
             "e.g. 'vehicle.breakdown.created' or 'vehicle.*'.",
    )
    model_name = fields.Char(
        required=True,
        help="Technical model name implementing the handler, e.g. 'deployfleet.mobile.push.bridge'.",
    )
    method_name = fields.Char(
        required=True,
        default="_handle_bus_event",
        help="Method called as handler(event_name, source_model, source_id, payload).",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    def _compute_name(self):
        for sub in self:
            sub.name = f"{sub.event_pattern} → {sub.model_name}.{sub.method_name}"
