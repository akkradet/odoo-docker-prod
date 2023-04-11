# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    barcode_id = fields.Many2one('product.conversion', string='Barcode', domain=[('product_id','=','product_id')])
    ref_code = fields.Char(related='product_id.ref_code',
                           string='Reference Code', readonly=True, store=True)  
    vendor_document = fields.Char(related='picking_id.vendor_document', readonly=True, store=True)
    created_purchase_line_id = fields.Many2one('purchase.order.line',
        'Created Purchase Order Line', ondelete='set null', readonly=True, copy=False, index=True)
    inventory_id = fields.Many2one('stock.inventory', 'Inventory', check_company=True, index=True)
