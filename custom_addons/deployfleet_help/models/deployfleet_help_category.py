from odoo import fields, models


class DeployfleetHelpCategory(models.Model):
    """A Help Center browse category (e.g. "Getting Started", "Module
    Guides" with 8 children, "FAQ"). `parent_id` lets a category group
    like "Module Guides" hold one child per business domain without
    each domain needing its own top-level category.

    `context_key` is the deep-link key a workspace's Help button passes
    when opening the Help Center pre-scoped to this category — see
    deployfleet_ui's help_center.js for the resolution order (an
    article's own context_key wins over its category's).
    """

    _name = "deployfleet.help.category"
    _description = "DeployFleet Help Category"
    _order = "sequence, name"

    name = fields.Char(required=True)
    slug = fields.Char(required=True, index=True, help="Stable key for deep-links, independent of the display name.")
    parent_id = fields.Many2one("deployfleet.help.category", ondelete="cascade")
    child_ids = fields.One2many("deployfleet.help.category", "parent_id")
    sequence = fields.Integer(default=10)
    icon = fields.Char(help="FontAwesome class, e.g. 'fa fa-truck'.")
    description = fields.Char(help="One-line summary shown on the Help Center landing page's category card.")
    domain_key = fields.Char(
        index=True,
        help="Mega Menu domain this category corresponds to (fleet/dispatch/compliance/billing/driver/ai), "
             "when applicable — Module Guide categories set this; FAQ/Troubleshooting/Getting Started do not.",
    )
    context_key = fields.Char(index=True, help="Deep-link key a workspace's Help button passes to land here.")
    article_ids = fields.One2many("deployfleet.help.article", "category_id")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("slug_unique", "UNIQUE(slug)", "This slug is already in use by another category."),
    ]
