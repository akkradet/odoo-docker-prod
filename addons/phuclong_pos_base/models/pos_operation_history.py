# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class PosOperationHistory(models.Model):
    _name = "pos.operation.history"

    warehouse_id = fields.Many2one('stock.warehouse', string='Store', related="pos_order_id.warehouse_id", store=True)
    date_perform = fields.Datetime(string="Perform Date")
    type = fields.Selection([('destroy_order_line', 'Destroy Order Line'),
                             ('destroy_order', 'Destroy Order'),
                             ('discount_line', 'Discount Line'),
                             ('discount_total', 'Discount Total'),
                             ('open_cash', 'Open Cash'),
                             ('search_customer', 'Search Customer'),
                             ('change_promotion', 'Change Promotion')
                             ], string="Type")
    pos_order_id = fields.Many2one('pos.order', string="Pos Order", ondelete="cascade")
    pos_permisson_id = fields.Many2one('pos.permission', string='Pos Permission')
    pos_manager_id = fields.Many2one('hr.employee', string='Pos Manager')
    cashier_id = fields.Many2one('hr.employee', string='Cashier', related="pos_order_id.cashier_id", store=True)
    product_id = fields.Many2one('product.product', string='Product')
    reason = fields.Text(string="Reason")
    
    @api.model
    def create(self, vals):
        if vals.get('date_perform',False):
            date_perform = self.env['res.users']._convert_date_datetime_to_utc(vals.get('date_perform',False), datetime_format=True)
            vals['date_perform'] = date_perform
        return super(PosOperationHistory, self).create(vals) 
    

