# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError, AccessError, ValidationError
from datetime import datetime

class PosOrder(models.Model):
    _inherit = 'pos.order'
    
    create_picking_error_log = fields.Char('Picking Create Error Log')
    cancel_duplicate = fields.Boolean(default=False)
    
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        user_admin = self.env.ref('base.user_admin')
        if self.env.user.id not in (user_admin.id, SUPERUSER_ID):
            args += [('cancel_duplicate', '!=', True)]
        return super(PosOrder, self).search(args, offset, limit, order, count=count)
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        user_admin = self.env.ref('base.user_admin')
        if self.env.user.id not in (user_admin.id, SUPERUSER_ID):
            domain += [('cancel_duplicate', '!=', True)]
        return super(PosOrder, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
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
            GROUP BY po.id, pol.id
            ORDER BY po.id
            LIMIT 100
        '''
        return sql
    
    @api.model
    def auto_create_picking(self):
        #Vuong: check duplicate order and cancel it
        self._cr.execute('''
            SELECT pos_reference, COUNT(*) FROM pos_order WHERE state != 'cancel' GROUP BY pos_reference HAVING COUNT(*) > 1;
        ''')
        for i in self._cr.dictfetchall():
            try:
                order_duplicate = self.env['pos.order'].sudo().search([('pos_reference','=', i['pos_reference'])])
                
                for order in order_duplicate:
                    if order != order_duplicate[0]:
                        # order.cancel_order()
                        order.write({'cancel_duplicate': True,
                                     'cancel_from_be': False,
                                     'state':'cancel'})
                        if order.picking_id:
                            if order.picking_id.state == 'done':
                                order.picking_id.action_reopen_done()
                            order.picking_id.action_cancel()
                            order.picking_id.unlink()
                        if order.session_id.state in ('closing_control', 'closed'):
                            order.session_id.recompute_bank_amount()
                self._cr.commit()
            except Exception as ex:
                print(ex)
                pass
            
        #Vuong: check picking in order duplicate and delete it
        order_duplicate_has_pick = self.env['pos.order'].sudo().search([('cancel_duplicate','=', True),('state','=', 'cancel'),('picking_id','!=', False)])
        for order in order_duplicate_has_pick:
            if order.picking_id.state == 'done':
                order.picking_id.action_reopen_done()
            order.picking_id.action_cancel()
            order.picking_id.unlink()
        
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
    
    def _force_picking_done(self, picking):
        self.ensure_one()
        picking = picking.with_context(disable_merge_move=True)
        if picking.state != 'assigned':
            if self.return_origin and picking.has_tracking and picking.picking_type_id.code == 'return_customer':
                pos_orig_id = self.env['pos.order'].sudo().search([('pos_reference','=', self.return_origin)])
                picking_ids = pos_orig_id.mapped('picking_id')
    
                pos_returned_ids = self.env['pos.order'].sudo().search([('return_origin','=', self.return_origin), ('id','!=', self.id)])
                picking_returned_ids = pos_returned_ids.mapped('picking_return_id')
                
                picking.action_assign_return(picking_ids=picking_ids, picking_returned_ids=picking_returned_ids, move_ids=None, move_returned_ids=None)
            else:
                picking.force_assign_pos()
            for move_line in picking.move_line_ids:
                if move_line.product_uom_qty != 0 and move_line.qty_done != move_line.product_uom_qty:
                    move_line.with_context(bypass_reservation_update=True).write({'qty_done':move_line.product_uom_qty})
            # Duy: Core đã có hàm set lot
            # wrong_lots = self.set_pack_operation_lot(picking)
            # if not wrong_lots:
        picking.with_context(bypass_reservation_update=True).action_done()
    
    def prepare_move_value(self, warehouse_id, location_id, destination_id, picking_type, orderline, quantity, product, has_missed_custom_material_config=False):
        return_pick_type = picking_type.return_picking_type_id or picking_type
        vals = {
            'name': orderline.name,
            'product_uom': product.uom_id.id,
            'product_id': product.id,
            'product_uom_qty': quantity,
            'state': 'draft',
            'location_id': location_id if quantity > 0 else destination_id,
            'location_dest_id': destination_id if quantity > 0 else location_id,
            'picking_type_id': picking_type.id if quantity > 0 else return_pick_type.id,
            'warehouse_id': warehouse_id,
            'pos_order_line_id':orderline.id,
            'has_missed_custom_material_config':has_missed_custom_material_config
        }
        return vals
    
    def create_picking(self, order_name=False):
        """Create a picking for each order and validate it."""
        Picking = self.env['stock.picking']
        StockWarehouse = self.env['stock.warehouse']
        for order in self:
            order_name_picking = order_name or order.name
            if order.state == 'cancel':
                continue
#             if not order.lines.filtered(lambda l: l.product_id.product_tmpl_id.type in ['product', 'consu']):
#                 continue
            address = order.partner_id.address_get(['delivery']) or {}
            picking_type = order.picking_type_id
            return_pick_type = order.picking_type_id.return_picking_type_id or order.picking_type_id
            order_picking = Picking
            order_return_picking = Picking
            warehouse_id = order.location_id.warehouse_id.id
            location_id = order.location_id.id
            destination_id = order.partner_id and order.partner_id.property_stock_customer.id
            if not destination_id:
                customerloc, supplierloc = StockWarehouse._get_partner_locations()
                destination_id = customerloc.id
                
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            
            if picking_type and warehouse_id and location_id:
                moves_vars = []
                moves_return_vars = []
                for line in order.lines.filtered(lambda l: l.product_id.product_tmpl_id.type in ['product', 'consu', 'service'] and not float_is_zero(l.qty, precision_rounding=l.product_id.uom_id.rounding)):
                    #Create Move from Service product
                    if line.product_id.product_tmpl_id.type == 'service':
                        if line.product_id.product_tmpl_id.fnb_type not in ('drink', 'food', 'topping'):
                            continue
                        else:
                            #Fixed Material
                            material_ids = line.product_id.product_material_ids or []
                            for material_list in material_ids:
                                material_available = material_list.material_line_ids.filtered(lambda l:l.product_id.type != 'service' and l.product_qty > 0).sorted(key=lambda l: l.sequence)
                                if len(material_available):
                                    material_product = material_available[0]
                                    if line.qty > 0 and len(material_available) > 1:
                                        for material in material_available:
                                            material_pro_id = self.env['product.product'].search([('product_tmpl_id','=',material.product_id.id)],limit=1)
                                            available_qty = self.env['stock.quant']._get_available_quantity(material_pro_id, order.location_id)
                                            if float_compare(available_qty, line.qty*material.product_qty,precision_digits=precision) >= 0:
                                                material_product = material
                                                break
                                    material_product_id = self.env['product.product'].search([('product_tmpl_id','=',material_product.product_id.id)],limit=1)
                                    material_quantity = line.qty*material_product.product_qty
                                    single_materal_move_vals = self.prepare_move_value(warehouse_id, location_id, destination_id, picking_type, line, material_quantity, material_product_id)
                                    if material_quantity >= 0:
                                        moves_vars.append((0,0,single_materal_move_vals))
                                    else:
                                        moves_return_vars.append((0,0,single_materal_move_vals))
                                        
                            #Cup and Lid by product
                            if line.cup_type and order.sale_type_id:
                                cup_line = False
                                cup_default = line.product_id.product_tmpl_id.cup_ids.filtered(lambda l: l.sale_type_id == order.sale_type_id and l.cup_line_ids)
                                if cup_default:
                                    cup_line = cup_default[0].cup_line_ids.filtered(lambda l: l.cup_type == line.cup_type).sorted(key=lambda l: l.sequence)
                                if cup_line:
                                    cup_product = cup_line[0]
                                    if line.qty > 0 and len(cup_line) > 1:
                                        for cup in cup_line:
                                            cup_pro_id = self.env['product.product'].search([('product_tmpl_id','=',cup.cup_id.id)],limit=1)
                                            available_qty = self.env['stock.quant']._get_available_quantity(cup_pro_id, order.location_id)
                                            if float_compare(available_qty, line.qty, precision_digits=precision) >= 0:
                                                cup_product = cup
                                                break
                                    cup_product_id = self.env['product.product'].search([('product_tmpl_id','=',cup_product.cup_id.id)],limit=1)
                                    if len(cup_product_id):
                                        single_cup_move_vals = self.prepare_move_value(warehouse_id, location_id, destination_id, picking_type, line, line.qty, cup_product_id)
                                        if line.qty >= 0:
                                            moves_vars.append((0,0,single_cup_move_vals))
                                        else:
                                            moves_return_vars.append((0,0,single_cup_move_vals))
                                        if cup_product_id.lid_id:
                                            lid_product = self.env['product.product'].search([('product_tmpl_id','=',cup_product_id.lid_id.id)],limit=1)
                                            if lid_product:
                                                single_lid_move_vals = self.prepare_move_value(warehouse_id, location_id, destination_id, picking_type, line, line.qty, lid_product)
                                                if line.qty >= 0:
                                                    moves_vars.append((0,0,single_lid_move_vals))
                                                else:
                                                    moves_return_vars.append((0,0,single_lid_move_vals))
                            #Material Option
                            material_option_ids = line.option_ids or []
                            for material_option in material_option_ids:
                                material_available = material_option.option_id.material_line_ids.filtered(lambda l:l.product_id.type != 'service' and l.product_qty > 0).sorted(key=lambda l: l.sequence)
                                if len(material_available):
                                    material_product = material_available[0]
                                    material_vals = {}
                                    if line.qty > 0:
                                        for material in material_available:
                                            has_missed_custom_material_config = False
                                            material_pro_id = self.env['product.product'].search([('product_tmpl_id','=',material.product_id.id)],limit=1)
                                            if not material_pro_id:
                                                continue
                                            custom_qty = material.product_qty
                                            if material_option.option_type != 'normal':
                                                custom_material_qty = self.env['product.custom.material.qty'].search([('material_id','=',material.product_id.id),\
                                                                                                                      ('custom_type','=',material_option.option_type),\
                                                                                                                      ('custom_qty','!=',0)], limit=1)
                                                if not len(custom_material_qty):
#                                                     error = _('Custom Material is not set for product: %s, type: %s'%(normal_option[0].material_id.name, material_option.option_type))
#                                                     order.write({'create_picking_error_log':error})
#                                                     raise UserError(error)
                                                    has_missed_custom_material_config = True
                                                else:
                                                    if material_option.option_type == 'below':
                                                        custom_qty -= custom_material_qty.custom_qty
                                                    else:
                                                        custom_qty += custom_material_qty.custom_qty
                                            
                                                if custom_qty <= 0:
#                                                     error =  _('Custom Material wrong for product: %s, type: %s, qty: %s'%(material_pro_id.name, material_option.option_type, str(custom_qty)))
#                                                     order.write({'create_picking_error_log':error})
#                                                     raise UserError(error)
                                                    custom_qty = 0
                                                
                                            custom_qty = custom_qty*line.qty
                                            
                                            vals_update = {'product_id':material_pro_id,
                                                           'product_qty': custom_qty,
                                                           'has_missed_custom_material_config': has_missed_custom_material_config}
                                            available_qty = self.env['stock.quant']._get_available_quantity(material_pro_id, order.location_id)
                                            if float_compare(available_qty, custom_qty,precision_digits=precision) >= 0:
                                                material_product = material
                                                material_vals = vals_update
                                                break
                                            if(material == material_available[0]):
                                                material_vals = vals_update
                                                
                                    if material_vals:
                                        single_option_move_vals = self.prepare_move_value(warehouse_id, location_id, destination_id, \
                                                                    picking_type, line, material_vals['product_qty'], material_vals['product_id'], \
                                                                    material_vals['has_missed_custom_material_config'])
                                        if line.qty >= 0:
                                            moves_vars.append((0,0,single_option_move_vals))
                                        else:
                                            moves_return_vars.append((0,0,single_option_move_vals))
                                    
                    else:
                        single_move_vals = self.prepare_move_value(warehouse_id, location_id, destination_id, picking_type, line, line.qty, line.product_id)
                        if line.qty >= 0:
                            moves_vars.append((0,0,single_move_vals))
                        else:
                            moves_return_vars.append((0,0,single_move_vals))
                        if line.product_id.spoon_id:
                            spoon_pro_id = self.env['product.product'].search([('product_tmpl_id', '=', line.product_id.product_tmpl_id.spoon_id.id)], limit=1)
                            if spoon_pro_id:
                                single_spoon_move_vals = self.prepare_move_value(warehouse_id, location_id, destination_id, picking_type, line, line.qty, spoon_pro_id)
                                if line.qty >= 0:
                                    moves_vars.append((0,0,single_spoon_move_vals))
                                else:
                                    moves_return_vars.append((0,0,single_spoon_move_vals))
                if moves_vars != [] or moves_return_vars != []:
                    message = _("This transfer has been created from the point of sale session: <a href=# data-oe-model=pos.order data-oe-id=%d>%s</a>") % (order.id, order_name_picking)
                    if moves_vars != []:
                        picking_vals= ({
                            'state': 'draft',
                            'origin': order_name_picking,
                            'partner_id': address.get('delivery', False),
                            'date_done': order.date_order,
                            'responsible': order.user_id.name,
                            'warehouse_id': warehouse_id,
                            'company_id': order.company_id.id,
                            'move_type': 'direct',
                            'note': order.note or "",
                            'picking_type_id': picking_type.id,
                            'location_id': location_id,
                            'location_dest_id': destination_id,
                            'create_from_pos': True,
                            'move_lines': moves_vars,
                            'name': "DTC/" + order_name_picking})
                        try:
                            order_picking = Picking.create(picking_vals)
                            order_picking.message_post(body=message)
                            order.write({'picking_id': order_picking.id})
                        except Exception as e:
                            order_picking_existed = Picking.search([('origin', '=', order_name_picking),('picking_type_id', '=', picking_type.id)], limit=1)
                            if order_picking_existed:
                                order.write({'picking_id': order_picking_existed.id, 'create_picking_error_log':e})
                    if moves_return_vars != []:
                        picking_return_vals = ({
                            'state': 'draft',
                            'origin': order_name_picking,
                            'partner_id': address.get('delivery', False),
                            'date_done': order.date_order,
                            'responsible': order.user_id.name,
                            'warehouse_id': warehouse_id,
                            'company_id': order.company_id.id,
                            'move_type': 'direct',
                            'note': order.note or "",
                            'location_id': destination_id,
                            'location_dest_id': location_id,
                            'picking_type_id': return_pick_type.id,
                            'create_from_pos': True,
                            'move_lines': moves_return_vars})
                        try:
                            order_return_picking = Picking.create(picking_return_vals)
                            order_return_picking.message_post(body=message)
                            order.write({'picking_return_id': order_return_picking.id})
                        except Exception as e:
                            order_picking_existed = Picking.search([('origin', '=', order_name_picking),('picking_type_id', '=', return_pick_type.id)], limit=1)
                            if order_picking_existed:
                                order.write({'picking_return_id': order_picking_existed.id, 'create_picking_error_log':e})
            if order_picking:
                order._force_picking_done(order_picking)
            if order_return_picking:
                order._force_picking_done(order_return_picking)
            if order.create_picking_error_log:
                order.write({'create_picking_error_log':False})

        return True
