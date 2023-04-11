# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _, SUPERUSER_ID
from datetime import timedelta

class POSOrder(models.Model):
    _inherit = 'pos.order'

    order_in_app = fields.Boolean('Order in App', default=False)
    description_for_app = fields.Text('Order App Description', default='')
    delivery_address_note = fields.Text('Delivery Note', default='')
    # shipping_fee = fields.Integer('Shipping Fee')
    order_status_app = fields.Selection([('new', 'New'),
                                         ('done', 'Done'),
                                         ('cancel', 'Cancel')], string="Status Mobile")
    delivery_address = fields.Text(string="Delivery Address")
    name_receiver = fields.Char('Name Receiver')
    phone_number_receiver = fields.Char('Phone Number Receiver')
    amount_voucher = fields.Float(string='Amount Voucher', default=0.0)
    address_id = fields.Many2one(comodel_name='res.partner', string='Address')
    voucher_lock_ids = fields.One2many(
        comodel_name='crm.voucher.lock', inverse_name='order_id', string='Voucher Data')

    payoo_request = fields.Text()
    payoo_request_ip = fields.Char()
    payoo_checksum = fields.Text()
    payoo_response = fields.Text()

    def notification_pos(self):
        return True

    def cron_delete_order_draft_mobile(self, log=False):
        try:
            sale_type_ids = self.env['pos.sale.type'].search(
                [('use_for_app', '=', True)])
            self._cr.execute('''
                delete from pos_order where state = 'draft' and order_status_app = 'new' and sale_type_id in (%s) and order_in_app = True;
                delete from crm_voucher_lock;
            ''' % (','.join(map(str, sale_type_ids.ids))))
        except Exception as e:
            if log:
                log(e)

    def cancel_order(self):
        result = super(POSOrder, self).cancel_order()
        if self._context.get('cancel_from_wizard', False):
            is_clear_coupon_code = False
            lines = self.mapped('lines').filtered(lambda l: l.coupon_app_id)
            if lines:
                is_clear_coupon_code = True
                lines.write({'coupon_app_id': False})
            if is_clear_coupon_code:
                self.write({'coupon_code': ''})
        return result


class POSOrderLine(models.Model):
    _inherit = 'pos.order.line'

    coupon_app_id = fields.Many2one(
        comodel_name='coupon.app', string='Coupon App')
