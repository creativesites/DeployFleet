from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetComplianceDocument(TransactionCase):
    def setUp(self):
        super().setUp()
        self.doc_type = self.env["deployfleet.compliance.document.type"].create({
            "name": "Insurance", "code": "insurance", "applies_to_model": "deployfleet.vehicle",
        })

    def _create_document(self, expiry_date=None, **extra):
        vals = {
            "document_type_id": self.doc_type.id, "res_model": "deployfleet.vehicle", "res_id": 1,
            "expiry_date": expiry_date,
        }
        vals.update(extra)
        return self.env["deployfleet.compliance.document"].create(vals)

    def test_document_requiring_expiry_without_one_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_document(expiry_date=None)

    def test_document_without_expiry_requirement_allows_none(self):
        doc_type = self.env["deployfleet.compliance.document.type"].create({
            "name": "Registration Certificate", "code": "reg_cert",
            "applies_to_model": "deployfleet.vehicle", "requires_expiry": False,
        })
        doc = self.env["deployfleet.compliance.document"].create({
            "document_type_id": doc_type.id, "res_model": "deployfleet.vehicle", "res_id": 1,
        })
        self.assertEqual(doc.state, "valid")

    def test_state_valid_when_far_from_expiry(self):
        doc = self._create_document(expiry_date=fields.Date.today() + timedelta(days=90))
        self.assertEqual(doc.state, "valid")

    def test_state_expiring_soon_within_threshold(self):
        doc = self._create_document(expiry_date=fields.Date.today() + timedelta(days=10))
        self.assertEqual(doc.state, "expiring_soon")

    def test_state_expired_in_the_past(self):
        doc = self._create_document(expiry_date=fields.Date.today() - timedelta(days=1))
        self.assertEqual(doc.state, "expired")

    def test_write_expiry_date_updates_state(self):
        doc = self._create_document(expiry_date=fields.Date.today() + timedelta(days=90))
        self.assertEqual(doc.state, "valid")
        doc.expiry_date = fields.Date.today() - timedelta(days=1)
        self.assertEqual(doc.state, "expired")

    def test_has_expired_documents(self):
        self._create_document(expiry_date=fields.Date.today() - timedelta(days=1))
        document_model = self.env["deployfleet.compliance.document"]
        self.assertTrue(document_model.has_expired_documents("deployfleet.vehicle", 1))
        self.assertFalse(document_model.has_expired_documents("deployfleet.vehicle", 2))

    def test_cron_refresh_states_updates_stale_state(self):
        doc = self._create_document(expiry_date=fields.Date.today() + timedelta(days=90))
        # Simulate a state that's gone stale (time passing without a write to this record).
        self.env.cr.execute(
            "UPDATE deployfleet_compliance_document SET expiry_date = %s WHERE id = %s",
            (fields.Date.today() - timedelta(days=1), doc.id),
        )
        doc.invalidate_recordset()
        self.assertEqual(doc.state, "valid")  # stale in-memory value before cron runs
        self.env["deployfleet.compliance.document"]._cron_refresh_states()
        doc.invalidate_recordset()
        self.assertEqual(doc.state, "expired")
