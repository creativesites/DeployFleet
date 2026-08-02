from datetime import date

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetPayrollPayslip(TransactionCase):
    def setUp(self):
        super().setUp()
        self.employee = self.env["hr.employee"].create({"name": "Payroll Employee"})
        self.rule_model = self.env["deployfleet.payroll.rule"]
        self.rule_model.create({
            "code": "PENSION", "name": "Pension Contribution", "sequence": 10,
            "category": "deduction", "amount_type": "percentage",
            "amount_percentage": 5.0, "percentage_base_code": "BASIC",
        })

    def _create_payslip(self, base_salary=10000.0):
        return self.env["deployfleet.payroll.payslip"].create({
            "employee_id": self.employee.id, "base_salary": base_salary,
            "period_start": date(2026, 1, 1), "period_end": date(2026, 1, 31),
        })

    def test_compute_creates_one_line_per_active_rule(self):
        payslip = self._create_payslip()
        payslip.action_compute()
        self.assertEqual(len(payslip.line_ids), 1)

    def test_percentage_rule_computed_against_base_salary(self):
        payslip = self._create_payslip()
        payslip.action_compute()
        pension_line = payslip.line_ids.filtered(lambda line: line.rule_id.code == "PENSION")
        self.assertEqual(pension_line.amount, 500.0)

    def test_different_employees_can_have_different_base_salaries(self):
        low = self._create_payslip(base_salary=8000.0)
        high = self._create_payslip(base_salary=20000.0)
        low.action_compute()
        high.action_compute()
        self.assertEqual(
            low.line_ids.filtered(lambda line: line.rule_id.code == "PENSION").amount, 400.0,
        )
        self.assertEqual(
            high.line_ids.filtered(lambda line: line.rule_id.code == "PENSION").amount, 1000.0,
        )

    def test_gross_and_net_totals(self):
        payslip = self._create_payslip()
        payslip.action_compute()
        self.assertEqual(payslip.gross_pay, 10000.0)
        self.assertEqual(payslip.total_deductions, 500.0)
        self.assertEqual(payslip.net_pay, 9500.0)

    def test_formula_rule_references_basic_and_earlier_rules(self):
        self.rule_model.create({
            "code": "TAKE_HOME", "name": "Take Home (formula check)", "sequence": 20,
            "category": "gross", "amount_type": "formula", "formula": "BASIC - PENSION",
        })
        payslip = self._create_payslip()
        payslip.action_compute()
        take_home_line = payslip.line_ids.filtered(lambda line: line.rule_id.code == "TAKE_HOME")
        self.assertEqual(take_home_line.amount, 9500.0)

    def test_inactive_rule_is_excluded(self):
        self.rule_model.create({
            "code": "BONUS", "name": "Bonus", "category": "gross", "amount_type": "fixed",
            "amount_fixed": 1000.0, "active": False,
        })
        payslip = self._create_payslip()
        payslip.action_compute()
        self.assertFalse(payslip.line_ids.filtered(lambda line: line.rule_id.code == "BONUS"))

    def test_full_workflow(self):
        payslip = self._create_payslip()
        payslip.action_compute()
        self.assertEqual(payslip.state, "computed")
        payslip.action_confirm()
        self.assertEqual(payslip.state, "confirmed")
        payslip.action_mark_paid()
        self.assertEqual(payslip.state, "paid")

    def test_cannot_confirm_before_computing(self):
        payslip = self._create_payslip()
        with self.assertRaises(UserError):
            payslip.action_confirm()

    def test_cannot_recompute_a_confirmed_payslip(self):
        payslip = self._create_payslip()
        payslip.action_compute()
        payslip.action_confirm()
        with self.assertRaises(UserError):
            payslip.action_compute()
