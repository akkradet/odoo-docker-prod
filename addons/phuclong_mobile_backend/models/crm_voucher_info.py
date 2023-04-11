# -*- coding: utf-8 -*-

from odoo import api, fields, models


class VoucherInfo(models.Model):
    _inherit = 'crm.voucher.info'

    used_on = fields.Selection(string='Used on', selection=[(
        'pos', 'POS'), ('mobile', 'Mobile App')], compute='_compute_used_on', store=True)

    @api.depends('pos_order_id')
    def _compute_used_on(self):
        for rec in self:
            if rec.pos_order_id:
                rec.used_on = rec.pos_order_id and rec.pos_order_id.order_in_app and 'mobile' or 'pos'
            else:
                rec.used_on = False
