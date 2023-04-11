# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare, float_round


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_purchase_order(self, company_id, origins, values):
        res = super(StockRule, self)._prepare_purchase_order(company_id, origins, values)
        values = values[0]
        res.update({'user_id': self._uid,
                    'warehouse_id': values['warehouse_id'].id,
                    'is_reordered_po': True,
                    'is_no_approval_required': False,
                    })
        type_id = self.env['purchase.type.config'].search([
            ('is_used_for_orderpoint', '!=', False),
        ])
        if type_id:
            res.update({'purchase_type_id': type_id.id,
                        })
        return res

    def _make_po_get_domain(self, company_id, values, partner):
        domain = super(StockRule, self)._make_po_get_domain(company_id, values, partner)
        if values.get('warehouse_id', False):
            domain += (
                ('warehouse_id', '=', values.get('warehouse_id', False).id),
            )
        domain += (
            ('type', '=', 'purchase'), ('is_reordered_po', '!=', False),
        )
        return domain

    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom,
                                     company_id, values, po):
        res = super(StockRule, self)._prepare_purchase_order_line(product_id,
                                    product_qty, product_uom,
                                    company_id, values, po)
        ctx = self._context.copy()
        product_qty = res.get('product_qty', False) or 0.0
        if ctx.get('orderpoint_qty_multiple', False):
            product_qty = float_round(product_qty/ctx.get('orderpoint_qty_multiple', False),
                                      precision_rounding=1,
                                      )
            product_qty = product_qty*ctx.get('orderpoint_qty_multiple', False)

        if res.get('product_qty', False) and ctx.get('buy_phuclong', False):
            res.update({
                'product_qty': product_qty,
                'qty_request': product_qty,
                'price_unit': 0.0,
            })
        return res

    def _update_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, line):
        res = super(StockRule, self)._update_purchase_order_line(product_id, 
                                                                  product_qty, product_uom, company_id, values, line)
        ctx = self._context.copy()
        product_qty = res.get('product_qty', False) or 0.0
        if ctx.get('orderpoint_qty_multiple', False):
            product_qty = float_round(product_qty/ctx.get('orderpoint_qty_multiple', False),
                                      precision_rounding=1,)
            product_qty = product_qty*ctx.get('orderpoint_qty_multiple', False)
        if res.get('product_qty', False) and ctx.get('buy_phuclong', False):
            res.update({
                'product_qty': product_qty,
                'qty_request': product_qty,
                'price_unit': 0.0,
            })
        return res
