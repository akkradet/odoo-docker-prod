from odoo import models, fields, api, _

class ProductCateMobile(models.Model):
    _name = 'product.category.mobile'

    name = fields.Char('Name')
    active = fields.Boolean('Active', default=True)
    sequence_of_category = fields.Integer('Sequence', default=0)