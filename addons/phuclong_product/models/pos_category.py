# -*- coding: utf-8 -*-
from odoo import fields, models, api

class PosCategory(models.Model):
    _inherit = "pos.category"

    product_ids = fields.One2many('product.template', 'pos_categ_id', string="POS Products", readonly=False)
    allow_show_original_price = fields.Boolean('Show Original Price', default=False)