# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _, SUPERUSER_ID
from odoo.exceptions import UserError
import time
from datetime import datetime
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    
class PosOrder(models.Model):
    _inherit = 'pos.order'
    
    mobile_receiver_info = fields.Char(compute="_get_mobile_receiver_info", readonly=True, store=True)
    
    @api.depends('name_receiver','phone_number_receiver')
    def _get_mobile_receiver_info(self):
        for record in self:
            mobile_receiver_info = ''
            if record.name_receiver and record.phone_number_receiver:
                mobile_receiver_info = 'Người nhận: ' + record.name_receiver + ' - ' + record.phone_number_receiver
            record.mobile_receiver_info = mobile_receiver_info
    
    @api.model
    def check_mobile_draft_order(self, session_id):
        draft_order_domain = [
            ('state', '=', 'paid'),
            ('order_in_app', '=', True),
            ('order_status_app', '=', 'new'),
            ('session_id', '=', session_id)
        ]
        draft_orders = self.search(draft_order_domain)
        order_name_list = [x.name for x in draft_orders]
        return order_name_list
    
    @api.model
    def check_draft_order(self, session_id):
        session = self.env['pos.session'].browse(session_id)
        draft_order_domain = [
            ('state', '=', 'draft'),
            ('config_id', '=', session.config_id.id),
            ('order_in_app', '=', False),
        ]
        draft_orders = self.sudo().search(draft_order_domain)
        return len(draft_orders) or 0
    
    def notification_pos(self):
        result = super(PosOrder, self).notification_pos()
        session_id = self.session_id.id
        order_name_list = self.check_mobile_draft_order(session_id)
        self.session_id.config_id._send_to_channel('pos.longpolling', ['mobile', order_name_list])
        return True
    
    @api.model
    def get_mobile_order_by_query(self, query, session_id, orderby='order_status_app desc, date_order desc'):
        result = []
        session = self.env['pos.session'].browse(session_id)
        
        #Các đơn hàng đã thanh toán        
        domain = [
            ('state', '=', 'paid'),
            ('order_in_app', '=', True),
            ('order_status_app', '!=', 'cancel'),
            ('session_id', '=', session_id)]
        if query:
            partner_by_query = self.env['res.partner'].search([
                '|',
                '|',
                ('name', 'ilike', query),
                ('mobile', '=', query),
                ('phone', '=', query)
            ])
            sale_type_by_query = self.env['pos.sale.type'].search([
                '|',
                ('name', 'ilike', query),
                ('description', 'ilike', query)
            ])
            domain += [
                '|',
                '|',
                '|',
                ('name', 'ilike', query),
                ('note_label', 'ilike', query),
                ('partner_id', 'in', partner_by_query.ids),
                ('sale_type_id', 'in', sale_type_by_query.ids)
            ]
        orders = self.search(domain, order=orderby)
        if orders:
            for item in orders:
                partner = ''
                if item.partner_id:
                    partner = item.partner_id.name
                result.append({
                    'id': item.id,
                    'order_name': item.name,
                    'partner': partner,
                    'date_order': item.date_order,
                    'amount': item.amount_total,
                    'sale_type': item.sale_type_id.name,
                    'is_draft_order': item.order_status_app == 'new' and True or False,
                    'label':item.note_label,
                    'order_status_app': item.order_status_app,
                })
        return result
    
    @api.model
    def get_order_to_pay(self, order_name):
        result = super(PosOrder, self).get_order_to_pay(order_name)
        if result and result['order']:
            order = self.browse(result['order'].get('id'))
            if order.order_in_app and len(order.payment_ids):
                payment_name = order.payment_ids[0].payment_method_id.name
                result['order']['payment_name'] = payment_name
        return result
    
    @api.model
    def check_mobile_order(self, order_name):
        order = self.search([('name', '=', order_name), ('state', '!=', 'cancel'), ('order_status_app', '!=', 'cancel')]) or False
        return order and True or False
    
    @api.model
    def get_order_by_query(self, query, session_id, orderby='date_order desc'):
        result = []
        session = self.env['pos.session'].browse(session_id)
#         now = datetime.now().date()
#         start_at = datetime.strptime(
#             str(session.start_at), '%Y-%m-%d %H:%M:%S')
#         start_at += timedelta(hours=7)
#         print(start_at, datetime.now())
#         if start_at.date() == now:
        # Thái: Search các đơn hàng nháp của ca trước
        draft_order_domain = [
            ('state', '=', 'draft'),
            ('config_id', '=', session.config_id.id),
            ('order_in_app', '=', False),
        ]
        if query:
            partner_by_query = self.env['res.partner'].search([
                '|',
                '|',
                ('name', 'ilike', query),
                ('mobile', '=', query),
                ('phone', '=', query)
            ])
            sale_type_by_query = self.env['pos.sale.type'].search([
                '|',
                ('name', 'ilike', query),
                ('description', 'ilike', query)
            ])
            draft_order_domain += [
                '|',
                '|',
                '|',
                ('name', 'ilike', query),
                ('note_label', 'ilike', query),
                ('partner_id', 'in', partner_by_query.ids),
                ('sale_type_id', 'in', sale_type_by_query.ids)
            ]
        
        draft_orders_orderby = orderby
        if orderby == 'date_order desc':
            draft_orders_orderby = 'sale_type_id desc, date_order desc'
        
        draft_orders = self.search(
            draft_order_domain, order=draft_orders_orderby)
        if draft_orders:
            for item in draft_orders:
                partner = ''
                if item.partner_id:
                    partner = item.partner_id.name
                result.append({
                    'id': item.id,
                    'order_name': item.name,
                    'partner': partner,
                    'date_order': item.date_order,
                    'amount': item.amount_total,
                    'sale_type': item.sale_type_id.name,
                    'is_draft_order': True,
                    'order_in_call_center':item.order_in_call_center,
                    'label':item.note_label
                })
        
        #Các đơn hàng đã thanh toán        
        domain = [
            ('state', 'in', ['paid', 'done', 'invoiced']),
            '|', 
            ('session_callcenter_id', '=', session_id),
            ('session_id', '=', session_id),
            '|', 
            ('order_in_app', '=', False),
            '&',
            ('order_in_app', '=', True),
            ('order_status_app', '=', 'done'),]
        if query:
            partner_by_query = self.env['res.partner'].search([
                '|',
                '|',
                ('name', 'ilike', query),
                ('mobile', '=', query),
                ('phone', '=', query)
            ])
            sale_type_by_query = self.env['pos.sale.type'].search([
                '|',
                ('name', 'ilike', query),
                ('description', 'ilike', query)
            ])
            domain += [
                '|',
                '|',
                '|',
                ('name', 'ilike', query),
                ('note_label', 'ilike', query),
                ('partner_id', 'in', partner_by_query.ids),
                ('sale_type_id', 'in', sale_type_by_query.ids)
            ]
        orders = self.search(domain, order=orderby)
        if orders:
            for item in orders:
                partner = ''
                if item.partner_id:
                    partner = item.partner_id.name
                result.append({
                    'id': item.id,
                    'order_name': item.name,
                    'partner': partner,
                    'date_order': item.date_order,
                    'amount': item.amount_total,
                    'sale_type': item.sale_type_id.name,
                    'is_draft_order': False,
                    'order_in_call_center':item.order_in_call_center,
                    'label':item.note_label
                })
        return result
    
    def update_existing_order(self, order):
        if 'linked_draft_order_be' in order['data'] and order['data']['linked_draft_order_be'] and \
            'order_in_app' in order['data'] and order['data']['order_in_app']:
            existing_order = self.env['pos.order'].search([
                    '|',
                    ('id', '=', order['data']['server_id']),
                    ('pos_reference', '=', order['data']['linked_draft_order_be'])
                ], limit=1)
            if existing_order:
                if order['data']['state'] == 'cancel':
                    existing_order.write({'state':'cancel',
                                          'order_status_app':'cancel',
                                          'note_label':order['data']['note_label']})
                else:
                    existing_order.write({'order_status_app':'done',
                                          'note_label':order['data']['note_label']})
                    existing_order.action_pos_update_point()
                return True
        return False
    
    def action_pos_update_point(self):
        orders = self.filtered(lambda order: not order.order_in_app)
        if orders:
            return super(PosOrder, orders).action_pos_update_point()
    
    @api.model
    def change_mobile_status(self, config_id, status):
        self._cr.execute('update pos_config set use_for_mobile = %s where id = %s'%(status, config_id))
        return True
    
    def cancel_order(self):
        for order in self:
            if order.order_in_app and not self._context.get('cancel_from_wizard', False):
                action = self.env.ref('phuclong_pos_mobile_order.action_wizard_cancel_pos_order_reason')
                result = action.read()[0]
                return result
        res = super(PosOrder, self).cancel_order()
        return res
    
    def sql_search_order_no_picking(self):
        sql = '''
            SELECT DISTINCT po.id pos_id
            FROM pos_order po
                JOIN pos_order_line pol ON pol.order_id = po.id
                JOIN product_product pp ON pp.id = pol.product_id 
                JOIN product_template pt ON pp.product_tmpl_id = pt.id 
                  
            WHERE po.state in ('paid','done','invoiced') and (order_in_app != true or order_status_app = 'done')
                AND (pt.type IN ('product', 'consu') OR (pt.type = 'service' AND pt.fnb_type IN ('drink', 'food', 'topping')))
                AND po.amount_total >= 0
                AND po.picking_id IS NULL AND po.picking_return_id IS NULL
            GROUP BY po.id, pol.id
            ORDER BY po.id
            LIMIT 100
        '''
        return sql
    
    @api.model
    def _order_fields(self, ui_order):
        fields = super(PosOrder,self)._order_fields(ui_order)
        fields['order_in_app'] = ui_order.get('order_in_app',False)
        return fields
        
class PosSession(models.Model):
    _inherit = 'pos.session'
       
    def action_pos_session_closing_control(self):
        check_condition = self.check_condition_open_cashbox()
        if not check_condition:
            raise UserError(_("Please process Mobile orders before closing the pos session"))
        return super(PosSession, self).action_pos_session_closing_control()
    
    def check_condition_open_cashbox(self):
        for session in self:
            mobile_order = self.env['pos.order'].sudo().search([('session_id', '=', session.id),
                                                               ('state', '=', 'paid'),
                                                               ('order_in_app', '=', True),
                                                               ('order_status_app', '=', 'new')], limit=1)
            if mobile_order:
                return False
        return True
    
    
    
    
        
