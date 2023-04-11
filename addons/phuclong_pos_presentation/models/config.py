# -*- coding: utf-8 -*-
from odoo import fields, models, api


class POSConfig(models.Model):
    _inherit = "pos.config"

    use_external_display = fields.Boolean(
        'Use External Display to show Order and Banners', default=False)
    order_break_timeout = fields.Float(
        'How many second will banners display\
            after the last action on screen?')
