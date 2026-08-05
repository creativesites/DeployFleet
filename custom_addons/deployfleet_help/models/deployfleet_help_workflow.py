from odoo import fields, models


class DeployfleetHelpWorkflow(models.Model):
    """One visual step-diagram (e.g. "Customer to Delivery",
    "Vehicle Maintenance") — stored as structured data rather than
    hardcoded in a JS file, so it's editable without a code deploy and
    is directly AI-retrievable later (see doc 22's future-integration
    sketch).
    """

    _name = "deployfleet.help.workflow"
    _description = "DeployFleet Help Workflow"
    _order = "sequence, name"

    name = fields.Char(required=True)
    slug = fields.Char(required=True, index=True)
    description = fields.Text()
    domain_key = fields.Char(help="Mega Menu domain this workflow is most relevant to, when applicable.")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    step_ids = fields.One2many("deployfleet.help.workflow.step", "workflow_id")

    _sql_constraints = [
        ("slug_unique", "UNIQUE(slug)", "This slug is already in use by another workflow."),
    ]


class DeployfleetHelpWorkflowStep(models.Model):
    """One step of a workflow diagram, e.g. "Shipment" in the
    Customer-to-Delivery workflow."""

    _name = "deployfleet.help.workflow.step"
    _description = "DeployFleet Help Workflow Step"
    _order = "sequence"

    workflow_id = fields.Many2one("deployfleet.help.workflow", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    title = fields.Char(required=True)
    description = fields.Text(required=True, help="The plain-language explanation of this step.")
    icon = fields.Char(help="FontAwesome class, e.g. 'fa fa-file-invoice'.")
    related_model = fields.Char(
        help="Soft-coupled technical model name this step corresponds to (e.g. 'deployfleet.shipment'), "
             "for future 'jump to this in the app' or AI-retrieval linking — referenced as a plain string, "
             "the same soft-coupling convention deployfleet_ui already uses everywhere.",
    )
    related_article_id = fields.Many2one("deployfleet.help.article", help="'Learn more' link into a Module Guide.")
