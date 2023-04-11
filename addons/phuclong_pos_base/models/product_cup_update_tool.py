# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ProductCupUpdate(models.Model):
    _name = "product.cup.update"

    name = fields.Char(string="Update Cup", default="Update Cup")
    sale_type_ids = fields.Many2many('pos.sale.type', 'cupupdate_saletype_rel', 'update_id', 'sale_type_id',
                                     string='Sale Type', required=True)
    product_ids = fields.Many2many('product.template', 'cupupdate_product_rel', 'update_id', 'product_id',
                                   string='Product', domain=[('fnb_type', '=', 'drink')], required=True)
    cup_line_ids = fields.One2many(
        'product.cup.update.line', 'product_cup_update_id', string="Cup List", required=True)

    def update_cup(self):
        self.env.cr.execute('''
            DELETE FROM product_cup_update WHERE create_uid=%(create_uid)s AND
            date(timezone('UTC',create_date::timestamp)) != current_date AND id != %(update_id)s;
        ''' % ({'create_uid': self.env.user.id, 'update_id': self.id}))
        if not self.cup_line_ids:
            raise UserError(_('Please choose cup(s) to apply.'))
        if not self.product_ids:
            raise UserError(_('Please choose drink to apply.'))
        cup_list = []
        for line in self.cup_line_ids:
            cup_list.append((0, 0, {'cup_id': line.cup_id.id,
                                    'sequence': line.sequence}))
        for product in self.product_ids:
            val = {
                'cup_ids': []
            }
            for sale_type in self.sale_type_ids:
                default_cup_available = product.cup_ids.filtered(
                    lambda l: l.sale_type_id == sale_type)
                if not default_cup_available:
                    val['cup_ids'].append((0, 0, {
                        'sale_type_id': sale_type.id,
                        'product_id': product.id,
                        'cup_line_ids': cup_list
                    }))
                else:
                    default_cup_available = default_cup_available[0]
                    cup_line_ids = [(2, cup.id)
                                    for cup in default_cup_available.cup_line_ids]
                    val['cup_ids'].append((1, default_cup_available.id, {
                        'cup_line_ids': cup_line_ids + cup_list
                    }))
            product.write(val)


class ProductCupUpdateLine(models.Model):
    _name = "product.cup.update.line"

    product_cup_update_id = fields.Many2one(
        'product.cup.update', string='Cup Update', required=True, ondelete='cascade')
    cup_id = fields.Many2one('product.template', string='Cup', required=True, domain=[
                             ('fnb_type', '=', 'cup')])
    ref_code = fields.Char(related="cup_id.ref_code", string='Reference Code')
    cup_type = fields.Selection(
        [('paper', 'Paper'), ('plastic', 'Plastic')], related='cup_id.cup_type', string="Cup Type")
    size_id = fields.Many2one(
        'product.size', related='cup_id.size_id', string="Size")
    sequence = fields.Integer(string='Sequence', required=True, default=1.0)

    @api.onchange('cup_id')
    def on_change_cup_id(self):
        cup_line_ids = self.product_cup_update_id.cup_line_ids
        if cup_line_ids:
            cup_domain = [
                ('id', 'not in', cup_line_ids.mapped(
                    'cup_id').ids), ('fnb_type', '=', 'cup')
            ]
        result = {
            'domain': {
                'cup_id': cup_domain,
            },
        }
        return result

    _sql_constraints = [
        ('sequence_product_cup_update_line_uniq', 'unique(sequence, product_cup_update_id)',
         'The sequence must be unique per Cup List!'),
    ]
