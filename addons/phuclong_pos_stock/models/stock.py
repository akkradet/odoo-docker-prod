# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    create_from_pos = fields.Boolean(string='Create From POS', readonly=True, copy=False, default=False)

    @api.model
    def get_picking_info(self, id):
        picking = self.env['stock.picking'].sudo().browse(id)
        user = self.env['res.users'].sudo().browse([self._uid])
        lines = []
        for item in picking.move_line_ids:
            lines.append({
                'product': item.product_id.product_tmpl_id.name,
                'qty': item.qty_done
            })
        values = {
            'user': user.partner_id.name,
            'lines': lines,
            'location_from': picking.location_id.barcode or picking.location_id.display_name,
            'location_to': picking.location_dest_id.barcode or picking.location_dest_id.display_name
        }
        return values


class StockMove(models.Model):
    _inherit = 'stock.move'

    pos_order_line_id = fields.Many2one('pos.order.line', string='Product Order', readonly=True, copy=False)
    has_missed_custom_material_config = fields.Boolean(default=False, readonly=True, copy=False)

    def _action_confirm(self, merge=True, merge_into=False):
        context = self._context or {}
        if context and context.get('disable_merge_move', False):
            merge = False
        return super(StockMove, self)._action_confirm(merge, merge_into)
    
    
class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'
    
    def sql_search_order_no_picking(self):
        sql = '''
            SELECT DISTINCT po.id pos_id
            FROM pos_order po
                JOIN pos_order_line pol ON pol.order_id = po.id
                JOIN product_product pp ON pp.id = pol.product_id 
                JOIN product_template pt ON pp.product_tmpl_id = pt.id 
                  
            WHERE po.state in ('paid','done','invoiced') 
                AND (pt.type IN ('product', 'consu') OR (pt.type = 'service' AND pt.fnb_type IN ('drink', 'food', 'topping')))
                AND po.amount_total >= 0
                AND po.picking_id IS NULL AND po.picking_return_id IS NULL
                AND po.warehouse_id = %s
            GROUP BY po.id, pol.id
            ORDER BY po.id
        '''%(self.id)
        return sql
    
    
    def create_pos_picking(self):
        sql = self.sql_search_order_no_picking()
        #Vuong: create and done picking
        self._cr.execute(sql)
        for i in self._cr.dictfetchall():
            try:
                pos = self.env['pos.order'].sudo().browse(i['pos_id'])
                pos.create_picking()
                self._cr.commit()
            except Exception as ex:
                print(ex)
                pass
        return True
        
        
        
        
