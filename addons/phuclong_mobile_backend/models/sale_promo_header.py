from odoo import models, fields, api, SUPERUSER_ID, _
import json
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class SalePromoHeader(models.Model):
    _inherit = 'sale.promo.header'

    # @api.model
    # def check_coupon_apply(self, coupon_code, search_type, backend_id):
    #     data = super(SalePromoHeader, self).check_coupon_apply(
    #         coupon_code, search_type, backend_id)
    #     if data and len(data) and data[0] not in ['date', 'count']:
    #         code = str(coupon_code['code'])
    #         criteria = [('ean', '=', code), ('type', '=', search_type)]
    #         voucher_pool = self.env['crm.voucher.info']
    #         coupon_apply = voucher_pool.search(criteria, limit=1)
    #         if coupon_apply:
    #             if coupon_apply.publish_id and coupon_apply.publish_id.apply_only_on_app and not self._context.get('from_mobile_app', False):
    #                 return []
    #             lock_voucher_id = self.env['crm.voucher.lock'].check_lock_voucher(
    #                 code)
    #             if lock_voucher_id:
    #                 used_count = coupon_apply.used_count + 1
    #                 if used_count >= coupon_apply.usage_limits:
    #                     result = []
    #                     order = lock_voucher_id.order_id
    #                     result.append('count')
    #                     result.append(used_count)
    #                     result.append(order and order.name or '')
    #                     order_warehouse = ''
    #                     order_date = ''
    #                     if order:
    #                         order_warehouse = order.warehouse_id and order.warehouse_id.name or ''
    #                         order_date = fields.Datetime.context_timestamp(
    #                             self, order.date_order)
    #                         order_date = order_date.strftime(
    #                             '%H:%M:%S %d-%m-%Y')
    #                     result.append(order_warehouse)
    #                     result.append(order_date)
    #                     return result
    #     return data

    def check_promo_is_apply(self, promo_line_id, product_id, date):
        if promo_line_id.start_date_active > date.date() or promo_line_id.end_date_active < date.date():
            return False
        if promo_line_id.product_attribute == 'product_template':
            if promo_line_id.product_tmpl_id.id != product_id.id:
                return False
        elif promo_line_id.product_attribute == 'combo':
            if product_id.id not in promo_line_id.product_ids.ids:
                return False
        elif promo_line_id.product_attribute == 'cat':
            if product_id.categ_id.id not in json.loads(promo_line_id.categories_dom):
                return False
        return True

    def check_promo_product(self, product_id, sale_type_id, warehouse_id, date):
        res = []
        promo_ids = self.sudo().search([('sale_type_ids', '=', sale_type_id), ('state', '=', 'approved'),
                                        ('start_date_active',
                                         '<=', str(date)[0:11]),
                                        ('end_date_active',
                                         '>=', str(date)[0:11]),
                                        '|', ('apply_type', '=',
                                              'all_warehouse'),
                                        '&', ('apply_type', '=',
                                              'select_warehouse'),
                                        ('warehouse_ids', '=', warehouse_id.id)])
        for promo_id in promo_ids:
            if promo_id.list_type == 'PRO':
                promo_lines = promo_id.promo_line
            else:
                promo_lines = promo_id.discount_line
            for promo_line_id in promo_lines:
                if self.check_promo_is_apply(promo_line_id, product_id, date):
                    apply_to_products = []
                    if promo_line_id.benefit_type == 'product_template':
                        apply_to_products.append({
                            'product_id': promo_line_id.benefit_product_tmpl_id.id,
                            'product_name': promo_line_id.benefit_product_tmpl_id.name,
                            'eng_name': promo_line_id.benefit_product_tmpl_id.eng_name,
                            'size': promo_line_id.benefit_product_tmpl_id.size_id.name,
                            'price': promo_line_id.benefit_product_tmpl_id.list_price,
                        })
                    else:
                        if promo_line_id.benefit_type == 'cat':
                            product_ids = self.env['product.template'].sudo().search(
                                [('categ_id', 'in', json.loads(promo_line_id.benefit_categories_dom))])
                        else:
                            product_ids = promo_line_id.benefit_product_tmpl_ids
                        for product in product_ids:
                            apply_to_products.append({
                                'product_id': product.id,
                                'product_name': product.name,
                                'eng_name': product.eng_name,
                                'size': product.size_id.name,
                                'price': product.list_price,
                            })
                    res.append({
                        'name': promo_id.name or '',
                        'start_date': promo_line_id.start_date_active,
                        'end_date': promo_line_id.end_date_active,
                        'type': promo_line_id.modify_type,
                        'discount_value': promo_line_id.discount_value or False,
                        'condition': promo_line_id.volume_type,
                        'operator': promo_line_id.operator,
                        'condition_value': promo_line_id.value_from,
                        'apply_to_products': apply_to_products
                    })
        return res
