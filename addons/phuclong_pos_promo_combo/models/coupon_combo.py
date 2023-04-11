# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools import float_is_zero, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang, format_date

from odoo.exceptions import UserError, ValidationError, RedirectWarning
import odoo.addons.decimal_precision as dp
import time
# import xmlrpclib
from datetime import datetime
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

import xlrd
import base64

class CrmVoucherPublish(models.Model):
    _inherit = 'crm.voucher.publish'

    apply_on_combo = fields.Boolean('Apply on Combo', default=False)
    apply_for_employee = fields.Boolean('Apply for Employee', default=False)
    apply_for_themos_cup_promo = fields.Boolean('Apply for Thermos Cup Promotion', default=False)
    promo_combo_id = fields.Many2one('sale.promo.combo','Combo')
    
    @api.onchange('apply_on_combo')
    def onchange_apply_on_combo(self):
        if self.apply_on_combo:
            if self.apply_for_employee:
                self.apply_for_employee = False
            if self.apply_for_themos_cup_promo:
                self.apply_for_themos_cup_promo = False
        
    @api.onchange('apply_for_employee')
    def onchange_apply_for_employee(self):
        if self.apply_for_employee:
            if self.apply_on_combo:
                self.apply_on_combo = False
            if self.apply_for_themos_cup_promo:
                self.apply_for_themos_cup_promo = False
            if self.coupon_type != 'import':
                self.coupon_type = 'import'
    
    @api.onchange('apply_for_themos_cup_promo')
    def onchange_apply_for_themos_cup_promo(self):
        result = {}
        if self.apply_for_themos_cup_promo:
            if self.apply_for_employee:
                self.apply_for_employee = False
            if self.apply_on_combo:
                self.apply_on_combo = False
            result = {
                'domain': {
                    'promotion_header_id': [('list_type', '=', 'DIS'),('use_for_coupon','=',True)],
                },
            }
        else:
            result = {
                'domain': {
                    'promotion_header_id': [('use_for_coupon','=',True)],
                },
            }
        return result
    
    @api.model
    def check_coupon_apply_combo(self, coupon_code ,backend_id):
        date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT).date()
        voucher_pool = self.env['crm.voucher.info']
        result = []
        code = str(coupon_code['code'])
        criteria = [('ean','=',code),('type','=','coupon'),('state','in',['Create','Open','Close'])]
        coupon_apply = voucher_pool.search(criteria, limit=1)
        
        if len(coupon_apply) and coupon_apply.publish_id.apply_for_employee:
            result.append('employee')
            return result
        
        if len(coupon_apply) and coupon_apply.publish_id.apply_for_themos_cup_promo:
            result.append('product_coupon')
            return result
        
        if len(coupon_apply) == 0 or not coupon_apply.publish_id.apply_on_combo or not coupon_apply.publish_id.promo_combo_id:
            return []
        
        if coupon_apply.effective_date_from and coupon_apply.effective_date_to:
            if coupon_apply.effective_date_from > date or coupon_apply.effective_date_to < date:
                result.append('date')
                result.append(coupon_apply.effective_date_to)
                return result
            
        if coupon_apply.state == 'Close':
            result.append('count')
            result.append(coupon_apply.used_count)
            result.append(coupon_apply.order_reference)
            order_warehouse = ''
            order_date = ''
            if(coupon_apply.order_reference):
                order = self.env['pos.order'].search([('pos_reference', '=', coupon_apply.order_reference)], limit=1) or False
                if order:
                    order_warehouse = order.warehouse_id and order.warehouse_id.name or ''
                    order_date = self.env['res.users']._convert_user_datetime(order.date_order.strftime(DATETIME_FORMAT))
                    order_date = order_date.strftime('%H:%M:%S %d-%m-%Y')
                    
            result.append(order_warehouse)
            result.append(order_date and order_date or '')
                    
            return result
        
        pushlish_id = coupon_apply.publish_id
        if backend_id!= False:
            if pushlish_id.apply_type == 'select_warehouse':
                if backend_id not in pushlish_id.warehouse_ids.ids:
                    return []
        
        promo_combo_id = coupon_apply.publish_id.promo_combo_id
        result.append('combo')
        result.append(coupon_apply.effective_date_to)
        result.append(coupon_apply.used_count)
        available_count = coupon_apply.usage_limits - coupon_apply.used_count
        result.append(available_count)
        result.append(promo_combo_id.id)
            
        return result
    
    @api.model
    def check_coupon_product(self, coupon_code ,backend_id):
        voucher_pool = self.env['crm.voucher.info']
        code = str(coupon_code)
        criteria = [('ean','=',code),('type','=','coupon'),('state','=','Create'),('publish_id.apply_for_themos_cup_promo','=',True),
                    ('effective_date_from','=',False),('effective_date_to','=',False)]
        coupon_apply = voucher_pool.search(criteria, limit=1)
        
        if not len(coupon_apply):
            return False
        
        pushlish_id = coupon_apply.publish_id
        if backend_id!= False:
            if pushlish_id.apply_type == 'select_warehouse':
                if backend_id not in pushlish_id.warehouse_ids.ids:
                    return False
        
        return True
    
    def print_report_coupon_voucher(self):
        if self.apply_for_employee:
            return self.env.ref('phuclong_pos_promo_combo.report_import_coupon_employee').report_action(self)
        else:
            return self.env.ref('besco_voucher_coupon.report_import_coupon_voucher').report_action(self)
        
    def import_file(self):
        failure = 0
        quantity = 0
        for voucher in self:
            if voucher.apply_for_employee:
                self._cr.execute('delete from crm_voucher_info where publish_id = %s'%(voucher.id))
                self._cr.commit()
            try:
                recordlist = base64.decodestring(voucher.file)
                excel = xlrd.open_workbook(file_contents=recordlist)
                sh = excel.sheet_by_index(0)
            except Exception:
                raise UserError(('Please select File'))
            if sh:
                messenger = ''
                for row in range(sh.nrows):
                    if row > 2:
                        if voucher.apply_for_employee:
                            employee_code = sh.cell(row, 2).value or False
                            if isinstance(employee_code, float):
                                employee_code = int(employee_code)
                                employee_code = str(employee_code)
                            
                            employee_code_id = self.env['cardcode.info'].search([('appear_code','=', employee_code),('employee_id', '!=', False),('state', '=', 'using')], limit=1)
                            if not employee_code_id:
                                failure += 1
                                line = row + 1
                                messenger += _('\n- Error in Line ') + str(line) + ': ' + _('Employee code is not available ')
                            else:
                                vals = {
                                    'ean': '%s%s' % (str(employee_code_id.hidden_code), fields.Datetime.context_timestamp(self, fields.Datetime.now()).strftime('%d%m%Y%H%M')),
                                    'publish_date':voucher.publish_date,
                                    'publish_id':voucher.id,
                                    'usage_limits':voucher.usage_limits,
                                    'state':'Create',
                                    'employee_id':employee_code_id.employee_id.id,
                                    'appear_code_id':employee_code_id.id
                                }
                                try:
                                    self.env['crm.voucher.info'].create(vals)
                                    quantity += 1
                                except Exception:
                                    failure += 1
                                    line = row + 1
                                    messenger += '\n- Error in Line ' + str(line)
                        
                        else:
                            coupon_code = sh.cell(row, 1).value or False
                            if isinstance(coupon_code, float):
                                coupon_code = int(coupon_code)
                                coupon_code = str(coupon_code)
                            voucher_amount = sh.cell(row, 2).value or False
                            voucher_limit = sh.cell(row, 3).value or 1
                            
                            vals = {
                                'ean': str(coupon_code),
                                'publish_date':voucher.publish_date,
                                'publish_id':voucher.id,
                                'voucher_amount':voucher_amount,
                                'usage_limits':voucher_limit,
                                'state':'Create',
                            }
                            try:
                                self.env['crm.voucher.info'].create(vals)
                                quantity += 1
                            except Exception:
                                failure += 1
                                line = row + 1
                                messenger += '\n- Error in Line ' + str(line)
            
                if failure > 0:
                    voucher.failure = failure or 0
                    raise UserError(messenger)
                
                voucher.write({'generate_flag':True,
                               'quantity':quantity,
                               'failure':0})
        return True
    
class CrmVoucherInfo(models.Model):
    _inherit = 'crm.voucher.info'
    
    apply_for_employee = fields.Boolean(related='publish_id.apply_for_employee', string='Apply for Employee', store=True, readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    appear_code_id = fields.Many2one('cardcode.info', string='Appear Card Code', readonly=True)
    used_count = fields.Integer(string='Used Count', readonly=False, default=0)


    @api.constrains('apply_for_employee', 'employee_id', 'state', 'effective_date_from', 'effective_date_to')
    def _check_overlap_coupon_apply_for_employee(self):
        """ Two coupons in state [Create | Open | Close] cannot overlap """
        overlap = False
        message = _('List of employees have issued a coupon code:')
        for coupon_id in self.filtered(lambda c: c.apply_for_employee and c.employee_id and c.state in ['Create', 'Open', 'Close'] and c.effective_date_from and c.effective_date_to):
            domain = [
                ('id', '!=', coupon_id.id),
                ('apply_for_employee', '=', True),
                ('employee_id', '=', coupon_id.employee_id.id),
                ('state', 'in', ['Create', 'Open', 'Close']),
                ('effective_date_from', '<=', coupon_id.effective_date_to),
                ('effective_date_to', '>', coupon_id.effective_date_from)
            ]
            coupon_overlap_id = self.sudo().search(domain, limit=1)
            if coupon_overlap_id:
                overlap = True
                message += '\n'
                message += ' - %s: %s (%s - %s)' % (coupon_overlap_id.employee_id.display_name, coupon_overlap_id.publish_id and coupon_overlap_id.publish_id.display_name or '', format_date(self.env, coupon_overlap_id.effective_date_from, lang_code=self.env.user.lang or 'vi_VN'), format_date(self.env, coupon_overlap_id.effective_date_to, lang_code=self.env.user.lang or 'vi_VN'))
        if overlap:
            raise ValidationError(message)
    
        
    