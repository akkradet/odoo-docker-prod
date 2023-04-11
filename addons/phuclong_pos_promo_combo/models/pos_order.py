# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class pos_order_line(models.Model):
    _inherit = 'pos.order.line'

    combo_id = fields.Many2one('sale.promo.combo', 'Combo')
    is_done_combo = fields.Boolean('Is done combo')
    combo_seq = fields.Char('Combo sequence')
    combo_qty = fields.Char('Combo Qty')
