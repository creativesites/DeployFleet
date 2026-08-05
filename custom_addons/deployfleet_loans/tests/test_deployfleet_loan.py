from datetime import date

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetLoan(TransactionCase):
    def setUp(self):
        super().setUp()
        self.employee = self.env["hr.employee"].create({"name": "Loan Employee"})

    def _create_payslip(self, base_salary=10000.0):
        return self.env["deployfleet.payroll.payslip"].create({
            "employee_id": self.employee.id, "base_salary": base_salary,
            "period_start": date(2026, 1, 1), "period_end": date(2026, 1, 31),
        })

    def test_loan_defaults_outstanding_balance_to_amount(self):
        loan = self.env["deployfleet.loan"].create({
            "employee_id": self.employee.id, "amount": 3000.0, "monthly_deduction": 500.0,
        })
        self.assertEqual(loan.outstanding_balance, 3000.0)
        self.assertEqual(loan.state, "active")

    def test_payslip_compute_adds_loan_deduction_line(self):
        self.env["deployfleet.loan"].create({
            "employee_id": self.employee.id, "amount": 3000.0, "monthly_deduction": 500.0,
        })
        payslip = self._create_payslip()
        payslip.action_compute()
        loan_line = payslip.line_ids.filtered(lambda line: line.rule_id.code == "LOAN")
        self.assertEqual(loan_line.amount, 500.0)
        self.assertEqual(payslip.net_pay, 9500.0)

    def test_recompute_does_not_duplicate_or_drain_balance(self):
        loan = self.env["deployfleet.loan"].create({
            "employee_id": self.employee.id, "amount": 3000.0, "monthly_deduction": 500.0,
        })
        payslip = self._create_payslip()
        payslip.action_compute()
        payslip.action_compute()
        loan_lines = payslip.line_ids.filtered(lambda line: line.rule_id.code == "LOAN")
        self.assertEqual(len(loan_lines), 1)
        self.assertEqual(loan.outstanding_balance, 3000.0)

    def test_confirm_applies_deduction_to_balance(self):
        loan = self.env["deployfleet.loan"].create({
            "employee_id": self.employee.id, "amount": 3000.0, "monthly_deduction": 500.0,
        })
        payslip = self._create_payslip()
        payslip.action_compute()
        payslip.action_confirm()
        self.assertEqual(loan.outstanding_balance, 2500.0)

    def test_final_deduction_closes_loan_and_caps_amount(self):
        loan = self.env["deployfleet.loan"].create({
            "employee_id": self.employee.id, "amount": 300.0, "monthly_deduction": 500.0,
        })
        payslip = self._create_payslip()
        payslip.action_compute()
        loan_line = payslip.line_ids.filtered(lambda line: line.rule_id.code == "LOAN")
        self.assertEqual(loan_line.amount, 300.0)
        payslip.action_confirm()
        self.assertEqual(loan.outstanding_balance, 0.0)
        self.assertEqual(loan.state, "closed")

    def test_closed_loan_no_longer_deducted(self):
        loan = self.env["deployfleet.loan"].create({
            "employee_id": self.employee.id, "amount": 300.0, "monthly_deduction": 500.0,
        })
        first = self._create_payslip()
        first.action_compute()
        first.action_confirm()
        self.assertEqual(loan.state, "closed")

        second = self._create_payslip()
        second.action_compute()
        self.assertFalse(second.line_ids.filtered(lambda line: line.rule_id.code == "LOAN"))

    def test_dispatcher_cannot_read_loans(self):
        # Regression test for an engineering-audit finding: this ACL
        # previously granted the dispatcher group perm_read=1, contrary
        # to this project's own documented "zero ACL rows outside
        # group_deployfleet_hr_payroll_officer" design for payroll-
        # adjacent data. Since group_deployfleet_manager/owner do NOT
        # imply hr_payroll_officer (only the owner gets it, via an
        # explicit separate implied_ids grant), an ordinary dispatcher
        # must get AccessError, not a result set.
        loan = self.env["deployfleet.loan"].create({
            "employee_id": self.employee.id, "amount": 3000.0, "monthly_deduction": 500.0,
        })
        dispatcher_group = self.env.ref("deployfleet_security.group_deployfleet_dispatcher")
        dispatcher_user = self.env["res.users"].create({
            "name": "Loan Dispatcher User", "login": "loan_dispatcher_user@example.com",
            "email": "loan_dispatcher_user@example.com", "group_ids": [(6, 0, [dispatcher_group.id])],
        })
        with self.assertRaises(AccessError):
            loan.with_user(dispatcher_user).read(["amount"])
