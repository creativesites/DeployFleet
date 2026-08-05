from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetWorkshopJobCard(TransactionCase):
    def setUp(self):
        super().setUp()
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = self.env["fleet.vehicle.model.brand"].create({"name": "Test Brand"})
            model = self.env["fleet.vehicle.model"].create({"name": "Test Model", "brand_id": brand.id})
        self.vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "JOB-001", "model_id": model.id, "status": "available",
        })
        self.part = self.env["deployfleet.part"].create({"name": "Oil Filter", "quantity_on_hand": 10.0})

    def test_job_card_gets_auto_reference(self):
        job_card = self.env["deployfleet.workshop.job.card"].create({"vehicle_id": self.vehicle.id})
        self.assertTrue(job_card.name.startswith("JOB"))

    def test_full_workflow_consumes_parts_and_frees_vehicle(self):
        job_card = self.env["deployfleet.workshop.job.card"].create({"vehicle_id": self.vehicle.id})
        job_card.action_start_diagnosis()
        job_card.action_start_repair()
        self.assertEqual(self.vehicle.status, "maintenance")

        self.env["deployfleet.workshop.job.line"].create({
            "job_card_id": job_card.id, "line_type": "part", "part_id": self.part.id,
            "quantity": 2.0, "unit_cost": 50.0,
        })
        self.env["deployfleet.workshop.job.line"].create({
            "job_card_id": job_card.id, "line_type": "labor", "description": "Oil change labor",
            "quantity": 1.0, "unit_cost": 100.0,
        })
        self.assertEqual(job_card.total_cost, 200.0)

        job_card.action_submit_for_approval()
        job_card.action_close()

        self.assertEqual(job_card.state, "closed")
        self.assertEqual(self.part.quantity_on_hand, 8.0)
        self.assertEqual(self.vehicle.status, "available")
        self.assertTrue(job_card.closed_date)

    def test_cannot_skip_states(self):
        job_card = self.env["deployfleet.workshop.job.card"].create({"vehicle_id": self.vehicle.id})
        with self.assertRaises(UserError):
            job_card.action_start_repair()

    def test_part_line_requires_part(self):
        job_card = self.env["deployfleet.workshop.job.card"].create({"vehicle_id": self.vehicle.id})
        with self.assertRaises(ValidationError):
            self.env["deployfleet.workshop.job.line"].create({
                "job_card_id": job_card.id, "line_type": "part", "quantity": 1.0,
            })

    def test_closing_one_job_card_does_not_free_vehicle_while_another_is_still_open(self):
        """Regression test for an engineering-audit finding (C-13):
        action_close() previously marked the vehicle available
        unconditionally, even if a second, unrelated job card on the
        SAME vehicle was still open - closing the first one silently
        released the vehicle back into dispatch rotation while a second
        repair was still in progress."""
        first = self.env["deployfleet.workshop.job.card"].create({"vehicle_id": self.vehicle.id})
        second = self.env["deployfleet.workshop.job.card"].create({"vehicle_id": self.vehicle.id})
        for job_card in (first, second):
            job_card.action_start_diagnosis()
            job_card.action_start_repair()
            job_card.action_submit_for_approval()

        first.action_close()
        self.assertEqual(first.state, "closed")
        self.assertEqual(self.vehicle.status, "maintenance")

        second.action_close()
        self.assertEqual(second.state, "closed")
        self.assertEqual(self.vehicle.status, "available")
