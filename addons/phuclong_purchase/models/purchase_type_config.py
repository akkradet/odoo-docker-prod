# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class PurchaseTypeConfig(models.Model):
    _name = "purchase.type.config"
    _description = "Purchase Type Config"
    _order = "name desc"

    name = fields.Char('Purchase Type', required=True)
    description = fields.Char('Description')
