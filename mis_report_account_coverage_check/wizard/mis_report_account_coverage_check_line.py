# Copyright 2026 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class MisReportAccountCoverageCheckLine(models.TransientModel):
    _name = "mis.report.account.coverage.check.line"
    _description = "Uncovered account found during a MIS report coverage check"

    check_id = fields.Many2one(
        comodel_name="mis.report.account.coverage.check",
        required=True,
        ondelete="cascade",
    )
    period_id = fields.Many2one(
        comodel_name="mis.report.instance.period", string="Period", required=True
    )
    account_id = fields.Many2one(
        comodel_name="account.account", string="Account", required=True
    )
    account_code = fields.Char(related="account_id.code")
    account_name = fields.Char(related="account_id.name")
    currency_id = fields.Many2one(related="account_id.company_id.currency_id")
    debit = fields.Monetary(currency_field="currency_id")
    credit = fields.Monetary(currency_field="currency_id")
    balance = fields.Monetary(currency_field="currency_id")
    move_line_count = fields.Integer(string="Journal Items")

    def action_view_move_lines(self):
        self.ensure_one()
        instance = self.check_id.report_instance_id
        aml_model_name = instance.report_id.sudo().move_lines_source.model
        domain = [
            ("account_id", "=", self.account_id.id),
            ("date", ">=", self.period_id.date_from),
            ("date", "<=", self.period_id.date_to),
            ("company_id", "in", instance.query_company_ids.ids),
        ]
        domain += self.period_id._get_additional_move_line_filter()
        return {
            "name": self.account_id.display_name,
            "type": "ir.actions.act_window",
            "res_model": aml_model_name,
            "domain": domain,
            "views": [[False, "list"], [False, "form"]],
            "view_mode": "list",
            "target": "current",
            "context": {"active_test": False},
        }
