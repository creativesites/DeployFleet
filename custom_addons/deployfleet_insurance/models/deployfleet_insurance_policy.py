from odoo import api, fields, models


class DeployfleetInsurancePolicy(models.Model):
    """A vehicle insurance policy — see
    docs/architecture/04-module-structure.md: 'Policy, premium, claims.'

    Keeps a linked `deployfleet.compliance.document` in sync
    (`compliance_document_id`), reusing the `doc_type_vehicle_insurance`
    type seeded by `deployfleet_vehicle_compliance` rather than seeding a
    second, competing "insurance" document type — see README for why
    this module depends on `deployfleet_vehicle_compliance` directly
    instead of `deployfleet_compliance`/`deployfleet_vehicle` as
    docs/architecture/04-module-structure.md's dependency column lists.
    """

    _name = "deployfleet.insurance.policy"
    _description = "DeployFleet Insurance Policy"
    _order = "end_date desc"

    # Engineering-audit fix (C-01): no company_id field existed on this
    # model at all.
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    vehicle_id = fields.Many2one("deployfleet.vehicle", required=True)
    policy_number = fields.Char(required=True)
    insurer_id = fields.Many2one("res.partner")
    start_date = fields.Date()
    end_date = fields.Date(required=True)
    premium_amount = fields.Monetary()
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)
    compliance_document_id = fields.Many2one("deployfleet.compliance.document", readonly=True, copy=False)
    claim_ids = fields.One2many("deployfleet.insurance.claim", "policy_id")

    @api.model_create_multi
    def create(self, vals_list):
        policies = super().create(vals_list)
        doc_type = self.env.ref("deployfleet_vehicle_compliance.doc_type_vehicle_insurance")
        for policy in policies:
            document = self.env["deployfleet.compliance.document"].create({
                "document_type_id": doc_type.id,
                "res_model": "deployfleet.vehicle", "res_id": policy.vehicle_id.id,
                "reference_number": policy.policy_number,
                "issue_date": policy.start_date,
                "expiry_date": policy.end_date,
            })
            policy.compliance_document_id = document.id
        return policies

    def write(self, vals):
        res = super().write(vals)
        if any(field in vals for field in ("end_date", "start_date", "policy_number")):
            for policy in self:
                if policy.compliance_document_id:
                    policy.compliance_document_id.write({
                        "expiry_date": policy.end_date,
                        "issue_date": policy.start_date,
                        "reference_number": policy.policy_number,
                    })
        return res
