from datetime import date, timedelta

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetInsurancePolicy(TransactionCase):
    def setUp(self):
        super().setUp()
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = self.env["fleet.vehicle.model.brand"].create({"name": "Test Brand"})
            model = self.env["fleet.vehicle.model"].create({"name": "Test Model", "brand_id": brand.id})
        self.vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "INS-001", "model_id": model.id,
        })

    def test_creating_policy_creates_linked_compliance_document(self):
        policy = self.env["deployfleet.insurance.policy"].create({
            "vehicle_id": self.vehicle.id, "policy_number": "POL-001",
            "end_date": date.today() + timedelta(days=180),
        })
        self.assertTrue(policy.compliance_document_id)
        self.assertEqual(policy.compliance_document_id.res_model, "deployfleet.vehicle")
        self.assertEqual(policy.compliance_document_id.res_id, self.vehicle.id)
        self.assertEqual(policy.compliance_document_id.expiry_date, policy.end_date)

    def test_expired_policy_flags_vehicle_as_non_compliant(self):
        self.env["deployfleet.insurance.policy"].create({
            "vehicle_id": self.vehicle.id, "policy_number": "POL-002",
            "end_date": date.today() - timedelta(days=1),
        })
        self.assertTrue(self.vehicle.has_expired_compliance_documents)

    def test_updating_end_date_updates_linked_compliance_document(self):
        policy = self.env["deployfleet.insurance.policy"].create({
            "vehicle_id": self.vehicle.id, "policy_number": "POL-003",
            "end_date": date.today() + timedelta(days=180),
        })
        new_end = date.today() + timedelta(days=365)
        policy.end_date = new_end
        self.assertEqual(policy.compliance_document_id.expiry_date, new_end)


@tagged("post_install", "-at_install")
class TestDeployfleetInsuranceClaim(TransactionCase):
    def setUp(self):
        super().setUp()
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = self.env["fleet.vehicle.model.brand"].create({"name": "Test Brand"})
            model = self.env["fleet.vehicle.model"].create({"name": "Test Model", "brand_id": brand.id})
        vehicle = self.env["deployfleet.vehicle"].create({"license_plate": "INS-CLM-001", "model_id": model.id})
        self.policy = self.env["deployfleet.insurance.policy"].create({
            "vehicle_id": vehicle.id, "policy_number": "POL-CLM-001", "end_date": date.today() + timedelta(days=180),
        })

    def test_claim_workflow(self):
        claim = self.env["deployfleet.insurance.claim"].create({
            "policy_id": self.policy.id, "amount_claimed": 5000.0,
        })
        self.assertEqual(claim.state, "draft")
        claim.action_submit()
        self.assertEqual(claim.state, "submitted")
        claim.action_approve(amount_approved=4500.0)
        self.assertEqual(claim.state, "approved")
        self.assertEqual(claim.amount_approved, 4500.0)
        claim.action_mark_paid()
        self.assertEqual(claim.state, "paid")

    def test_cannot_approve_a_draft_claim(self):
        claim = self.env["deployfleet.insurance.claim"].create({
            "policy_id": self.policy.id, "amount_claimed": 5000.0,
        })
        with self.assertRaises(UserError):
            claim.action_approve()

    def test_reject_sets_state(self):
        claim = self.env["deployfleet.insurance.claim"].create({
            "policy_id": self.policy.id, "amount_claimed": 5000.0,
        })
        claim.action_submit()
        claim.action_reject()
        self.assertEqual(claim.state, "rejected")
