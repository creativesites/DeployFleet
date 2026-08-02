from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class DeployfleetBillingTestBase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.customer = self.env["res.partner"].create({"name": "Billing Customer"})
        self.pickup = self.env["deployfleet.depot"].create({"name": "Billing Pickup"})
        self.dropoff = self.env["deployfleet.depot"].create({"name": "Billing Dropoff"})
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = self.env["fleet.vehicle.model.brand"].create({"name": "Billing Brand"})
            model = self.env["fleet.vehicle.model"].create({"name": "Billing Model", "brand_id": brand.id})
        self.vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "BILL-001", "model_id": model.id, "status": "available",
        })
        self.driver = self.env["hr.employee"].create({"name": "Billing Driver", "deployfleet_is_driver": True})
        self.contract = self.env["deployfleet.contract"].create({
            "customer_id": self.customer.id, "rate_basis": "per_trip",
        })

    def _create_shipment(self, weight_kg=500.0, with_contract=True):
        return self.env["deployfleet.shipment"].create({
            "customer_id": self.customer.id,
            "pickup_depot_id": self.pickup.id,
            "dropoff_depot_id": self.dropoff.id,
            "weight_kg": weight_kg,
            "contract_id": self.contract.id if with_contract else False,
        })

    def _complete_a_trip_for(self, shipment):
        [assignment] = shipment.action_suggest_assignments(limit=1)
        assignment.action_confirm()
        trip = self.env["deployfleet.trip"].search([("dispatch_assignment_id", "=", assignment.id)])
        trip.action_depart()
        trip.action_complete()
        return trip


class TestDeployfleetRateCard(DeployfleetBillingTestBase):
    def test_rate_card_requires_positive_amount(self):
        with self.assertRaises(ValidationError):
            self.env["deployfleet.rate.card"].create({
                "contract_id": self.contract.id, "unit_amount": 0.0,
            })

    def test_rate_card_mirrors_contract_rate_basis(self):
        rate_card = self.env["deployfleet.rate.card"].create({
            "contract_id": self.contract.id, "unit_amount": 1500.0,
        })
        self.assertEqual(rate_card.rate_basis, "per_trip")

    def test_get_rate_prefers_vehicle_type_specific(self):
        vehicle_type = self.env["deployfleet.vehicle.type"].search([], limit=1)
        general_rate = self.env["deployfleet.rate.card"].create({
            "contract_id": self.contract.id, "unit_amount": 1000.0,
        })
        if vehicle_type:
            scoped_rate = self.env["deployfleet.rate.card"].create({
                "contract_id": self.contract.id, "unit_amount": 2000.0, "vehicle_type_id": vehicle_type.id,
            })
            found = self.env["deployfleet.rate.card"]._get_rate(self.contract, vehicle_type)
            self.assertEqual(found, scoped_rate)
        found_generic = self.env["deployfleet.rate.card"]._get_rate(self.contract, None)
        self.assertEqual(found_generic, general_rate)


class TestDeployfleetInvoice(DeployfleetBillingTestBase):
    def test_confirm_requires_lines(self):
        invoice = self.env["deployfleet.invoice"].create({"customer_id": self.customer.id})
        with self.assertRaises(UserError):
            invoice.action_confirm()

    def test_amount_total_sums_line_subtotals(self):
        invoice = self.env["deployfleet.invoice"].create({
            "customer_id": self.customer.id,
            "line_ids": [
                (0, 0, {
                    "shipment_id": self._create_shipment().id,
                    "description": "Line 1", "quantity": 2.0, "unit_amount": 100.0,
                }),
            ],
        })
        self.assertEqual(invoice.amount_total, 200.0)

    def test_confirm_registers_event(self):
        invoice = self.env["deployfleet.invoice"].create({
            "customer_id": self.customer.id,
            "line_ids": [
                (0, 0, {
                    "shipment_id": self._create_shipment().id,
                    "description": "Line 1", "quantity": 1.0, "unit_amount": 500.0,
                }),
            ],
        })
        before = self.env["deployfleet.event.log"].search_count([
            ("name", "=", "deployfleet.invoice.confirmed"),
        ])
        invoice.action_confirm()
        after = self.env["deployfleet.event.log"].search_count([
            ("name", "=", "deployfleet.invoice.confirmed"),
        ])
        self.assertEqual(after, before + 1)


class TestDeployfleetInvoiceGeneration(DeployfleetBillingTestBase):
    def test_trip_completion_generates_invoice_when_contract_and_rate_card_exist(self):
        self.env["deployfleet.rate.card"].create({
            "contract_id": self.contract.id, "unit_amount": 1500.0,
        })
        shipment = self._create_shipment()
        self._complete_a_trip_for(shipment)

        invoice = self.env["deployfleet.invoice"].search([("customer_id", "=", self.customer.id)])
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.state, "draft")
        self.assertEqual(invoice.amount_total, 1500.0)

    def test_trip_completion_skips_invoice_without_contract(self):
        shipment = self._create_shipment(with_contract=False)
        self._complete_a_trip_for(shipment)
        invoices = self.env["deployfleet.invoice"].search([("customer_id", "=", self.customer.id)])
        self.assertFalse(invoices)

    def test_per_tonnage_rate_uses_shipment_weight_as_quantity(self):
        self.contract.rate_basis = "per_tonnage"
        self.env["deployfleet.rate.card"].create({
            "contract_id": self.contract.id, "unit_amount": 2.0,
        })
        shipment = self._create_shipment(weight_kg=800.0)
        self._complete_a_trip_for(shipment)

        invoice = self.env["deployfleet.invoice"].search([("customer_id", "=", self.customer.id)])
        self.assertEqual(invoice.amount_total, 1600.0)
