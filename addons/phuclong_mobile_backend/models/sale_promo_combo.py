from odoo import models, fields, api, _

class SalePromoCombo(models.Model):
    _inherit = 'sale.promo.combo'

    image_mobile = fields.Image('Image for Mobile')