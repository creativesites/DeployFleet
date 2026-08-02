from unittest.mock import MagicMock, patch

from odoo.tests import HttpCase, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestDeployfleetAIWhatsappMessageHandling(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env["deployfleet.ai.whatsapp.config"].create({
            "phone_number_id": "1234567890",
            "access_token": "test-token",
            "webhook_verify_token": "test-verify-token",
        })
        cls.driver = cls.env["hr.employee"].create({
            "name": "WhatsApp Driver", "deployfleet_is_driver": True, "mobile_phone": "+260971234567",
        })
        model = cls.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = cls.env["fleet.vehicle.model.brand"].create({"name": "WhatsApp Brand"})
            model = cls.env["fleet.vehicle.model"].create({"name": "WhatsApp Model", "brand_id": brand.id})
        cls.vehicle = cls.env["deployfleet.vehicle"].create({
            "license_plate": "WA-001", "model_id": model.id,
            "status": "assigned", "current_driver_id": cls.driver.id,
        })

    def _handle(self, phone, text):
        with patch(
            "odoo.addons.deployfleet_ai_whatsapp.models.deployfleet_ai_action_request.requests"
        ) as mock_requests:
            mock_requests.post.return_value = MagicMock()
            result = self.env["deployfleet.ai.action.request"]._handle_whatsapp_message(
                self.config, phone, text
            )
            return result, mock_requests

    def test_breakdown_message_creates_pending_request_never_executed(self):
        request, mock_requests = self._handle("260971234567", "Help, my truck has a breakdown")
        self.assertTrue(request)
        self.assertEqual(request.state, "pending_approval")
        self.assertEqual(request.target_model, "deployfleet.vehicle")
        self.assertEqual(request.target_id, self.vehicle.id)
        self.assertEqual(request.source_context, "whatsapp_message")
        mock_requests.post.assert_called_once()
        # The pipeline must never auto-execute: the vehicle's actual status
        # is untouched until a manager calls action_approve().
        self.assertEqual(self.vehicle.status, "assigned")

    def test_non_breakdown_message_creates_no_request(self):
        before = self.env["deployfleet.ai.action.request"].search_count([])
        request, mock_requests = self._handle("260971234567", "What time is my next trip?")
        self.assertIsNone(request)
        after = self.env["deployfleet.ai.action.request"].search_count([])
        self.assertEqual(before, after)
        mock_requests.post.assert_not_called()

    def test_unmatched_phone_sends_fallback_and_creates_no_request(self):
        before = self.env["deployfleet.ai.action.request"].search_count([])
        request, mock_requests = self._handle("15551234567", "breakdown please help")
        self.assertIsNone(request)
        after = self.env["deployfleet.ai.action.request"].search_count([])
        self.assertEqual(before, after)
        mock_requests.post.assert_called_once()

    def test_driver_without_vehicle_sends_fallback_and_creates_no_request(self):
        unassigned_driver = self.env["hr.employee"].create({
            "name": "Unassigned Driver", "deployfleet_is_driver": True, "mobile_phone": "+260979999999",
        })
        before = self.env["deployfleet.ai.action.request"].search_count([])
        request, mock_requests = self._handle("260979999999", "breakdown on the highway")
        self.assertIsNone(request)
        after = self.env["deployfleet.ai.action.request"].search_count([])
        self.assertEqual(before, after)
        mock_requests.post.assert_called_once()
        self.assertTrue(unassigned_driver.deployfleet_is_driver)


@tagged("post_install", "-at_install")
class TestDeployfleetAIWhatsappWebhookVerification(HttpCase):
    def setUp(self):
        super().setUp()
        self.env["deployfleet.ai.whatsapp.config"].create({
            "phone_number_id": "1234567890", "access_token": "test-token",
            "webhook_verify_token": "correct-token",
        })

    def test_verification_succeeds_with_correct_token(self):
        response = self.url_open(
            "/api/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=correct-token&hub.challenge=xyz123"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "xyz123")

    def test_verification_fails_with_wrong_token(self):
        response = self.url_open(
            "/api/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=wrong-token&hub.challenge=xyz123"
        )
        self.assertEqual(response.status_code, 403)
