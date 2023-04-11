# -*- encoding: utf-8 -*-
from odoo import api, fields, models, SUPERUSER_ID, _
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class ReportCouponVoucher(models.TransientModel):
    _inherit = "report.coupon.voucher"
    
    def get_voucher_info(self, voucher_id):    
        warehouse_dom = ''
        if self.warehouse_ids:
            warehouse_str = ','.join(map(str, [x.id for x in self.warehouse_ids]))
            warehouse_dom = 'and sw.id in (%s)'%(warehouse_str) 
        sql='''
                SELECT cvf.ean , to_char(cvf.publish_date,'dd-mm-YYYY') publish_date, cvf.state, to_char(cvf.effective_date_from,'dd-mm-YYYY') effective_date_from, 
                to_char(cvf.effective_date_to,'dd-mm-YYYY') effective_date_to, cvf.voucher_amount, cvf.used_count, cvf.usage_limits, order_reference,
                sw.name warehouse_name, po.date_order as date_order
                FROM crm_voucher_info cvf JOIN crm_voucher_publish cvp
                ON cvf.publish_id = cvp.id
                LEFT JOIN pos_order po on cvf.order_reference = po.pos_reference
                LEFT JOIN stock_warehouse sw on po.warehouse_id = sw.id
                WHERE cvf.publish_id = (%s) %s
                ORDER BY sw.id
            '''%(voucher_id, warehouse_dom)
        self._cr.execute(sql)
        res = []
        for i in self._cr.dictfetchall():
            if i['date_order']:
                date_order = fields.Date.context_today(self, fields.Datetime.from_string(i['date_order'])).strftime('%d-%m-%Y')
            else:
                date_order = False
            res.append(
               {
               'ean': str(i['ean']),
               'publish_date':i['publish_date'],
               'state':dict(self.env['crm.voucher.info'].with_context(lang=self.env.user.lang)._fields['state']._description_selection(self.with_context(lang=self.env.user.lang).env))[i['state']],
               'ean':i['ean'],
               'effective_date_from':i['effective_date_from'],
               'effective_date_to':i['effective_date_to'],
               'voucher_amount':i['voucher_amount'],
               'limit':i['usage_limits'],
               'usage':i['used_count'],
               'order_ref':i['order_reference'] or False,
               'warehouse_name':i['warehouse_name'] or False,
               'date_order': date_order,
               })
        return res
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
