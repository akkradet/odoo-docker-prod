# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError
from lxml import etree
import base64, xlrd
import time
from datetime import datetime
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class WizardCheckVoucherCoupon(models.TransientModel):
    _name = "wizard.check.voucher.coupon"
    _description = 'WizardCheckVoucherCoupon'

    type = fields.Selection([('voucher', 'Voucher'),
                             ('coupon', 'Coupon'),
                             ('coupon_employee', 'Coupon Employee')], string="Type", required=True, default="voucher")
    code = fields.Char()
    appear_code = fields.Char()
    result = fields.Text(translate=True)
    
    def check_voucher_coupon(self):
        self.result = False
        code = False
        if self.type!='coupon_employee':
            code = self.env['crm.voucher.info'].search([('ean','=',self.code), ('type','=',self.type), 
                                                        ('publish_id.apply_for_employee','=',False)],limit=1)
            if not len(code):
                self.result = _('Code is not exist')
            if code.state == 'Close':
                order_warehouse = ''
                order_date = ''
                if code.order_reference:
                    order = self.env['pos.order'].with_user(SUPERUSER_ID).search([('pos_reference', '=', code.order_reference)], limit=1) or False
                    if order:
                        order_warehouse = order.warehouse_id and order.warehouse_id.name or ''
                        order_date = self.env['res.users']._convert_user_datetime(order.date_order.strftime(DATETIME_FORMAT))
                        order_date = order_date.strftime('%H:%M:%S %d-%m-%Y')
                
                error_message = (_('Code already in use\n' + 
                                  'Bill: %s\n'%code.order_reference + 
                                  'Store: %s\n'%order_warehouse +
                                  'Date: %s\n'%order_date))
                self.result = error_message
        else:
            employee = self.sudo().env['hr.employee'].search([('emp_card_id.appear_code','=',self.appear_code)], limit=1)
            if not employee:
                self.result = _('Employee is not exist')
            else:
                code = self.env['crm.voucher.info'].search([('employee_id','=',employee.id), 
                                                            ('publish_id.apply_for_employee','=',True)], limit=1)
                if not len(code):
                    self.result = _('No employee coupons have been issued for this card code')
                if code.state == 'Close':
                    self.result = _('Coupon is using out of limit')
        
        if code and not self.result:
            if code.state == 'Cancel':
                self.result = _('Code is cancelled and not available')
            else:
                code = code.sudo()
                employee_string = ''
                voucher_amount = ''
                if code.employee_id and code.appear_code_id:
                    employee_string = code.appear_code_id.appear_code + ' - ' + code.employee_id.name + '\n'
                if code.type == 'voucher' and code.voucher_amount:
                    voucher_amount = 'Voucher Amount: %s'%('{:,.0f}'.format(code.voucher_amount) or '')
                info_message = (_('Code is valid\n' + employee_string +
                                  'Used Count: %s\n'%code.used_count + 
                                  'Remaining Count: %s\n'%(code.usage_limits - code.used_count) + 
                                  'Date from: %s\n'%(code.effective_date_from and code.effective_date_from.strftime('%d-%m-%Y') or '') +
                                  'Date to: %s\n'%(code.effective_date_to and code.effective_date_to.strftime('%d-%m-%Y') or '') +
                                  voucher_amount))
                self.result = info_message
                
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.check.voucher.coupon',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        } 
                
