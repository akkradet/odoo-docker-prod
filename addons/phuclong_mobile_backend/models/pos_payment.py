# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    payoo_payment_method = fields.Selection(string='Payoo Payment Method', selection=[
        ('1', 'Ví điện tử'),
        ('2', 'Thẻ quốc tế'),
        ('3', 'Thẻ nội địa'),
        ('4', 'Thanh toán sau'),
        ('5', 'Thanh toán QRCode'),
        ('6', 'Thanh toán trả góp'),
    ])
    payoo_card_issuance_type = fields.Selection(string='Payoo Card Issuance Type', selection=[
        ('0', 'Trong nước'),
        ('1', 'Ngoài nước'),
    ])
    payoo_bank_name = fields.Char(string='Payoo Bank Name')
    payoo_card_number = fields.Char(string='Payoo Card Number')
    payoo_billing_code = fields.Char(string='Payoo Billing Code')
