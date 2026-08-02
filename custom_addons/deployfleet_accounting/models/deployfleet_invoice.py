from odoo import fields, models


class DeployfleetInvoice(models.Model):
    """Extends deployfleet_billing's domain invoice with a real Odoo
    accounting entry. Confirming a deployfleet.invoice now also creates and
    posts an `account.move` (a customer invoice) - deployfleet_billing
    itself has no knowledge of `account.move` at all, so this module owns
    the entire translation from "what the customer owes" to "a posted
    accounting document"."""

    _inherit = "deployfleet.invoice"

    account_move_id = fields.Many2one("account.move", readonly=True, copy=False)
    payment_state = fields.Selection(related="account_move_id.payment_state", store=False, readonly=True)

    def action_confirm(self):
        result = super().action_confirm()
        for invoice in self.filtered(lambda inv: inv.state == "confirmed" and not inv.account_move_id):
            invoice._create_account_move()
        return result

    def _create_account_move(self):
        self.ensure_one()
        product = self.env.ref("deployfleet_accounting.product_deployfleet_freight_service")
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.customer_id.id,
            "invoice_date": self.invoice_date,
            "invoice_origin": self.name,
            "invoice_line_ids": [
                (0, 0, {
                    "product_id": product.id,
                    "name": line.description,
                    "quantity": line.quantity,
                    "price_unit": line.unit_amount,
                })
                for line in self.line_ids
            ],
        })
        move.action_post()
        self.account_move_id = move.id
        self.env["deployfleet.event.log"].register_event(
            "deployfleet.invoice.posted", "deployfleet.invoice", self.id,
            {"account_move_id": move.id, "customer_id": self.customer_id.id},
        )
        return move
