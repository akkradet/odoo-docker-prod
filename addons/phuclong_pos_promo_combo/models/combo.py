# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64
import xlrd
import random

class Combo(models.Model):
    _name = 'sale.promo.combo'
    _description = 'Combo'
    _order= 'create_date desc'
    _inherit = ['mail.thread']

    @api.depends('combo_line_ids')
    def _get_combo_price(self):
        for combo in self:
            product = 0
            total = 0
            for line in combo.combo_line_ids:
                total += line.sub_total
                product += line.qty_combo
            combo.combo_price = total
            combo.sum_of_qty = product

    name = fields.Char('Name', required=True)
    warehouse_ids = fields.Many2many(
        'stock.warehouse',
        'combo_warehouse_rel',
        'combo_id', 'warehouse_id',
        string='Stores')
    sale_type_ids = fields.Many2many(
        'pos.sale.type',
        'combo_sale_type_rel',
        'combo_id', 'sale_type_id',
        string='Sale Type')
    member_category = fields.Many2many(
        'res.partner.category',
        'combo_partner_cate_rel',
        'combo_id', 'partner_cate_id',
        string='Partner Category')
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    start_hour = fields.Float(string='Start Hour', required=True)
    end_hour = fields.Float(string='End Hour', required=True, default=23.983)
    day_of_week = fields.Many2many(
        'day.of.week.config',
        'combo_day_rel',
        'combo_id', 'day_id',
        string='Day of Week')
    combo_line_ids = fields.One2many(
        'sale.promo.combo.line',
        'sale_promo_combo_id', 'Combo Lines', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('cancel', 'Cancel')
        ], string='State', default='draft')
    active = fields.Boolean('Active', default=True)
    combo_price = fields.Float(
        string='Combo Price',
        compute='_get_combo_price', store=True)
    sum_of_qty = fields.Float(
        string='Sum of quantity',
        compute='_get_combo_price', store=True)
    use_for_coupon = fields.Boolean('Use For Coupon', default=False)

    def action_cancel(self):
        self.write({'state': 'cancel'})
        self.message_post(body=_(
                "The Combo <b><em>%s</em></b> has been "
                "<b>Canceled</b> by <b><b><em>%s</em></b></b>.") %
                (self.name, self.env.user.name))
    
    def action_reset(self):
        self.write({'state': 'draft'})
    
    def action_approve(self):
        self.write({'state': 'approved'})
        self.message_post(body=_(
                "The Combo <b><em>%s</em></b> has been "
                "<b>Confirmed</b> by <b><b><em>%s</em></b></b>.") %
                (self.name, self.env.user.name))


class ComboLine(models.Model):
    _name = 'sale.promo.combo.line'
    _description = 'Combo Line'

    @api.depends('unit_price_combo', 'qty_combo')
    def _get_subtotal(self):
        for line in self:
            line.sub_total = line.unit_price_combo * line.qty_combo

#     @api.depends('categ_id')
#     def _get_categories_dom(self):
#         for line in self:
#             if line.categ_id:
#                 categ_list = self.env['product.category']
#                 child_categ_ids = self.env['product.category'].search([
#                     ('id', 'child_of', line.categ_id.id)])
#                 categ_list |= child_categ_ids
#                 domain = "[%s]" % (','.join(map(str, [i.id for i in categ_list])))
#                 line.categories_dom = domain
#             else:
#                 line.categories_dom = False
    name = fields.Char('Combo Line Name', required=True)
    sale_promo_combo_id = fields.Many2one('sale.promo.combo', ondelete='cascade')
    apply_on = fields.Selection(
        [('product_list', 'Product List'), ('categ', 'Category')], 'Apply On', default="product_list")
#     categ_id = fields.Many2one(
#         'product.category',
#         string="Category")
    categ_ids = fields.Many2many(
        'product.category', 'combo_line_categ_rel', 'line_id', 'categ_id',
        string="Category List")
    product_list_ids = fields.Many2many(
        'product.product',
        'combo_line_template_rel',
        'line_id', 'product_id',
        compute='_compute_combo_line_detail_product',
        string='Product List')
    unit_price_combo = fields.Float(
        string='Unit Price in Combo',
        required=False)
    qty_combo = fields.Float(
        string='Qty in Combo',
        default=1,
        required=True)
    sub_total = fields.Float(
        compute='_get_subtotal',
        store=True,
        string='Subtotal')
    required_different = fields.Boolean(
        'Required Different Product ', default=False)
    categories_dom = fields.Char(compute="_get_categories_dom", store=True)
    combo_line_detail_ids = fields.One2many(
        'sale.promo.combo.line.detail',
        'sale_promo_combo_line_id', 'Combo Line Details', required=True)
    use_pricelist = fields.Boolean(default=False)
    file = fields.Binary('File', help='Choose file Excel', readonly=False, copy=False)
    file_name = fields.Char('Filename', size=100, default='Combo Products.xls')
    
    @api.onchange('use_pricelist')
    def onchange_use_pricelist(self):
        if not self.use_pricelist and self.apply_on == 'categ':
            self.apply_on = 'product_list'
    
    @api.depends('apply_on', 'combo_line_detail_ids', 'categ_ids')
    def _compute_combo_line_detail_product(self):
        for line in self:
            if line.apply_on == 'product_list':
                if line.combo_line_detail_ids:
                    line.product_list_ids = line.combo_line_detail_ids.mapped('product_id')
                else:
                    line.product_list_ids = False
            else:
                if line.categ_ids:
                    child_categ_ids = self.env['product.category'].sudo().search([
                        ('id', 'child_of', line.categ_ids.ids)])
                    product_ids = self.env['product.product'].search([('categ_id', 'in', child_categ_ids.ids)])
                    line.product_list_ids = product_ids
                else:
                    line.product_list_ids = False
    
    def print_report_product_import(self):
        return self.env.ref('phuclong_pos_promo_combo.report_import_product_combo').report_action(self)
    
    def import_file(self):
        failure = 0
        quantity = 0
        for line in self:
            if line.combo_line_detail_ids:
                line.combo_line_detail_ids.unlink()
            try:
                recordlist = base64.decodestring(line.file)
                excel = xlrd.open_workbook(file_contents=recordlist)
                sheet = excel.sheet_by_index(0)
            except Exception:
                raise UserError(('Please select File'))
            if sheet:
                mess_log = ''
                for row in range(sheet.nrows):
                    if row >= 1:
                        product_name = sheet.cell(row,1).value
                        sub_price = sheet.cell(row,2).value
                        product_price = sheet.cell(row,3).value
                        if isinstance(product_name, float):
                            product_name = int(product_name)
                            product_name = str(product_name)
                        product_id, product_uom, barcode_id, mess_failed = self.env['product.product']._get_product(product_name)
                        if not product_id:
                            product_id = self.env['product.product'].search([('ref_code', '=', product_name)])
                        if not product_id:
                            failure += 1
                            mess_log += _(" + Line %s:"%(int(row +1))) + mess_failed + '\n'
                        else:
                            try:
                                self.env['sale.promo.combo.line.detail'].create({'product_id': product_id.id,
                                                                             'sub_price': sub_price if (not line.use_pricelist and sub_price) else 0,
                                                                             'unit_price_combo': product_price if (not line.use_pricelist and product_price) else 0,
                                                                             'sale_promo_combo_line_id':line.id})
                            except Exception as e:
                                failure += 1
                                mess_log += _(" + Line %s: "%(int(row +1))) + str(e) + '\n'
                                continue

                if failure > 0:
                    raise UserError(_(mess_log))

        return True
    
    
class ComboLineDetail(models.Model):
    _name = 'sale.promo.combo.line.detail'
    _description = 'Combo Line Detail'
    
    sale_promo_combo_line_id = fields.Many2one('sale.promo.combo.line', ondelete='cascade')
    product_id = fields.Many2one('product.product', string="Product", required=True)
    uom_id = fields.Many2one('uom.uom', string="Uom", related="product_id.uom_id", readonly=True)
    sub_price = fields.Float(string="Sub Price")
    unit_price_combo = fields.Float(string="Price Unit in Combo")
    
    @api.constrains('sub_price', 'unit_price_combo')
    def _check_price(self):
        for line in self:
            if line.sub_price < line.unit_price_combo:
                raise UserError(_("%s: Unit price must be smaller than Sub price")%(line.product_id.display_name))
    
    
    
