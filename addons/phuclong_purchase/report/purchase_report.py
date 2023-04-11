# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    date_planned = fields.Datetime(string='Receipt Date', )

    def _select(self):
        res = super(PurchaseReport, self)._select()
        res += ",po.date_planned"
        return res

    def _group_by(self):
        res = super(PurchaseReport, self)._group_by()
        res += ",po.date_planned"
        return res
