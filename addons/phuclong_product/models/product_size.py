# -*- coding: utf-8 -*-
from odoo import fields, models, api

class ProductSize(models.Model):
    _name = "product.size"
    _order = "sequence"

    name = fields.Char("Name", required=True)
    description = fields.Char("Description")
    sequence = fields.Integer(string='Sequence', required=True, default=1)
    
    @api.constrains('sequence',)
    def _check_sequence(self):
        for rcs in self:
            if rcs.sequence < 0:
                raise UserError(_('The sequence is must be positive numbers!'))
            
