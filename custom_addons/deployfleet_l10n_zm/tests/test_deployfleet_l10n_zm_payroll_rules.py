from datetime import date

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetL10nZmPayrollRules(TransactionCase):
    def setUp(self):
        super().setUp()
        self.employee = self.env["hr.employee"].create({"name": "ZM Payroll Employee"})

    def _compute_payslip(self, base_salary):
        payslip = self.env["deployfleet.payroll.payslip"].create({
            "employee_id": self.employee.id, "base_salary": base_salary,
            "period_start": date(2026, 1, 1), "period_end": date(2026, 1, 31),
        })
        payslip.action_compute()
        return payslip

    def _line_amount(self, payslip, code):
        return payslip.line_ids.filtered(lambda line: line.rule_id.code == code).amount

    def test_lowest_band_pays_no_paye(self):
        payslip = self._compute_payslip(4000.0)
        self.assertEqual(self._line_amount(payslip, "NAPSA"), 200.0)
        self.assertEqual(self._line_amount(payslip, "NHIMA"), 40.0)
        self.assertEqual(self._line_amount(payslip, "PAYE"), 0.0)
        self.assertEqual(payslip.net_pay, 3760.0)

    def test_second_band(self):
        payslip = self._compute_payslip(6000.0)
        self.assertEqual(self._line_amount(payslip, "PAYE"), 120.0)
        self.assertEqual(payslip.net_pay, 5520.0)

    def test_third_band(self):
        payslip = self._compute_payslip(8000.0)
        self.assertEqual(self._line_amount(payslip, "PAYE"), 550.0)
        self.assertEqual(payslip.net_pay, 6970.0)

    def test_top_band(self):
        payslip = self._compute_payslip(12000.0)
        self.assertEqual(self._line_amount(payslip, "PAYE"), 1855.0)
        self.assertEqual(payslip.net_pay, 9425.0)

    def test_wcf_is_not_a_payslip_line(self):
        payslip = self._compute_payslip(6000.0)
        codes = payslip.line_ids.mapped("rule_id.code")
        self.assertNotIn("WCF", codes)
