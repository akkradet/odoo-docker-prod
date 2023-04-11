# -*- coding: utf-8 -*-
from odoo import api, models, tools, fields, _
import time
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class WizardReportMoveLine(models.TransientModel):
    _name = 'wizard.report.move.line'
    _description = 'Wizard Report Move Line'

    warehouse_ids = fields.Many2many('stock.warehouse', string='Stores')
    date_from = fields.Date(string="From Date", required=True, default=fields.Datetime.now)
    date_to = fields.Date(string="To Date", required=True, default=fields.Datetime.now)
    type = fields.Selection([('drink_food', 'Drink Food'),
                             ('packaged_product', 'Packaged Product')],
                             string='Report Type', default='drink_food', required=True)
    report_type = fields.Selection([('delivery_to_customer', 'Delivery To Customer'),
                             ('receipt_from_supplier', 'Receipt From Supplier'),
                             ('return_to_supplier', 'Return To Supplier')],
                             string='Print Report Type', default='delivery_to_customer', required=True)

    @api.constrains('date_from', 'date_to')
    def _check_date(self):
        if self.date_to < self.date_from:
            raise ValidationError(_('From Date must be before To Date'))
        
    @api.onchange('date_from')
    def _check_date(self):
        if self.date_from:
            self.date_to = self.date_from

    def action_report_print(self):
        if self.report_type == 'delivery_to_customer':
            return self.env.ref('phuclong_stock.report_move_delivery_to_customer').report_action(self)
        else:
            return self.env.ref('phuclong_stock.report_move_supplier_xlsx').report_action(self)
        
    def get_warehouse_list(self):
        warehouse_ids = self.env['stock.warehouse']
        if self.warehouse_ids:
            warehouse_ids = self.warehouse_ids
        else:
            warehouse_ids = self.env['stock.warehouse'].search([])
        return [x.id for x in warehouse_ids]
        
    def get_products(self):
        warehouse_ids = self.get_warehouse_list()
        picking_type_posout = self.env.ref('besco_pos_base.picking_type_posout').id or False
        fnb_type_operator = '='
        if self.type == 'drink_food':
            fnb_type_operator = '!='
        sql = '''
            SELECT sw.code warehouse_code, sw.name warehouse_name, aaa.code analytic_account_code, pt.ref_code, 
            pt.name product_name, sum(sml.qty_done) qty_done, uu.name product_uom 
            FROM stock_move_line sml JOIN product_product pp ON sml.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            JOIN uom_uom uu ON sml.product_uom_id = uu.id
            JOIN stock_warehouse sw ON sml.warehouse_id = sw.id
            JOIN stock_move sm ON sml.move_id = sm.id
            JOIN account_analytic_account aaa on sw.account_analytic_id = aaa.id
            WHERE sml.state = 'done' AND sml.warehouse_id in (%(warehouse_ids)s)
            AND sm.picking_type_id = %(picking_type_id)s
            AND timezone('UTC',sml.date::timestamp)::date BETWEEN '%(date_from)s' AND '%(date_to)s'
            AND pt.fnb_type %(fnb_type_operator)s 'packaged_product'
            GROUP BY sw.code, sw.name, aaa.code, pt.ref_code, pt.name,uu.name
            ORDER BY sw.code, pt.name'''%({'warehouse_ids': ' ,'.join(map(str, warehouse_ids)),
                                           'picking_type_id': picking_type_posout,
                                           'date_from': self.date_from.strftime(DEFAULT_SERVER_DATE_FORMAT),
                                           'date_to': self.date_to.strftime(DEFAULT_SERVER_DATE_FORMAT),
                                           'fnb_type_operator': fnb_type_operator})
        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        return result
    
    def get_products_supplier(self, get_warehouse=False):
        warehouse_ids = self.get_warehouse_list()
        picking_type_id = False
        if self.report_type == 'receipt_from_supplier':
            picking_type_id = self.env.ref('besco_stock.picking_type_good_receipt').id
        elif self.report_type == 'return_to_supplier':
            picking_type_id = self.env.ref('besco_stock.picking_type_return_supplier').id
        date_from = self.date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)
        date_to = self.date_to.strftime(DEFAULT_SERVER_DATE_FORMAT)
                                        
        if not get_warehouse:
            sql = '''
                SELECT sml.product_id, sml.product_uom_id, sml.warehouse_id warehouse_code, sum(sml.qty_done) qty_done
                FROM stock_move_line sml JOIN product_product pp ON sml.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                JOIN stock_move sm ON sml.move_id = sm.id
                WHERE sml.state = 'done' AND sml.warehouse_id in (%(warehouse_ids)s)
                AND sm.picking_type_id = %(picking_type_id)s
                AND timezone('UTC',sml.date::timestamp)::date BETWEEN '%(date_from)s' AND '%(date_to)s'
                GROUP BY sml.product_id, pt.name, sml.product_uom_id, sml.warehouse_id
                ORDER BY pt.name'''%({'warehouse_ids': ' ,'.join(map(str, warehouse_ids)),
                                               'picking_type_id': picking_type_id,
                                               'date_from': date_from,
                                               'date_to': date_to})
            self._cr.execute(sql)
            result = self._cr.fetchall()
            return result
        else:
            sql_products = '''
                SELECT sml.product_id, sml.product_uom_id
                FROM stock_move_line sml JOIN product_product pp ON sml.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                JOIN stock_move sm ON sml.move_id = sm.id
                WHERE sml.state = 'done' AND sml.warehouse_id in (%(warehouse_ids)s)
                AND sm.picking_type_id = %(picking_type_id)s
                AND timezone('UTC',sml.date::timestamp)::date BETWEEN '%(date_from)s' AND '%(date_to)s'
                GROUP BY sml.product_id, pt.name, sml.product_uom_id
                ORDER BY pt.name'''%({'warehouse_ids': ' ,'.join(map(str, warehouse_ids)),
                                               'picking_type_id': picking_type_id,
                                               'date_from': date_from,
                                               'date_to': date_to})
            
            self._cr.execute(sql_products)
            products = self._cr.fetchall()
            
            sql_warehouses = '''
                SELECT distinct(sml.warehouse_id)
                FROM stock_move_line sml 
                JOIN stock_move sm ON sml.move_id = sm.id
                WHERE sml.state = 'done' AND sml.warehouse_id in (%(warehouse_ids)s)
                AND sm.picking_type_id = %(picking_type_id)s
                AND timezone('UTC',sml.date::timestamp)::date BETWEEN '%(date_from)s' AND '%(date_to)s'
                '''%({'warehouse_ids': ' ,'.join(map(str, warehouse_ids)),
                                               'picking_type_id': picking_type_id,
                                               'date_from': date_from,
                                               'date_to': date_to})
            
            self._cr.execute(sql_warehouses)
            warehouses = self._cr.fetchall()
            return products, warehouses
        
    def get_date_from_string(self):
        date = self.date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)
        date = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
        return date.strftime('%d/%m/%Y')

    def get_date_to_string(self):
        date = self.date_to.strftime(DEFAULT_SERVER_DATE_FORMAT)
        date = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
        return date.strftime('%d/%m/%Y')

    def get_current_date(self):
        date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_report_header(self):
        if self.report_type == 'receipt_from_supplier':
            return 'BÁO CÁO TỔNG HỢP NHẬP KHO MUA HÀNG'
        elif self.report_type == 'return_to_supplier':
            return 'BÁO CÁO TỔNG HỢP XUẤT KHO TRẢ HÀNG MUA'
        else:
            if self.type == 'drink_food':
                return 'BÁO CÁO XUẤT KHO NGUYÊN LIỆU THỨC ĂN/THỨC UỐNG'
            else:
                return 'BÁO CÁO XUẤT KHO HÀNG ĐÓNG GÓI'
    
    def get_ref_code_label(self):
        if self.type == 'drink_food':
            return 'Mã tham chiếu nguyên liệu'
        else:
            return 'Mã tham chiếu'
        
    def get_product_label(self):
        if self.type == 'drink_food':
            return 'Tên nguyên liệu'
        else:
            return 'Tên sản phẩm'
        
    def get_report_name(self):
        if self.report_type == 'receipt_from_supplier':
            return _('Report Receipt From Supplier')
        else:
            return _('Report Return To Supplier')
    
    
    
    
    
    
    
    
    