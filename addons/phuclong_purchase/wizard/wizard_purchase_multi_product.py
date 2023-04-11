# -*- coding: utf-8 -*-

from odoo import api, models, tools, fields
import logging
import threading
from datetime import datetime

_logger = logging.getLogger(__name__)


class WizardPurchaseMultiProduct(models.TransientModel):
    _name = 'wizard.purchase.multi.product'
    _description = 'Wizard Purchase Multi Product'

    product_ids = fields.Many2many('product.product', string="Products")
    
    def _prepare_purchase_line_values(self, product, purchase):
        purchase_id = purchase.id
        vals = {
            'name': product.description_purchase or product.display_name,
            'product_id': product.id,
            'product_qty': 1,
            'qty_request': 1,
            'price_unit': 0,
            'order_id': purchase_id }
        return vals
    
    def action_add_products(self):
        purchase_id = self._context.get('active_id', False)
        if purchase_id:
            purchase = self.env['purchase.order'].browse(purchase_id)
            for product in self.product_ids:
                purchase_line = self.env['purchase.order.line'].create(self._prepare_purchase_line_values(product, purchase))
                purchase_line.onchange_product_id()
                purchase_line._onchange_quantity()
                if purchase.date_planned:
                    purchase_line.date_planned = purchase.date_planned
                


