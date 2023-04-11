# -*- coding: utf-8 -*-
from itertools import chain
import time

from odoo import tools
from odoo import SUPERUSER_ID

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.translate import _
from odoo.tools.float_utils import float_round

from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models

import base64
import xlrd
from xlrd import open_workbook, xldate_as_tuple


class Pricelist(models.Model):
    _inherit = "product.pricelist"

    price_type = fields.Selection(
        selection_add=[('card_code', 'Card Code')])
    card_code_pricelist = fields.Boolean('Is Pricelist By Card Code', default=False)
    card_code_partner_ids = fields.One2many(
        comodel_name='res.partner', inverse_name='card_code_pricelist_id', string='Partners', context={'with_appear_code': True})
    card_code_partner_count = fields.Integer(compute='_compute_card_code_partner_count', store=True)

    @api.depends('name','order_type','price_type')
    def name_get(self):
        result = []
        for pricelist in self:
            order_type = _('Retail')
            if pricelist.order_type == 'sale':
                order_type = _('Wholesale')
            price_type = _('Base Price') 
            if pricelist.price_type == 'price_event':
                price_type = _('Price Event')
            elif pricelist.card_code_pricelist:
                    price_type = _('Card Code')
            name = order_type + _('/ ') + price_type + _(': ') + _(pricelist.name) + ' (' + pricelist.currency_id.name + ')'
            result.append((pricelist.id, name))
        return result
    
    @api.depends('card_code_partner_ids')
    def _compute_card_code_partner_count(self):
        for rec in self:
            rec.card_code_partner_count = len(rec.card_code_partner_ids.ids)

    def action_view_card_code_partners(self):
        action = self.env.ref('base.action_partner_form').read()[0]
        action['domain'] = [('type','=','contact'), ('customer', '!=', False), ('card_code_pricelist_id', 'in', self.ids)]
        return action
    
    def action_read_file(self):
        self.ensure_one()
        if not self.file_data:
            raise UserError(_("The file data do not exits."))
        try:
            item_ids, log_failed, failed = self._read_file_xls()
            if item_ids:
                self.item_ids = [(5,)]
                self.update({'item_ids': item_ids})
            self.update(
                {'failed': failed or 0, 'log_failed': log_failed if failed > 0 else ''})
        except Exception as e:
            if self.env.user._is_admin():
                raise UserError(e)
            else:
                raise UserError(_("The file must be of extension .xls."))
        return True

    def _format_xldate_as_tuple(self, value, datemode, format_date):
        if isinstance(value, float) or isinstance(value, int):
            try:
                value = int(value)
                year, month, day, hour, minute, second = xldate_as_tuple(
                    value, datemode)
                return datetime(year, month, day, hour, minute, second)
            except Exception as e:
                pass
        elif isinstance(value, str):
            try:
                return datetime.strptime(value, format_date)
            except Exception as e:
                pass
        return False

    def _read_file_xls(self):
        self.ensure_one()
        file_data = base64.decodestring(self.file_data)
        book = open_workbook(file_contents=file_data)
        sheet = book.sheet_by_index(0)

        failed = 0
        log_failed = (_('Failed to read file %s:\n') % (self.file_name))
        item_ids = []
        self.env.cr.execute('''
                        BEGIN;
                            DELETE FROM product_pricelist_item where pricelist_id = %s;
                        COMMIT;''' % (self.id))
        for row in range(sheet.nrows):
            if row < 3:
                continue

            mess_log = ""
            failed_line = 0
            product_tmpl_id = product_uom = conversion_by_uom = False
            if sheet.cell(row, 0).value:
                im_ref_code = sheet.cell(row, 0).value
                if isinstance(im_ref_code, float):
                    im_ref_code = int(im_ref_code)
                    im_ref_code = str(im_ref_code)

                im_product_uom = sheet.cell(row, 1).value
                if isinstance(im_product_uom, float):
                    im_product_uom = int(im_product_uom)
                    im_product_uom = str(im_product_uom)

                # product_con = self.env['product.conversion'].search([('barcode','=',im_ref_code)])
                # if product_con:
                #     product_tmpl_id = product_con.product_tmpl_id
                #     product_uom = product_con.uom_id
                # else:
                product_tmpl_id = self.env['product.template'].search(
                    [('ref_code', '=', im_ref_code)])
                if not product_tmpl_id:
                    failed_line += 1
                    if mess_log == "":
                        mess_log = _(" + Line %s: Product not found" %
                                     (int(row + 1)))
                elif len(product_tmpl_id) > 1:
                    failed_line += 1
                    if mess_log == "":
                        mess_log = _(" + Line %s: Ref code in multi product: %s" %
                                     (int(row + 1), ', '.join(product_tmpl_id.mapped('display_name'))))
                else:
                    product_conversion = self.env['product.conversion'].search(
                        [('product_tmpl_id', '=', product_tmpl_id.id), ('primary', '=', True)])
                    if im_product_uom:
                        product_uom_id = self.env['uom.uom'].search(
                            [('name', '=', im_product_uom)], limit=1)
                        if product_uom_id:
                            conversion_by_uom = self.env['product.conversion'].search(
                                [('product_tmpl_id', '=', product_tmpl_id.id), ('uom_id', '=', product_uom_id.id)], limit=1)
                            if conversion_by_uom:
                                product_conversion = conversion_by_uom
                    product_uom = product_conversion.uom_id

            min_qty = 0.0
            if sheet.cell(row, 2).value:
                min_qty = sheet.cell(row, 2).value

                if not isinstance(min_qty, (float, int)):
                    min_qty = min_qty.strip()
                    try:
                        min_qty = float(min_qty)
                    except Exception:
                        failed_line += 1
                        if mess_log == "":
                            mess_log = _(" + Line %s:" % (int(row + 1)))
                        mess_log += (_(' The min quantity only supports numeric.\n'))
                        min_qty = False

            fixed_price = 0.0
            if sheet.cell(row, 3).value:
                fixed_price = sheet.cell(row, 3).value

                if not isinstance(fixed_price, (float, int)):
                    fixed_price = fixed_price.strip()
                    try:
                        fixed_price = float(fixed_price)
                    except Exception:
                        failed_line += 1
                        if mess_log == "":
                            mess_log = _(" + Line %s:" % (int(row + 1)))
                        mess_log += (_(' The fixed price only supports numeric.\n'))
                        fixed_price = False

                elif fixed_price < 0.0:
                    failed_line += 1
                    if mess_log == "":
                        mess_log = _(" + Line %s:" % (int(row + 1)))
                    mess_log += (_(' The fixed price must be greater than 0.\n'))
                    fixed_price = False

            percent_price = 0.0
            if sheet.cell(row, 4).value:
                percent_price = sheet.cell(row, 4).value

                if not isinstance(percent_price, (float, int)):
                    percent_price = percent_price.strip()
                    try:
                        percent_price = float(percent_price)
                    except Exception:
                        failed_line += 1
                        if mess_log == "":
                            mess_log = _(" + Line %s:" % (int(row + 1)))
                        mess_log += (_(' The discount only supports numeric.\n'))
                        percent_price = False

                elif percent_price < 1.0 or percent_price > 100.0:
                    failed_line += 1
                    if mess_log == "":
                        mess_log = _(" + Line %s:" % (int(row + 1)))
                    mess_log += (_(' The discount value must be between 1% to 100% .\n'))
                    percent_price = False

            date_start = False
            if sheet.cell(row, 5).value:
                date_start = self._format_xldate_as_tuple(
                    sheet.cell(row, 5).value, book.datemode, '%d/%m/%Y')
                if not date_start:
                    failed_line += 1
                    if mess_log == "":
                        mess_log = _(" + Line %s:" % (int(row + 1)))
                    mess_log += (_(' Please check format of Date Start: dd/mm/yyyy.\n'))

            if failed_line == 0 and product_tmpl_id:
                if fixed_price > 0.0:
                    item_ids.append((0, 0, {
                        'pricelist_id': self.id,
                        'applied_on': '1_product',
                        'product_tmpl_id': product_tmpl_id.id,
                        'product_uom_id': product_uom.id,
                        'date_start': date_start or datetime.now(),
                        'compute_price': 'fixed',
                        'fixed_price': fixed_price or 0,
                        'min_quantity': min_qty or 0,
                        # 'percent_price': percent_price or 0,
                    }))
                else:
                    item_ids.append((0, 0, {
                        'pricelist_id': self.id,
                        'applied_on': '1_product',
                        'product_tmpl_id': product_tmpl_id.id,
                        'product_uom_id': product_uom.id,
                        'date_start': date_start or datetime.now(),
                        'compute_price': 'percentage',
                        # 'fixed_price': fixed_price or 0,
                        'min_quantity': min_qty or 0,
                        'percent_price': percent_price or 0,
                    }))
            else:
                log_failed += mess_log
                failed += failed_line

        return item_ids, log_failed, failed
