from odoo import models, api, _, fields

class ShippingFee(models.Model):
    _name = 'shipping.fee'

    name = fields.Char(string="Name")
    active = fields.Boolean('Active', default=True)
    distance_to = fields.Char('Distance to (km)')
    distance_from = fields.Char('Distance from (km)')
    quantity_product_min = fields.Char('Quantity Product Min')
    quantity_product_max = fields.Char('Quantity Product Max')
    delivery_cost = fields.Float('Delivery Cost')