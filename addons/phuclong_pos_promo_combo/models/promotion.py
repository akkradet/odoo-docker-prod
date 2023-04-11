from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.tools import float_is_zero, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang

from odoo.exceptions import UserError, RedirectWarning
import odoo.addons.decimal_precision as dp
import time
# import xmlrpclib
from datetime import datetime
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class SalePromoHeader(models.Model):
    _description = "Promotion Header"
    _inherit = "sale.promo.header"

    def _get_coupon_employee(self, cardcode_id, effective_date=False):
        if not effective_date:
            effective_date = fields.Date.context_today(self)
        return self.env['crm.voucher.info'].search([
            ('apply_for_employee', '=', True),
            ('employee_id', '=', cardcode_id.employee_id.id),
            ('type', '=', 'coupon'),
            ('state', 'in', ['Create', 'Open', 'Close']),
            ('effective_date_from', '<=', effective_date),
            ('effective_date_to', '>=', effective_date),
        ], limit=1)

    def _get_cardcode_employee(self, code):
        return self.env['cardcode.info'].search([
            ('hidden_code', '=', code),
            ('card_type', '=', 'employee'),
            ('employee_id', '!=', False),
            ('state', '=', 'using')
        ], limit=1)

    @api.model
    def check_coupon_apply(self, coupon_code, search_type, backend_id):
        if search_type == 'coupon':
            code = str(coupon_code['code'])
            cardcode_id = self._get_cardcode_employee(code)
            if cardcode_id:
                coupon_apply = self._get_coupon_employee(cardcode_id)
                if coupon_apply:
                    coupon_code['code'] = coupon_apply.ean
        return super(SalePromoHeader, self).check_coupon_apply(coupon_code, search_type, backend_id)

    @api.model
    def update_set_done_coupon(self, coupon_code, order_name, customer_id, warehouse_id):
        for coupon in coupon_code:
            code = coupon[0]
            cardcode_id = self._get_cardcode_employee(code)
            if cardcode_id:
                coupon_apply = self._get_coupon_employee(cardcode_id)
                if coupon_apply:
                    coupon[0] = coupon_apply.ean
        return super(SalePromoHeader, self).update_set_done_coupon(coupon_code, order_name, customer_id, warehouse_id)
    
    @api.model
    def check_coupon_apply_product(self, code, backend_id):
        date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT).date()
        voucher_pool = self.env['crm.voucher.info']
        result = []
        criteria = [('ean','=',code),('type','=','coupon'),('state','=','Create'),('publish_id.apply_for_themos_cup_promo','=',True),
                    ('effective_date_from','!=',False),('effective_date_to','!=',False)]
        coupon_apply = voucher_pool.search(criteria, limit=1)
        
        if len(coupon_apply) == 0:
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
                order = self.env['pos.order'].with_user(SUPERUSER_ID).search([('pos_reference', '=', coupon_apply.order_reference)], limit=1) or False
                if order:
                    order_warehouse = order.warehouse_id and order.warehouse_id.name or ''
                    order_date = self.env['res.users']._convert_user_datetime(order.date_order.strftime(DATETIME_FORMAT))
                    order_date = order_date.strftime('%H:%M:%S %d-%m-%Y')
                    
            result.append(order_warehouse)
            result.append(order_date)
                    
            return result
        
        pushlish_id = coupon_apply.publish_id
        if backend_id!= False:
            if pushlish_id.apply_type == 'select_warehouse':
                if backend_id not in pushlish_id.warehouse_ids.ids:
                    return []
        
        result.append(0)
        result.append(coupon_apply.effective_date_to)
        result.append(coupon_apply.used_count)
        available_count = coupon_apply.usage_limits - coupon_apply.used_count
        result.append(available_count)
        result.append(pushlish_id.promotion_header_id.id)
            
        return result
