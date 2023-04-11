# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PosModifyPaymentHistory(models.Model):
    _name = "pos.modify.payment.history"

    date_perform = fields.Datetime(string="Date Perform")
    user_id = fields.Many2one('res.users', string="Responsible")
    currency_name = fields.Char(string="Currency Name")
    payment_method_before_id = fields.Many2one(
        'pos.payment.method',
        string="Payment Method Before")
    payment_method_after_id = fields.Many2one(
        'pos.payment.method',
        string="Payment Method After")
    voucher_code = fields.Char(string="Voucher Code")
    amount_before = fields.Float(string="Amount Before")
    amount_after = fields.Float(string="Amount After")
    pos_order_id = fields.Many2one(
        'pos.order',
        string="Pos Order",
        ondelete="cascade")
