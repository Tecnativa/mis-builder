# coding: utf-8
# Copyright 2018 Tecnativa - Pedro M. Baeza
from odoo import models
from odoo.tools import ormcache


class AccountGroup(models.Model):
    _inherit = "account.group"

    @ormcache('self', 'level')
    def _get_group_by_level(self, level):
        if self.level > level:
            return self.parent_id._get_group_by_level(level)
        return self
