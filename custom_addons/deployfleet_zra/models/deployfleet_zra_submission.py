import json

from odoo import api, fields, models


class DeployfleetZRASubmission(models.Model):
    """One ZRA Smart Invoice submission attempt for a `deployfleet.invoice`.
    Created automatically when `deployfleet_accounting` posts an invoice's
    `account.move` and fires `deployfleet.invoice.posted` on the event bus.
    """

    _name = "deployfleet.zra.submission"
    _description = "DeployFleet ZRA Smart Invoice Submission"
    _order = "create_date desc"

    invoice_id = fields.Many2one("deployfleet.invoice", required=True, ondelete="cascade")
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("error", "Error"),
        ],
        default="draft",
        required=True,
    )
    zra_receipt_no = fields.Char(string="ZRA Receipt No.")
    request_payload = fields.Text(readonly=True)
    response_payload = fields.Text(readonly=True)
    error_message = fields.Text(readonly=True)
    submitted_date = fields.Datetime(readonly=True)

    def action_submit(self):
        for submission in self:
            config = self.env["deployfleet.zra.config"].search(
                [("company_id", "=", submission.company_id.id)], limit=1
            )
            if not config:
                submission.write({
                    "state": "error",
                    "error_message": self.env._("No ZRA device configuration for this company."),
                })
                continue
            try:
                client = self.env["deployfleet.zra.client"]
                payload, response = client._submit_sale(config, submission.invoice_id)
                submission.write({
                    "state": "accepted",
                    "request_payload": json.dumps(payload),
                    "response_payload": json.dumps(response),
                    "zra_receipt_no": (response.get("data") or {}).get("rcptNo"),
                    "submitted_date": fields.Datetime.now(),
                })
            except Exception as exc:  # noqa: BLE001 — a failed fiscal submission must never raise past this point
                submission.write({
                    "state": "error",
                    "error_message": str(exc),
                    "submitted_date": fields.Datetime.now(),
                })

    @api.model
    def _handle_bus_event(self, event_name, _source_model, source_id, _payload):
        """Event bus subscriber — see
        data/deployfleet_zra_event_subscriptions.xml."""
        if event_name != "deployfleet.invoice.posted":
            return None
        invoice = self.env["deployfleet.invoice"].browse(source_id)
        if not invoice.exists():
            return None
        submission = self.create({"invoice_id": invoice.id, "company_id": invoice.company_id.id})
        submission.action_submit()
        return submission
