from datetime import date

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetDriverPerformanceEvent(TransactionCase):
    def setUp(self):
        super().setUp()
        self.driver = self.env["hr.employee"].create({"name": "Perf Driver", "deployfleet_is_driver": True})

    def test_onchange_suggests_score_impact(self):
        event = self.env["deployfleet.driver.performance.event"].new({
            "driver_id": self.driver.id, "event_type": "accident",
        })
        event._onchange_event_type_suggest_score_impact()
        self.assertEqual(event.score_impact, -20.0)

    def test_reliability_score_starts_at_100(self):
        self.assertEqual(self.driver.deployfleet_reliability_score, 100.0)

    def test_reliability_score_decreases_with_events(self):
        self.env["deployfleet.driver.performance.event"].create({
            "driver_id": self.driver.id, "event_type": "speeding", "score_impact": -5.0,
        })
        self.env["deployfleet.driver.performance.event"].create({
            "driver_id": self.driver.id, "event_type": "harsh_braking", "score_impact": -2.0,
        })
        self.assertEqual(self.driver.deployfleet_reliability_score, 93.0)

    def test_reliability_score_floors_at_zero(self):
        self.env["deployfleet.driver.performance.event"].create({
            "driver_id": self.driver.id, "event_type": "accident", "score_impact": -150.0,
        })
        self.assertEqual(self.driver.deployfleet_reliability_score, 0.0)

    def test_old_events_outside_trailing_window_do_not_count(self):
        self.env["deployfleet.driver.performance.event"].create({
            "driver_id": self.driver.id, "event_type": "accident", "score_impact": -20.0,
            "date": date(2020, 1, 1),
        })
        self.assertEqual(self.driver.deployfleet_reliability_score, 100.0)


@tagged("post_install", "-at_install")
class TestDeployfleetDriverPerformancePayrollDeduction(TransactionCase):
    def setUp(self):
        super().setUp()
        self.driver = self.env["hr.employee"].create({"name": "Perf Payroll Driver", "deployfleet_is_driver": True})

    def _create_payslip(self, base_salary=10000.0):
        return self.env["deployfleet.payroll.payslip"].create({
            "employee_id": self.driver.id, "base_salary": base_salary,
            "period_start": date(2026, 1, 1), "period_end": date(2026, 1, 31),
        })

    def test_event_with_deduction_creates_payslip_line(self):
        self.env["deployfleet.driver.performance.event"].create({
            "driver_id": self.driver.id, "event_type": "accident",
            "date": date(2026, 1, 15), "payroll_deduction_amount": 300.0,
        })
        payslip = self._create_payslip()
        payslip.action_compute()
        line = payslip.line_ids.filtered(lambda line: line.rule_id.code == "DRIVER_PERF")
        self.assertEqual(line.amount, 300.0)

    def test_event_without_deduction_has_no_line(self):
        self.env["deployfleet.driver.performance.event"].create({
            "driver_id": self.driver.id, "event_type": "harsh_braking", "date": date(2026, 1, 15),
        })
        payslip = self._create_payslip()
        payslip.action_compute()
        self.assertFalse(payslip.line_ids.filtered(lambda line: line.rule_id.code == "DRIVER_PERF"))

    def test_confirm_marks_event_applied_and_excludes_from_next_period(self):
        event = self.env["deployfleet.driver.performance.event"].create({
            "driver_id": self.driver.id, "event_type": "accident",
            "date": date(2026, 1, 15), "payroll_deduction_amount": 300.0,
        })
        payslip = self._create_payslip()
        payslip.action_compute()
        payslip.action_confirm()
        self.assertTrue(event.payroll_deduction_applied)

        next_payslip = self.env["deployfleet.payroll.payslip"].create({
            "employee_id": self.driver.id, "base_salary": 10000.0,
            "period_start": date(2026, 2, 1), "period_end": date(2026, 2, 28),
        })
        next_payslip.action_compute()
        self.assertFalse(next_payslip.line_ids.filtered(lambda line: line.rule_id.code == "DRIVER_PERF"))
