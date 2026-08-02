from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class DeployfleetZRATestBase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.config = self.env["deployfleet.zra.config"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        self.config.write({
            "base_url": "https://vsdc.example.zm",
            "tpin": "1000000000",
            "device_serial_no": "20180520000000",
        })
        self.customer = self.env["res.partner"].create({"name": "ZRA Customer", "vat": "2000000000"})
        self.shipment = self.env["deployfleet.shipment"].create({
            "customer_id": self.customer.id,
            "pickup_depot_id": self.env["deployfleet.depot"].create({"name": "ZRA Pickup"}).id,
            "dropoff_depot_id": self.env["deployfleet.depot"].create({"name": "ZRA Dropoff"}).id,
            "weight_kg": 500.0,
        })
        self.invoice = self.env["deployfleet.invoice"].create({
            "customer_id": self.customer.id,
            "line_ids": [
                (0, 0, {
                    "shipment_id": self.shipment.id,
                    "description": "Trip charge", "quantity": 1.0, "unit_amount": 1000.0,
                }),
            ],
        })

    def _mock_requests_post(self, json_data):
        mock_response = MagicMock()
        mock_response.json.return_value = json_data
        mock_response.raise_for_status = MagicMock()
        return patch(
            "odoo.addons.deployfleet_zra.models.deployfleet_zra_client.requests"
        ), mock_response


class TestDeployfleetZRAConfig(DeployfleetZRATestBase):
    def test_device_init_stores_key_and_marks_initialized(self):
        patcher, mock_response = self._mock_requests_post({"data": {"apiKey": "TESTKEY123"}})
        with patcher as mock_requests:
            mock_requests.post.return_value = mock_response
            self.config.action_initialize_device()

        self.assertTrue(self.config.initialized)
        self.assertEqual(self.config.device_api_key, "TESTKEY123")


class TestDeployfleetZRAClient(DeployfleetZRATestBase):
    def test_submit_sale_builds_expected_payload(self):
        patcher, mock_response = self._mock_requests_post({"data": {"rcptNo": "R-001"}})
        with patcher as mock_requests:
            mock_requests.post.return_value = mock_response
            payload, response = self.env["deployfleet.zra.client"]._submit_sale(self.config, self.invoice)

        self.assertEqual(payload["tpin"], "1000000000")
        self.assertEqual(payload["custTpin"], "2000000000")
        self.assertEqual(payload["custNm"], "ZRA Customer")
        self.assertEqual(payload["totAmt"], 1000.0)
        self.assertEqual(len(payload["itemList"]), 1)
        self.assertEqual(response["data"]["rcptNo"], "R-001")


class TestDeployfleetZRASubmission(DeployfleetZRATestBase):
    def test_handle_bus_event_creates_and_submits_on_invoice_posted(self):
        patcher, mock_response = self._mock_requests_post({"data": {"rcptNo": "R-002"}})
        with patcher as mock_requests:
            mock_requests.post.return_value = mock_response
            self.env["deployfleet.zra.submission"]._handle_bus_event(
                "deployfleet.invoice.posted", "deployfleet.invoice", self.invoice.id, {}
            )

        submission = self.env["deployfleet.zra.submission"].search([("invoice_id", "=", self.invoice.id)])
        self.assertEqual(len(submission), 1)
        self.assertEqual(submission.state, "accepted")
        self.assertEqual(submission.zra_receipt_no, "R-002")

    def test_unrelated_event_does_not_create_submission(self):
        before = self.env["deployfleet.zra.submission"].search_count([])
        self.env["deployfleet.zra.submission"]._handle_bus_event(
            "deployfleet.trip.completed", "deployfleet.trip", 1, {}
        )
        after = self.env["deployfleet.zra.submission"].search_count([])
        self.assertEqual(before, after)

    def test_submit_records_error_when_no_config_for_company(self):
        self.config.unlink()
        submission = self.env["deployfleet.zra.submission"].create({"invoice_id": self.invoice.id})
        submission.action_submit()
        self.assertEqual(submission.state, "error")
