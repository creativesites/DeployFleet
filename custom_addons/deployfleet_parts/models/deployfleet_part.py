from odoo import api, fields, models
from odoo.exceptions import UserError


class DeployfleetPart(models.Model):
    """A stocked spare part — consumed by `deployfleet_workshop` job cards
    and `deployfleet_tyres` replacements (both depend on this module),
    per docs/architecture/04-module-structure.md: 'parts before tyres
    before workshop, in that dependency order.'

    Deliberately a lightweight stock tracker, not an integration with
    Odoo's full Inventory app — the workshop/tyre use case only needs
    quantity-on-hand and a reorder alert, not multi-warehouse routing.
    """

    _name = "deployfleet.part"
    _description = "DeployFleet Part"
    _order = "name"

    name = fields.Char(required=True)
    reference = fields.Char(string="Part Number")
    category_id = fields.Many2one("deployfleet.part.category")
    quantity_on_hand = fields.Float(default=0.0)
    reorder_level = fields.Float(default=0.0)
    unit_cost = fields.Monetary()
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)
    is_low_stock = fields.Boolean(compute="_compute_is_low_stock", store=True)

    @api.depends("quantity_on_hand", "reorder_level")
    def _compute_is_low_stock(self):
        for part in self:
            part.is_low_stock = part.quantity_on_hand <= part.reorder_level

    def action_receive_stock(self, quantity):
        self.ensure_one()
        if quantity <= 0:
            raise UserError(self.env._("Received quantity must be positive."))
        self.quantity_on_hand += quantity

    def action_consume_stock(self, quantity):
        """Engineering-audit fix: this previously read
        self.quantity_on_hand, checked it, and wrote back a decremented
        value - not atomic at the SQL level. Two technicians closing two
        different job cards that both consume the same shared part
        concurrently could each read the same starting quantity, both
        pass the "enough stock" check, and the second write would
        silently overwrite the first's decrement (a lost update, parts
        being an explicitly shared, non-vehicle-scoped pool). SELECT ...
        FOR UPDATE locks this row for the rest of the transaction, so a
        second concurrent caller blocks here until the first commits and
        then sees the up-to-date quantity."""
        self.ensure_one()
        if quantity <= 0:
            raise UserError(self.env._("Consumed quantity must be positive."))
        self.env.cr.execute(
            "SELECT quantity_on_hand FROM deployfleet_part WHERE id = %s FOR UPDATE",
            (self.id,),
        )
        [current_quantity] = self.env.cr.fetchone()
        if quantity > current_quantity:
            raise UserError(
                self.env._(
                    "Cannot consume %(quantity)s of '%(part)s' — only %(available)s in stock.",
                    quantity=quantity, part=self.name, available=current_quantity,
                )
            )
        self.write({"quantity_on_hand": current_quantity - quantity})
