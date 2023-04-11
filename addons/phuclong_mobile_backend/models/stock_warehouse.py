from odoo import models, fields, api, _
from odoo.addons.phuclong_restful_api.common import invalid_response, valid_response
from datetime import datetime
import json

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    def get_product_lock(self, payload):
        product_obj = self.env['product.template'].sudo()
        warehouse_id = self.env['stock.warehouse'].browse(int(payload.get('warehouse_id', 0)))
        product_domain = ['|', '|', '|', ('available_in_mobile', '=', False), ('sale_ok', '=', False), ('available_in_pos', '=', False), ('active', '=', False)]
        res = []
        if warehouse_id:
            lock_product_id = self.env['pos.product.lock'].sudo().search([('warehouse_id', '!=', warehouse_id.id)])
            if lock_product_id:
                product_domain.insert(0, '|')
                product_domain += [('id', 'in', lock_product_id.product_ids.ids)]
            product_ids = product_obj.sudo().search(product_domain)
            res.append(product_ids.ids)
        else:
            return invalid_response("Invalid data", "warehouse_id not in params", 400)
        return valid_response(res)
