# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    card_code_pricelist_id = fields.Many2one(
        comodel_name='product.pricelist', string='Pricelist')
