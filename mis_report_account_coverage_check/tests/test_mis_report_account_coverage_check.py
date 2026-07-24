# Copyright 2026 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import datetime

from odoo import fields
from odoo.tests import common


class TestMisReportAccountCoverageCheck(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        type_ar = self.browse_ref("account.data_account_type_receivable")
        type_in = self.browse_ref("account.data_account_type_revenue")
        self.account_ar = self.env["account.account"].create(
            {
                "company_id": self.company.id,
                "code": "400AR",
                "name": "Receivable",
                "user_type_id": type_ar.id,
                "reconcile": True,
            }
        )
        self.account_uncovered = self.env["account.account"].create(
            {
                "company_id": self.company.id,
                "code": "500UN",
                "name": "Uncovered account",
                "user_type_id": type_in.id,
            }
        )
        self.account_in = self.env["account.account"].create(
            {
                "company_id": self.company.id,
                "code": "700IN",
                "name": "Income",
                "user_type_id": type_in.id,
            }
        )
        self.account_out_of_range = self.env["account.account"].create(
            {
                "company_id": self.company.id,
                "code": "900OU",
                "name": "Out of range account",
                "user_type_id": type_in.id,
            }
        )
        self.journal = self.env["account.journal"].create(
            {
                "company_id": self.company.id,
                "name": "Sale journal",
                "code": "VEN",
                "type": "sale",
            }
        )
        self.date_from = datetime.date.today().replace(day=1)
        next_month = self.date_from.replace(day=28) + datetime.timedelta(days=4)
        self.date_to = next_month - datetime.timedelta(days=next_month.day)
        # covered postings: only account_ar/account_in appear in the KPI expr
        self._create_move(self.account_ar, self.account_in, 100)
        # uncovered-but-used posting, in range: must be detected
        self._create_move(self.account_ar, self.account_uncovered, 50)
        # posting on an out-of-range account: must never be detected
        self._create_move(self.account_ar, self.account_out_of_range, 20)

        self.report = self.env["mis.report"].create({"name": "Test report"})
        self.env["mis.report.kpi"].create(
            {
                "report_id": self.report.id,
                "name": "balance",
                "description": "Balance",
                "expression_ids": [(0, 0, {"name": "balp[400AR,700IN]"})],
            }
        )
        self.instance = self.env["mis.report.instance"].create(
            {
                "name": "Test instance",
                "report_id": self.report.id,
                "company_id": self.company.id,
                "date_from": fields.Date.to_string(self.date_from),
                "date_to": fields.Date.to_string(self.date_to),
                "period_ids": [(0, 0, {"name": "Default"})],
            }
        )

    def _create_move(self, debit_account, credit_account, amount):
        move = self.env["account.move"].create(
            {
                "journal_id": self.journal.id,
                "date": fields.Date.to_string(self.date_from),
                "line_ids": [
                    (
                        0,
                        0,
                        {"name": "/", "debit": amount, "account_id": debit_account.id},
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "/",
                            "credit": amount,
                            "account_id": credit_account.id,
                        },
                    ),
                ],
            }
        )
        move._post()
        return move

    def _create_wizard(self):
        return self.env["mis.report.account.coverage.check"].create(
            {
                "report_instance_id": self.instance.id,
                "account_code_from": "400AR",
                "account_code_to": "700IN",
            }
        )

    def test_uncovered_account_detected(self):
        wizard = self._create_wizard()
        wizard.action_check()
        self.assertEqual(wizard.state, "done")
        self.assertEqual(len(wizard.line_ids), 1)
        line = wizard.line_ids
        self.assertEqual(line.account_id, self.account_uncovered)
        self.assertEqual(line.debit, 0)
        self.assertEqual(line.credit, 50)
        self.assertEqual(line.balance, -50)

    def test_covered_accounts_not_listed(self):
        wizard = self._create_wizard()
        wizard.action_check()
        result_accounts = wizard.line_ids.mapped("account_id")
        self.assertNotIn(self.account_ar, result_accounts)
        self.assertNotIn(self.account_in, result_accounts)

    def test_out_of_range_account_not_listed(self):
        wizard = self._create_wizard()
        wizard.action_check()
        self.assertNotIn(
            self.account_out_of_range, wizard.line_ids.mapped("account_id")
        )

    def test_view_move_lines_action_domain(self):
        wizard = self._create_wizard()
        wizard.action_check()
        line = wizard.line_ids
        action = line.action_view_move_lines()
        move_lines = self.env[action["res_model"]].search(action["domain"])
        self.assertTrue(move_lines)
        self.assertEqual(
            set(move_lines.mapped("account_id.id")), {self.account_uncovered.id}
        )

    def test_action_back_resets_state(self):
        wizard = self._create_wizard()
        wizard.action_check()
        wizard.action_back()
        self.assertEqual(wizard.state, "init")
        self.assertFalse(wizard.line_ids)
