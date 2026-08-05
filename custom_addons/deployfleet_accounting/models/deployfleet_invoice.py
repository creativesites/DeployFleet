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
        self._ensure_income_account(product)
        self._ensure_receivable_account(self.customer_id)
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

    def _ensure_income_account(self, product):
        """A fresh company with no chart of accounts installed has no
        account.account records at all, so account.move.line's account_id
        would end up NULL and violate its accountable-fields check
        constraint. Lazily provisions one dedicated income account the
        first time any invoice is posted, rather than requiring every new
        DeployFleet company to run Odoo's full accounting-onboarding wizard
        before its first invoice."""
        if product.property_account_income_id:
            return
        product.property_account_income_id = self._get_or_create_account(
            "400100", "Freight Service Income", "income",
        )

    def _ensure_receivable_account(self, partner):
        if partner.property_account_receivable_id:
            return
        partner.property_account_receivable_id = self._get_or_create_account(
            "100100", "Accounts Receivable", "asset_receivable", reconcile=True,
        )

    def _get_or_create_account(self, code, name, account_type, reconcile=False):
        # Engineering-audit fix (H-12): the search here previously had no
        # company filter at all - a matching code created for Company A
        # would be silently reused for Company B's invoice too (posting
        # Company B's revenue into Company A's chart of accounts), and
        # the reverse (a matching account existing but invisible to a
        # standard multi-company account.account rule) could instead
        # cause a spurious duplicate account to be created. Scoping the
        # lookup to the requesting company mirrors the same
        # company_ids-vs-company_id branch already used below for create().
        account_model = self.env["account.account"]
        domain = [("code", "=", code)]
        if "company_ids" in account_model._fields:
            domain.append(("company_ids", "in", self.env.company.id))
        elif "company_id" in account_model._fields:
            domain.append(("company_id", "=", self.env.company.id))
        account = account_model.search(domain, limit=1)
        if account:
            return account
        vals = {"name": name, "code": code, "account_type": account_type, "reconcile": reconcile}
        if "company_ids" in account_model._fields:
            vals["company_ids"] = [(6, 0, [self.env.company.id])]
        elif "company_id" in account_model._fields:
            vals["company_id"] = self.env.company.id
        return account_model.create(vals)
