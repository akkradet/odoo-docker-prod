# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class productPosSurchargeHeader(models.Model):
    _name = 'product.surcharge.header'
    _inherit = ['mail.thread']

    name = fields.Char('Name', required=True)
    warehouse_ids = fields.Many2many(
        'stock.warehouse',
        'surcharge_header_warehouse_rel',
        'surcharge_header_id', 'warehouse_id',
        string='Stores')
    sale_type_ids = fields.Many2many(
        'pos.sale.type',
        'surcharge_header_saletype_rel', 'surcharge_header_id', 'sale_type_id',
        string='Sale type')
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    surcharge_line_ids = fields.One2many(
        'product.surcharge.line',
        'surcharge_header_id', 'Surcharge Line', required=True)
    active = fields.Boolean('Active', default=True)
    
    @api.constrains('start_date', 'end_date')
    def _check_date_range(self):
        for record in self:
            if record.start_date > record.end_date:
                raise UserError(_('End date must greater than start date'))
        return True


class productPosSurchargeHeaderLine(models.Model):
    _name = 'product.surcharge.line'

    @api.depends('category_ids')
    def _get_categories_dom(self):
        for line in self:
            if line.category_ids:
                categ_list = self.env['product.category']
                for item in line.category_ids:
                    child_categ_ids = self.env['product.category'].search([
                        ('id', 'child_of', item.id)])
                    categ_list |= child_categ_ids
                domain = "[%s]" % (
                    ','.join(map(str, [i.id for i in categ_list])))
                line.categories_dom = domain
            else:
                line.categories_dom = False

    apply_on = fields.Selection([
        ('category', 'Category'),
        ('combo', 'Combo'),
        ], string='Apply On', default='category')
    category_ids = fields.Many2many(
        'product.category',
        'surcharge_line_product_category_rel',
        'surcharge_line_id',
        'product_category_id',
        string='Category')
    combo_ids = fields.Many2many(
        'sale.promo.combo',
        'surcharge_line_combo_rel',
        'surcharge_line_id',
        'combo_id',
        string='Combo')
    surcharge_percent = fields.Float('Surcharge (%)', required=True)
    surcharge_header_id = fields.Many2one(
        'product.surcharge.header',
        'Surcharge Header'
    )
    categories_dom = fields.Char(compute="_get_categories_dom", store=True)
