from odoo import models, fields, api, _

class PosSaleType(models.Model):
    _inherit = 'pos.sale.type'

    use_for_app = fields.Boolean('Use for App', default=False)
    type_for_app = fields.Selection([('1', 'Pick up'), ('2', 'Delivery')], 'Shipping Type')