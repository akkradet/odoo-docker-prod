from odoo import models, fields, api, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    available_in_mobile = fields.Boolean('Available in Mobile', default=False)
    mobile_category_id = fields.Many2one('product.category.mobile')
    use_for_topup = fields.Boolean('Use for Topup', default=False)
    is_new_product = fields.Boolean('New product', default=False)
    app_description = fields.Text('Description')
    name_mobile = fields.Char("Mobile Name")
