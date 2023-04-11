# -*- encoding: utf-8 -*-
from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta
import time
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from odoo.exceptions import ValidationError
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class ReportPurchaseDetails(models.TransientModel):
    _name = "report.purchase.details"

    date_from = fields.Date(string="From Date", required=True)
    date_to = fields.Date(string="To Date", required=True)
    warehouse_ids = fields.Many2many('stock.warehouse', 'wizard_purchase_details_warehouse_rel',
                                     'detail_id', 'warehouse_id', string="Stores")
    type_report = fields.Selection([('purchase', 'Purchase'),
                                    ('return', 'Return')],
                                    string='Report Type', default='purchase', required=True)

    @api.constrains('date_from', 'date_from')
    def _check_date_start(self):
        if self.date_to < self.date_from:
            raise ValidationError(_('The From Date must be before the To Date'))

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    # các phương thức có sẵn của model: init, default_get, create, write, unlink, name_search, search, name_get
    @api.model
    def default_get(self, fields):
        rec = super(ReportPurchaseDetails, self).default_get(fields)
        date_from = date.today() + relativedelta(days=-1)
        rec.update({
            'date_from': date_from,
            'date_to': date_from,
        })
        return rec

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------

    # action_draft, action_done, action_invoice_create, action_invoice_view
    def action_export(self):
        return self.env.ref('phuclong_purchase.purchase_details_xlsx').report_action(self)

    def get_date_from(self):
        date = self.date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)
        date = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
        return date.strftime('%d/%m/%Y')

    def get_date_to(self):
        date = self.date_to.strftime(DEFAULT_SERVER_DATE_FORMAT)
        date = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_current_date(self):
        date = time.strftime(DATETIME_FORMAT)
        date = self.env['res.users']._convert_user_datetime(date)
        return date.strftime('%d/%m/%Y %H:%M:%S')

    def get_data_products(self):
        convert_date_datetime_to_utc = self.env.user._convert_date_datetime_to_utc
        date_from = convert_date_datetime_to_utc(self.date_from.strftime(DEFAULT_SERVER_DATETIME_FORMAT), True)
        date_to = convert_date_datetime_to_utc((self.date_to + timedelta(days=1)).strftime(DEFAULT_SERVER_DATETIME_FORMAT), True)
        domain = [('state', '=', 'purchase'),
                  ('order_id.type', '=', self.type_report),
                  ('order_id.date_planned', '>=', date_from),
                  ('order_id.date_planned', '<', date_to),]
        if self.warehouse_ids:
            domain.append(('warehouse_id', 'in', self.warehouse_ids.ids))
        total_po_line_ids = self.env['purchase.order.line'].sudo().search(domain)
        po_line_ids = self.env['purchase.order.line'].sudo()
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in total_po_line_ids:
            if line.order_id.type == 'return':
                po_line_ids |= line
            else:
                if float_compare(line.product_qty, line.qty_received, precision_digits=precision) > 0:
                    po_line_ids |= line
        if po_line_ids:
            warehouse_id = po_line_ids.mapped('warehouse_id').sorted(key=lambda m: (m.region_stock_id, m.code))
            product_id = po_line_ids.mapped('product_id').sorted('categ_id')
            return product_id, warehouse_id
        else:
            return self.env['product.product'], self.env['stock.warehouse']

#     def get_warehouse(self):
#         if self.warehouse_ids:
#             return self.warehouse_ids
#         else:
#             return self.env['stock.warehouse'].sudo().search([], order='code')

    def total_purchased_product_qty(self, product_id, warehouse):
        convert_date_datetime_to_utc = self.env.user._convert_date_datetime_to_utc
        date_from = convert_date_datetime_to_utc(self.date_from.strftime(DEFAULT_SERVER_DATETIME_FORMAT), True)
        date_to = convert_date_datetime_to_utc((self.date_to + timedelta(days=1)).strftime(DEFAULT_SERVER_DATETIME_FORMAT), True)
        po_line_ids = self.env['purchase.order.line'].sudo().search([('state', '=', 'purchase'),
                                                                    ('order_id.type', '=', self.type_report),
                                                                    ('order_id.date_planned', '>=', date_from),
                                                                    ('order_id.date_planned', '<', date_to),
                                                                    ('product_id', '=', product_id.id),
                                                                    ('warehouse_id', '=', warehouse.id)
                                                                    ],)
        product_qty = po_line_ids and abs(sum(po_line_ids.mapped('product_qty'))) or 0
        product_qty_received = po_line_ids and abs(sum(po_line_ids.mapped('qty_received'))) or 0
        total_qty = product_qty - product_qty_received
        return total_qty
    
    def get_report_name(self):
        if self.type_report == 'purchase':
            report_name = 'Báo cáo tổng hợp mua hàng hằng ngày'
        else:
            report_name = 'Báo cáo tổng hợp trả hàng hằng ngày'
        return report_name   
            
        
        
        

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
