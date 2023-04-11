# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import safe_eval


class WizardModifyPayment(models.TransientModel):
    _inherit = 'wizard.modify.payment'

    voucher_list = fields.Char(string="Voucher List")
#     is_delete = fields.Boolean(compute='_is_delete')
     
#     @api.depends('payment_line_ids', 'order_id')
#     def _is_delete(self):
#         is_delete = False
#         order = self.env['pos.order'].browse(self.order_id)
#         current_payment_ids = order.payment_ids
#         payments_to_delete = current_payment_ids.filtered(
#                 lambda l: l.id not in [
#                 x.payment_line_id for x in self.payment_line_ids])
#         if len(payments_to_delete):
#             is_delete = True
#         self.is_delete = is_delete

    @api.model
    def default_get(self, fields):
        res = super(WizardModifyPayment, self).default_get(fields)
        active_id = self._context.get('active_id')
        order = self.env['pos.order'].browse(active_id)
        payment_ids = []
        voucher_list = []
        for payment in order.payment_ids:
            vals = {'payment_method_id': payment.payment_method_id.id,
                    'payment_line_id': payment.id,
                    'amount': payment.amount,
                    'voucher_code': payment.voucher_code}
            if payment.voucher_code:
                voucher_list.append(payment.id)
                vals.update({'voucher_code': payment.voucher_code})
            payment_id = self.env['wizard.modify.payment.line'].create(vals)
            payment_ids.append(payment_id.id)
        res['payment_line_ids'] = payment_ids
        res['voucher_list'] = "[%s]" % (','.join(map(str, voucher_list)))
        return res

    def edit_payment_info(self):
        for pay in self:
            order = self.env['pos.order'].browse(self.order_id)
            current_payment_ids = order.payment_ids
            if pay.voucher_list:
                voucher_list = safe_eval(pay.voucher_list)
                payment_list = pay.payment_line_ids.mapped('payment_line_id')
                diff_voucher_list = list(
                    set(voucher_list).difference(set(payment_list)))
                if diff_voucher_list:
                    raise UserError(_("You can't delete payment method."))
            for line in self.payment_line_ids:
                curr_id = current_payment_ids.filtered(
                    lambda x: x.id == line.payment_line_id)
                if not line.payment_line_id or (
                        curr_id and (
                            curr_id.amount != line.amount
                            or curr_id.payment_method_id
                            != line.payment_method_id)):
                    vals = {
                        'date_perform': fields.Datetime.now(),
                        'user_id': self.env.user.id,
                        'payment_method_after_id': line.payment_method_id.id,
                        'amount_after': line.amount,
                        'pos_order_id': pay.order_id
                    }
                    if line.payment_line_id > 0:
                        payment_line_id = self.env['pos.payment'].browse(
                            line.payment_line_id)
                        vals.update({
                            'currency_name': payment_line_id.currency_name,
                            'payment_method_before_id':
                                payment_line_id.payment_method_id.id,
                            'voucher_code': payment_line_id.voucher_code,
                            'amount_before': payment_line_id.amount})
                    self.env['pos.modify.payment.history'].create(vals)
            payments_to_delete = current_payment_ids.filtered(
                lambda l: l.id not in [
                    x.payment_line_id for x in self.payment_line_ids])
            for line in payments_to_delete:
                vals = {
                    'date_perform': fields.Datetime.now(),
                    'user_id': self.env.user.id,
                    'payment_method_before_id': line.payment_method_id.id,
                    'amount_before': line.amount,
                    'voucher_code': line.voucher_code,
                    'pos_order_id': pay.order_id
                }
                self.env['pos.modify.payment.history'].create(vals)
        super(WizardModifyPayment, self).edit_payment_info()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pos.order',
            'res_id': self.order_id,
            'view_mode': 'form',
            'target': 'main',
        }


class WizardModifyPaymentLine(models.TransientModel):
    _inherit = 'wizard.modify.payment.line'

    voucher_code = fields.Char(string="Voucher Code")
