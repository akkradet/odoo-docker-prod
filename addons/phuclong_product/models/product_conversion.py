# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class ProductConversion(models.Model):
    _inherit = "product.conversion"
    
    @api.model
    def default_get(self, fields):
        rec = super(ProductConversion, self).default_get(fields)
        rec.update({
            'list_price': 0.0,
            'rounding':0.00001
        })
        return rec
    