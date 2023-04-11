# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

from odoo.exceptions import UserError


class ProductMaterialLine(models.Model):
    _name = 'product.material.line'
    _description = 'Product Material Line'
    _order = 'sequence asc'
    
    # FIELDS
    # -------------------------------------------------------------------------
    sequence = fields.Integer(string='Sequence', required=True, default=1.0)
    # Tên danh sách nguyên liệu
    product_id = fields.Many2one('product.template', string='Material', required=True)
    product_uom_id = fields.Many2one('uom.uom', related='product_id.uom_id', string='Unit of Measure',
                                     store=True, readonly=True)
    product_material_id = fields.Many2one('product.material', string='Bill of Material Line', required=True, ondelete="cascade")
    # =========================================================
    # AMOUNT FIELDS
    # =========================================================
    product_qty = fields.Float(string='Quantity', required=True, digits='Product Unit of Measure')
    
    # -------------------------------------------------------------------------
    # CONSTRAINS METHODS
    # -------------------------------------------------------------------------
    @api.constrains('sequence',)
    def _check_sequence(self):
        for rcs in self:
            if rcs.sequence < 0:
                raise UserError(_('The sequence is must be positive numbers!'))
            
#     @api.constrains('product_qty',)
#     def _check_quantity(self):
#         for rcs in self:
#             if rcs.product_qty <= 0:
#                 raise UserError(_('The Quantity must be > 0!'))

    # _sql_constraints, @api.constrains
    _sql_constraints = [
        ('sequence_material_line_uniq', 'unique(sequence, product_material_id)',
         'The sequence of the product material line must be unique per product material list!'),
    ]
    
#     @api.onchange('product_material_id')
#     def on_change_product_material_id(self):
#         result = {}
#         if self.product_material_id.product_custom_id:
#             result = {
#                 'domain': {
#                     'product_id': [('fnb_type', '=', 'customizable_material')],
#                 },
#             }
#         return result

