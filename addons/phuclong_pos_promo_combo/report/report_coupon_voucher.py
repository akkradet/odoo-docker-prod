# -*- encoding: utf-8 -*-
from odoo import api, fields, models, SUPERUSER_ID, _
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class ReportCouponVoucher(models.TransientModel):
    _inherit = "report.coupon.voucher"

    type = fields.Selection(selection_add=[('coupon_for_employee', 'Coupon For Employee')])
    
    def get_voucher_publish(self):
        sql ='''
                SELECT name, publish_date, id
                FROM crm_voucher_publish
                WHERE date(timezone('UTC',publish_date::timestamp)) between '%(date_start)s' and '%(date_end)s'
                AND type = '%(type)s' AND (apply_for_employee is null or apply_for_employee = false)
        '''%({
            'date_start': self.date_start,
            'date_end': self.date_end,
            'type': self.type,
            })
        self._cr.execute(sql)
        res = []
        for i in self._cr.dictfetchall():
            if not len(self.get_voucher_info(i['id'])):
                continue
            res.append(
                   {
                   'id' : i['id'],
                   'name':i['name'],
                   'publish_date':i['publish_date'],
                   })
        return res
    
    def print_report(self):
        if self.type == 'coupon_for_employee':
            return self.env.ref('phuclong_pos_promo_combo.report_coupon_employee').report_action(self)
        else:
            return self.env.ref('besco_voucher_coupon.report_coupon_voucher').report_action(self)
        
    def get_coupon_employee(self):
        sql = '''
        select ci.appear_code employee_code, he.name employee_name, cvi.usage_limits sum_coupon,  
        cvi.used_count coupon_used, (cvi.usage_limits - cvi.used_count) coupon_available
        from crm_voucher_info cvi join crm_voucher_publish cvp on cvi.publish_id  = cvp.id
        join hr_employee he on cvi.employee_id = he.id
        join cardcode_info ci on he.emp_card_id = ci.id
        where cvp.apply_for_employee = true '''
        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        return res
    
    def get_coupon_employee_detail(self):
        sql = '''
        select to_char(timezone('UTC',po.date_order::timestamp), 'DD/MM/YYYY HH24:MI:SS') date_order,
        sw.name store, ci.appear_code employee_code, he.name employee_name, po.name order_ref,  
        pp.display_name product_name, pol.qty product_qty, pol.price_unit unit_price, hec.name cashier_name,
        (pol.price_subtotal_incl - pol.price_unit*pol.qty) discount, pol.price_subtotal_incl total
        from pos_order_line pol join pos_order po on pol.order_id = po.id
        join product_product pp on pol.product_id = pp.id
        join hr_employee hec on po.cashier_id = hec.id
        join stock_warehouse sw on po.warehouse_id = sw.id
        join sale_promo_header sph on pol.promotion_id = sph.id
        join crm_voucher_publish cvp on pol.promotion_id = cvp.promotion_header_id
        join cardcode_info ci on po.emp_coupon_code = ci.hidden_code
        join hr_employee he on ci.employee_id = he.id
        where po.state in ('paid', 'done', 'invoiced') and emp_coupon_code is not null and emp_coupon_code != '' and pol.promotion_id is not null
        and sph.use_for_coupon = true and cvp.apply_for_employee = true
        and timezone('UTC',po.date_order::timestamp) between '%(date_start)s 00:00:00' and '%(date_end)s 23:59:59'
        group by sw.name, ci.appear_code, he.name, po.name, to_char(timezone('UTC',po.date_order::timestamp), 'DD/MM/YYYY HH24:MI:SS'), pp.display_name, pol.qty, pol.price_unit, hec.name, pol.price_subtotal_incl, po.id
        order by employee_code, po.id'''%({'date_start':self.date_start, 'date_end':self.date_end})
        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        return res
    
