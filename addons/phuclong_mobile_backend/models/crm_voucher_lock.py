# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _, SUPERUSER_ID
from datetime import timedelta

class VoucherLock(models.Model):
    _name = 'crm.voucher.lock'
    _rec_name = 'voucher_code'

    order_id = fields.Many2one(comodel_name='pos.order', string='Order ID')
    order_line_id = fields.Many2one(
        comodel_name='pos.order.line', string='Order Line')
    voucher_code = fields.Char(string='Voucher Code')
    is_coupon_app = fields.Boolean(string='Coupon App')
    is_combo = fields.Boolean(string='Combo')
    is_coupon = fields.Boolean(string='Coupon')
    is_voucher = fields.Boolean(string='Voucher')
    res_model = fields.Char(
        'Related Document Model Name', required=True, index=True)
    res_id = fields.Many2oneReference(
        'Related Document ID', index=True, model_field='res_model')
    discount_amount = fields.Float(string='Discount Amount', default=0.0)
    
    def get_record(self):
        self.ensure_one()
        return self.env[self.res_model].browse(self.res_id)

    def view_record(self):
        self.ensure_one()
        return {
            'name': self.voucher_code,
            'view_mode': 'form',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'type': 'ir.actions.act_window',
        }

    @api.model
    def create(self, values):
        # Add code here
        if values.get('voucher_code', False):
            if values.get('is_coupon_app', False):
                coupon_app_id = self.env['coupon.app'].sudo().search(
                    [('name', '=', values.get('voucher_code'))], limit=1)
                if coupon_app_id:
                    values.update({
                        'res_model': 'coupon.app',
                        'res_id': coupon_app_id.id
                    })
                else:
                    raise
            elif values.get('is_coupon', False) or values.get('is_voucher', False):
                voucher_id = self.env['crm.voucher.info'].sudo().search(
                    [('ean', '=', values.get('voucher_code'))], limit=1)
                if voucher_id:
                    values.update({
                        'res_model': 'crm.voucher.info',
                        'res_id': voucher_id.id
                    })
                else:
                    raise
        return super(VoucherLock, self).create(values)

    def get_start_end_today(self, format_datetime=False):
        to_datetime = fields.Datetime.to_datetime
        today = to_datetime(fields.Date.context_today(self))
        convert_date_datetime_to_utc = self.env['res.users']._convert_date_datetime_to_utc
        start_today, end_today = convert_date_datetime_to_utc(fields.Datetime.to_string(
            today), True), convert_date_datetime_to_utc(fields.Datetime.to_string(today + timedelta(days=1, seconds=-1)), True)
        if format_datetime:
            return to_datetime(start_today), to_datetime(end_today)
        return start_today, end_today
    
    def check_lock_voucher(self, voucher_code):
        start_today, end_today = self.get_start_end_today()
        return self.sudo().search([
            ('voucher_code', '=', voucher_code),
            ('order_id.state', '=', 'draft'),
            ('order_id.date_order', '>=', start_today),
            ('order_id.date_order', '=', end_today),
        ], limit=1)