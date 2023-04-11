# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class ReasonConfig(models.Model):
    _name = "reason.config"
    _description = "Reason Config"
    _order = "sequence, name desc"

    name = fields.Char('Reason', required=True)
    sequence = fields.Integer('Sequence', )
    description = fields.Char('Description',)
