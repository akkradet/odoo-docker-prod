# -*- coding: utf-8 -*-
from odoo import fields, models, api


class POSPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    use_for = fields.Selection(
        selection_add=[('gift_code', 'Gift Code')]
    )
    giftcode_api = fields.Many2one(
        'giftcode.api.config',
        'Giftcode API'
    )
