from odoo import models, fields, api, _

class ProductCategory(models.Model):
    _inherit = 'product.category'

    available_in_mobile = fields.Boolean('Available in Mobile', default=False)