# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import xlrd
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    file_data = fields.Binary(
        'File', help="File to check and/or import, raw binary (not base64)")
    file_name = fields.Char('File Name', default="Template")

    failed = fields.Integer(copy=False)
    log_failed = fields.Text(copy=False)

    def print_template(self):
        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": '/phuclong_purchase_import/static/report/Import_Purchase_Lines.xls'
        }

    def action_log_failed(self):
        self.ensure_one()
        if not self.log_failed:
            return
        raise ValidationError(self.log_failed)

    def action_read_file(self):
        self.ensure_one()
        if not self.file_data:
            raise UserError(_("The file data do not exits."))
        try:
            order_line, log_failed, failed = self._read_file_xls()
            if order_line:
                # self.order_line = [(5,)]
                self.update({'order_line': order_line})
            self.update(
                {'failed': failed or 0, 'log_failed': log_failed if failed > 0 else ''})
            for purchase_line in self.order_line:
                purchase_line.with_context(
                    pass_suggest_quantity=True).onchange_product_id()
                purchase_line._onchange_quantity()
                if self.date_planned:
                    purchase_line.date_planned = self.date_planned
        except (UserError, ValidationError) as e:
            raise e
        except Exception as e:
            _logger.error(e)
            raise UserError(_("The file must be of extension .xls."))
        return True

    def _read_file_xls(self):
        self.ensure_one()
        file_data = base64.decodestring(self.file_data)
        book = xlrd.open_workbook(file_contents=file_data)
        sheet = book.sheet_by_index(0)

        failed = 0
        log_failed = (_('Failed to read file %s:') % (self.file_name))
        order_line = []
        field_search_product = 'ref_code'
        project_obj = self.env['product.product']
        for row in range(sheet.nrows):
            if row < 3:
                continue

            error = False
            mess_log = '\n' + _(" + Line %s:" % (int(row + 1)))
            ref_code = sheet.cell(row, 1).value
            product_qty = sheet.cell(row, 2).value
            product_id = project_obj.search(
                [(field_search_product, '=', ref_code)], limit=1)
            if not product_id:
                failed += 1
                mess_log += '\n' + \
                    _('   - Reference code %s is not existed') % ref_code
                error = True
            if not isinstance(product_qty, (float, int)):
                product_qty = product_qty.strip()
                try:
                    product_qty = float(product_qty)
                except Exception:
                    failed += 1
                    mess_log += '\n' + \
                        _('   - The ordered quantity only supports numeric.')
                    error = True

            if not error:
                order_line_existed = self.order_line.filtered(lambda l: l.product_id.id == product_id.id)
                if not len(order_line_existed):
                    order_line.append((0, 0, {
                        'name': product_id.description_purchase or product_id.display_name,
                        'product_id': product_id.id,
                        'product_qty': product_qty,
                        'qty_request': product_qty,
                        'price_unit': 0,
                        'order_id': self.id
                    }))
                else:
                    order_line_existed[0].write({'product_qty': product_qty,
                                                 'qty_request': product_qty})
            else:
                log_failed += mess_log

        return order_line, log_failed, failed


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.onchange('product_id')
    def onchange_product_id(self):
        product_qty = self.product_qty
        qty_request = self.product_qty
        onchange = super(PurchaseOrderLine, self).onchange_product_id()
        if self._context.get('pass_suggest_quantity', False):
            self.product_qty = product_qty
            self.qty_request = qty_request
        return onchange
