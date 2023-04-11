# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ProductCustomMaterial(models.Model):
    _name = "product.custom.material"

    material_id = fields.Many2one('product.template', string='Material', required=True, domain="[('fnb_type','=','customizable_material')]")
    product_id = fields.Many2one('product.template', string='Product', required=True, ondelete='cascade')
    product_uom_id = fields.Many2one('uom.uom', related='material_id.uom_id', string='Unit of Measure', store=True, readonly=True)
    custom_qty = fields.Float('Quantity', default=0.0, digits='Product Unit of Measure')
    
    @api.onchange('material_id')
    def on_change_material_id(self):
        material_ids = self.product_id.custom_material_ids
        if material_ids:
            domain = [
                ('fnb_type','=','customizable_material'), ('id', 'not in', material_ids.mapped('material_id').ids)
            ]
        result = {
            'domain': {
                'material_id': domain,
            },
        }
        return result

class ProductCustomMaterialQty(models.Model):
    _name = "product.custom.material.qty"

    material_id = fields.Many2one('product.template', string='Material', required=True, domain="[('fnb_type','=','customizable_material')]")
    product_uom_id = fields.Many2one('uom.uom', related='material_id.uom_id', string='Unit of Measure', store=True, readonly=True)
    custom_type = fields.Selection([('below', 'Below'), ('over', 'Over')], string="Custom Type", required=True)
    custom_qty = fields.Float('Quantity', default=0.0, digits='Product Unit of Measure')
    
    @api.constrains('material_id', 'custom_type')
    def _check_unique_material_type(self):
        if self.material_id and self.custom_type:
            existed_material = self.search([('id', '!=', self.id),('material_id', '=', self.material_id.id), ('custom_type', '=', self.custom_type)], limit=1) or False
            if existed_material:
                raise UserError(_('Config must be unique per Material and Custom type.'))