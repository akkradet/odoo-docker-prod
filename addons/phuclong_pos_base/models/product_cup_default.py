# -*- coding: utf-8 -*-
from odoo import fields, models, api

class ProductCupDefault(models.Model):
    _name = "product.cup.default"

    sale_type_id = fields.Many2one('pos.sale.type', string='Sale Type', required=True)
#     cup_id = fields.Many2one('product.template', string='Cup', required=True, domain=[('fnb_type', '=', 'cup')])
#     lid_id = fields.Many2one('product.template', related='cup_id.lid_id', string='Lid', readonly=True, store=True)
    product_id = fields.Many2one('product.template', string='Product', required=True, ondelete='cascade')
    cup_line_ids = fields.One2many('product.cup.line', 'cup_default_id', string="Cup List", required=True)
    cup_type_load_pos = fields.Selection([('none', 'None'),('paper', 'Paper'), ('plastic', 'Plastic'),
                                          ('paper_1st', 'Paper First'),('plastic_1st', 'Plastic First')],
                                          compute="_get_cup_type_load_pos", store=True, string="Cup Type Load POS", default="none")
    
    @api.depends('cup_line_ids')
    def _get_cup_type_load_pos(self):
        for cup in self:
            if cup.cup_line_ids:
                cup_lines_sorted = cup.cup_line_ids.sorted(key=lambda l: l.sequence)
                cup_type = cup_lines_sorted[0].cup_type
                for cup_line in cup_lines_sorted:
                    if cup_line.cup_type != cup_type:
                        cup_type = cup_type + '_1st'
                        break
                cup.cup_type_load_pos = cup_type
            else:
                cup.cup_type_load_pos = 'none'
    
    @api.onchange('sale_type_id')
    def on_change_sale_type_id(self):
        cup_ids = self.product_id.cup_ids
        if cup_ids:
            cup_domain = [
                ('id', 'not in', cup_ids.mapped('sale_type_id').ids)
            ]
        result = {
            'domain': {
                'sale_type_id': cup_domain,
            },
        }
        return result
    
class ProductCupLine(models.Model):
    _name = "product.cup.line"
    
    cup_default_id = fields.Many2one('product.cup.default', string='Cup Default', required=True, ondelete='cascade')
    cup_id = fields.Many2one('product.template', string='Cup', required=True, domain=[('fnb_type', '=', 'cup')])
    lid_id = fields.Many2one('product.template', related='cup_id.lid_id', string='Lid', readonly=True, store=True)
    cup_type = fields.Selection([('paper', 'Paper'), ('plastic', 'Plastic')], related='cup_id.cup_type', string="Cup Type", store=True)
    sequence = fields.Integer(string='Sequence', required=True, default=1.0)
    
    @api.onchange('cup_id')
    def on_change_cup_id(self):
        cup_line_ids = self.cup_default_id.cup_line_ids
        if cup_line_ids:
            cup_domain = [
                ('id', 'not in', cup_line_ids.mapped('cup_id').ids), ('fnb_type', '=', 'cup')
            ]
        result = {
            'domain': {
                'cup_id': cup_domain,
            },
        }
        return result
    
    _sql_constraints = [
        ('sequence_product_cup_line_uniq', 'unique(sequence, cup_default_id)',
         'The sequence must be unique per Cup List!'),
    ]

class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    cup_ids = fields.One2many('product.cup.default', 'product_id', string='Default Cup')
    
    