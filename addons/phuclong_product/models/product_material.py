# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductMaterial(models.Model):
    _name = 'product.material'
    _description = 'Product Material'
    _order = 'name desc'
    
    @api.depends('option_unavailable_ids')
    def _get_option_unavailable_dom(self):
        for record in self:
            domain = ''
            if record.option_unavailable_ids:
                domain = "%s"%(','.join(map(str, [i.type for i in record.option_unavailable_ids])))
            record.option_unavailable_dom = domain
    
    name = fields.Char(string="Name", required=True)
    material_line_ids = fields.One2many('product.material.line', 'product_material_id',string='Material Line',)
    product_id = fields.Many2one('product.template', string='Product')
    product_custom_id = fields.Many2one('product.template', string='Product')
    option_unavailable_ids = fields.Many2many('product.material.option', 'product_material_option_rel', 'material_id', 'option_id', string="Unavailable Options")
    option_unavailable_dom = fields.Char(compute='_get_option_unavailable_dom', store=True)
    
class ProductMaterialOption(models.Model):
    _name = 'product.material.option'
    _description = 'Product Material Option'

    name = fields.Char(string='Type')
    type = fields.Selection([('none', 'None'), ('below', 'Below'), ('normal', 'Normal'), ('over', 'Over')], string='Type', required=True)
    