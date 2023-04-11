# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductMaterial(models.Model):
    _inherit = 'product.material'

    available_in_mobile = fields.Boolean('Available in mobile', default=True)
    name_mobile = fields.Char('Mobile Name')