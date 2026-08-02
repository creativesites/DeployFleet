from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetVehicleCompliance(TransactionCase):
    def setUp(self):
        super().setUp()
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = self.env["fleet.vehicle.model.brand"].create({"name": "Test Brand"})
            model = self.env["fleet.vehicle.model"].create({"name": "Test Model", "brand_id": brand.id})
        self.vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "COMP-001", "model_id": model.id,
        })
        self.insurance_type = self.env.ref("deployfleet_vehicle_compliance.doc_type_vehicle_insurance")

    def test_no_documents_means_not_expired(self):
        self.assertFalse(self.vehicle.has_expired_compliance_documents)

    def test_expired_document_flags_vehicle(self):
        self.env["deployfleet.compliance.document"].create({
            "document_type_id": self.insurance_type.id,
            "res_model": "deployfleet.vehicle", "res_id": self.vehicle.id,
            "expiry_date": fields.Date.today() - timedelta(days=1),
        })
        self.assertTrue(self.vehicle.has_expired_compliance_documents)

    def test_valid_document_does_not_flag_vehicle(self):
        self.env["deployfleet.compliance.document"].create({
            "document_type_id": self.insurance_type.id,
            "res_model": "deployfleet.vehicle", "res_id": self.vehicle.id,
            "expiry_date": fields.Date.today() + timedelta(days=90),
        })
        self.assertFalse(self.vehicle.has_expired_compliance_documents)

    def test_action_view_compliance_documents_domain_scopes_to_vehicle(self):
        action = self.vehicle.action_view_compliance_documents()
        expected_domain = [("res_model", "=", "deployfleet.vehicle"), ("res_id", "=", self.vehicle.id)]
        self.assertEqual(action["domain"], expected_domain)
