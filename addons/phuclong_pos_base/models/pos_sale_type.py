# -*- coding: utf-8 -*-
from odoo import fields, models, api

class PosSaleType(models.Model):
    _name = "pos.sale.type"

    name = fields.Char("Name", required=True)
    description = fields.Char("Description")
    active = fields.Boolean('Active', default=True)
    logo = fields.Image('Logo', copy=False, attachment=True, max_width=1024, max_height=1024)
    use_for_call_center = fields.Boolean('Use for call center', default=False)
    allow_print_label_first = fields.Boolean('Print Label First', default=False)
    show_original_subtotal = fields.Boolean('Show Original Subtotal', default=False)