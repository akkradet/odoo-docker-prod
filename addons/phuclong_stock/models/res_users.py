# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.tools.safe_eval import safe_eval


class ResUsers(models.Model):
    _inherit = "res.users"

    def _warehouses_worker_domain(self):
        domain = "[]"
        if self.id == SUPERUSER_ID:
            return False
        if self.warehouses_dom:
            domain = safe_eval(self.warehouses_dom)
        return domain
