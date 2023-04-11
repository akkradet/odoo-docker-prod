# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class CrmVoucherInfo(models.Model):
    _inherit = "crm.voucher.info"

    pos_order_id = fields.Many2one('pos.order', string='Pos Order',
                                   compute='_compute_pos_order_id', compute_sudo=True, store=True)
    date_used = fields.Date(
        string='Date Used', compute='_compute_date_used', store=True)
    product_coupon_order_ref = fields.Char()

    def action_reset_voucher(self):
        for rec in self:
            rec._compute_pos_order_id()
            if rec.type == 'voucher' and rec.state == 'Close' and rec.order_reference and not rec.pos_order_id and rec.used_count > 0:
                rec.write({
                    'used_count': 0,
                    'state': 'Create',
                    'order_reference': False
                })

    @api.depends('order_reference')
    def _compute_pos_order_id(self):
        for rec in self:
            pos_order_id = False
            if rec.order_reference:
                pos_order_id = self.env['pos.order'].sudo().search(
                    [('pos_reference', '=', rec.order_reference)], limit=1)
            rec.pos_order_id = pos_order_id

    @api.depends('pos_order_id')
    def _compute_date_used(self):
        context_timestamp = fields.Datetime.context_timestamp
        for rec in self:
            date_used = False
            if rec.pos_order_id and rec.pos_order_id.date_order:
                date_used = context_timestamp(
                    rec, rec.pos_order_id.date_order).date()
            rec.date_used = date_used
