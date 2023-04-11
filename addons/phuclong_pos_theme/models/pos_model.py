# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, SUPERUSER_ID, tools
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
import psycopg2
import logging
_logger = logging.getLogger(__name__)

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class posPayment(models.Model):
    _inherit = 'pos.payment'

    currency_name = fields.Char('Currency Name')
    currency_origin_value = fields.Float('Currency Origin Value')
    amount_change = fields.Float('Change Amount')
    exchange_rate = fields.Float('Exchange Rate', default=1, digits=False)
    voucher_max_value = fields.Float('Value of Voucher')


class posOrder(models.Model):
    _inherit = 'pos.order'

    def _process_payment_lines(self, pos_order, order, pos_session, draft):
        prec_acc = order.pricelist_id.currency_id.decimal_places

        order_bank_statement_lines= self.env['pos.payment'].search([('pos_order_id', '=', order.id)])
        order_bank_statement_lines.unlink()
        
        #Vuong: Add zero cash payment when order has no payment
        if order.state == 'paid' and not len(pos_order['statement_ids']):
            cash_payment_method = pos_session.payment_method_ids.filtered('is_cash_count')[:1]
            if not cash_payment_method:
                raise UserError(_("No cash statement found for this session. Unable to record returned cash."))
            zero_payment_vals = {
                'name': _('Zero Payment'),
                'pos_order_id': order.id,
                'amount': 0,
                'payment_date': fields.Date.context_today(self),
                'payment_method_id': cash_payment_method.id,
            }
            order.add_payment(zero_payment_vals)
        
        for payments in pos_order['statement_ids']:
            if not float_is_zero(payments[2]['amount'], precision_digits=2):
                order.add_payment(self._payment_fields(order, payments[2]))

        order.amount_paid = sum(order.payment_ids.mapped('amount'))

        if not float_is_zero(pos_order['amount_return'], 2):
            payment_cash_available = order.payment_ids.filtered(lambda l: l.amount > pos_order['amount_return']
                                                           and l.payment_method_id.is_cash_count 
                                                           and not l.payment_method_id.use_for_voucher)
            if payment_cash_available:
                payment_to_return = payment_cash_available[0]
                payment_to_return.write({'amount': payment_to_return.amount-pos_order['amount_return'],
                                         'amount_change': pos_order['amount_return']})
            else:
                cash_payment_method = pos_session.payment_method_ids.filtered('is_cash_count')[:1]
                if not cash_payment_method:
                    raise UserError(_("No cash statement found for this session. Unable to record returned cash."))
                return_payment_vals = {
                    'name': _('return'),
                    'pos_order_id': order.id,
                    'amount': -pos_order['amount_return'],
                    'payment_date': fields.Date.context_today(self),
                    'payment_method_id': cash_payment_method.id,
                }
                order.add_payment(return_payment_vals)
            

#     @api.model
    def get_reward_code(self, limit=1, promotion_line_id=False):
#         code = []
        code_obj = self.env['reward.code.info']
        description = ''
        link = ''
        now = self.env['res.users']._convert_user_datetime(fields.Datetime.now()).date()
        reward_publish = self.env['reward.code.publish'].search([
            ('effective_date_from', '<=', now),
            ('effective_date_to', '>=', now),
            ('promotion_ids', 'in', [promotion_line_id])
        ], order='effective_date_from')
        if reward_publish:
            code_ids = reward_publish.reward_code_info_ids
            codes = code_ids.filtered(
                lambda c: not c.pos_order_id and c.state == 'create')
            if codes:
                if limit > len(codes):
                    limit = len(codes)
                for c in range(limit):
                    if codes[c]:
#                         code.append(codes[c].name)
                        code_obj |= codes[c]
                description = codes[0].reward_code_publish_id.description
                link = codes[0].reward_code_publish_id.reward_link
        return code_obj, description, link

    @api.model
    def update_set_done_reward_code(self, limit, order_name, promotion_line_id):
        updated_reward = self.env['reward.code.info'].search([
            ('pos_order_id', '=', order_name)],
            limit=1) or False
        if updated_reward:
            return True
        
        code_updates, description, link = self.get_reward_code(limit, promotion_line_id)
        if len(code_updates) == limit:
            code_updates.sudo().write({
                'pos_order_id': order_name,
                'state': 'close'
            })
            return [x.name for x in code_updates], description, link
        else:
            return False

    @api.model
    def get_available_warehouse_callcenter(self):
        warehouse_list = []
        session_ids = self.env['pos.session'].sudo().search([('config_id.is_callcenter_pos','=',False),('state','=','opened')])
        warehouses = []
        for session in session_ids:
            start_at = self.env['res.users']._convert_user_datetime(session.create_date)
            now = self.env['res.users']._convert_user_datetime(fields.Datetime.now())
            if start_at.date() != now.date():
                continue
            config = session.config_id
            if config.sale_type_ids.filtered(lambda l: l.use_for_call_center):
                warehouse = config.warehouse_id
                if warehouse.id not in warehouses:
                    warehouses.append(warehouse.id)
                    warehouse_list.append({'id':warehouse.id,
                                           'display_name':warehouse.display_name,
                                           'code':warehouse.code})
        return warehouse_list
    
    @api.model
    def get_session_by_warehouse_callcenter(self, warehouse_id):
        session_ids = self.env['pos.session'].sudo().search([('config_id.is_callcenter_pos','=',False),('state','=','opened'),('config_id.warehouse_id','=',warehouse_id)])
        for session in session_ids:
            start_at = self.env['res.users']._convert_user_datetime(session.create_date)
            now = self.env['res.users']._convert_user_datetime(fields.Datetime.now())
            if start_at.date() != now.date():
                continue
            config = session.config_id
            if config.sale_type_ids.filtered(lambda l: l.use_for_call_center):
                product_lock = self.get_product_lock_by_warehouse(warehouse_id)
                return session.id, product_lock
        return False
    
    @api.model
    def get_product_lock_by_warehouse(self, warehouse_id):
        lock_product = self.env['pos.product.lock'].sudo().search([('warehouse_id','=',warehouse_id)])
        if lock_product:
            return lock_product[0].product_ids.ids
        else:
            return []

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
            ('config_id', '=', session.config_id.id)
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
                    'order_in_call_center': item.order_in_call_center,
                    'label':item.note_label
                })
        
        #Các đơn hàng đã thanh toán        
        domain = [
            ('state', 'in', ['paid', 'done', 'invoiced']),
            '|', 
            ('session_callcenter_id', '=', session_id),
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
                    'is_draft_order': False,
                    'order_in_call_center':item.order_in_call_center,
                    'label':item.note_label
                })
        return result
    
    @api.model
    def get_mobile_order_by_query(self, query, session_id, orderby='date_order desc'):
        return
    
    @api.model
    def check_draft_order(self, session_id):
        session = self.env['pos.session'].browse(session_id)
        draft_order_domain = [
            ('state', '=', 'draft'),
            ('config_id', '=', session.config_id.id)
        ]
        draft_orders = self.sudo().search(draft_order_domain)
        return len(draft_orders) or 0

    @api.depends('date_first_order', 'date_last_order')
    def _hanging_time(self):
        for order in self:
            if order.date_first_order and order.date_last_order:
                date_order = order.date_last_order
                start_order = order.date_first_order
                time = date_order - start_order
                hanging_time_to_seconds = time.total_seconds()
                hanging_time_to_hours = hanging_time_to_seconds / 3600

                order.hanging_time = abs(hanging_time_to_hours)
#                 order.date_first_order -= timedelta(hours=7)
            else:
                order.hanging_time = 0

    number_of_printed_bill = fields.Integer(
        string='Number of Printed Bill', default=1)
    date_first_order = fields.Datetime(
        string='Date First Order', readonly=True)
    date_last_order = fields.Datetime(
        string='Date Last Order', readonly=True)
    hanging_time = fields.Float(
        'Hanging Time', compute='_hanging_time', store=True)
    reward_code = fields.Char('Reward Code')
    cancel_reason = fields.Text()
    pay_draft_order = fields.Boolean(default=False)
    order_in_call_center = fields.Boolean('Order in Call Center', default=False)
    session_callcenter_id = fields.Many2one('pos.session', string="Session Call Center")
    cc_is_timer = fields.Boolean(' Is Timer ?', default=False)
    cc_delivery_time = fields.Datetime('Delivery Time')
    
    invoice_name = fields.Char('Company/Person Name', tracking=True)
    invoice_vat = fields.Char('VAT No.', tracking=True)
    invoice_address = fields.Char('Address', tracking=True)
    invoice_email = fields.Char('Email', tracking=True)
    invoice_contact = fields.Char('Contact Info', tracking=True)
    invoice_note = fields.Char('Note', tracking=True)
    invoice_request = fields.Boolean('Request for VAT', tracking=True)

    @api.model
    def set_count_of_print_bill(self, name):
        pos_order = self.env['pos.order'].sudo().search([
            ('pos_reference', '=', name)])
        self._cr.execute('''
            update pos_order set number_of_printed_bill = %s where id= %s
        ''' % (pos_order.number_of_printed_bill + 1, pos_order.id))
        self._cr.commit()
        return (pos_order.number_of_printed_bill + 1)

    @api.model
    def _order_fields(self, ui_order):
        fields = super(posOrder, self)._order_fields(ui_order)
        if ui_order.get('date_first_order', False):
            fields['date_first_order'] = ui_order['date_first_order'].replace('T', ' ')[:19]
        if ui_order.get('date_last_order', False):
            fields['date_last_order'] =  ui_order['date_last_order'].replace('T', ' ')[:19]
        fields['reward_code'] = ui_order.get('reward_code', False)
        fields['has_printed_label_first'] = ui_order.get(
            'has_printed_label_first', False)
        fields['linked_draft_order_be'] = ui_order.get(
            'linked_draft_order_be', False)
        fields['pay_draft_order'] = ui_order.get('pay_draft_order', False)
        fields['order_in_call_center'] = ui_order.get('order_in_call_center', False)
        if ui_order.get('order_in_call_center', False) and ui_order.get('session_callcenter_id', False):
            fields['session_id'] = ui_order.get('session_callcenter_id', False)
            fields['session_callcenter_id'] = ui_order.get('pos_session_id', False)
        
        fields['invoice_name'] = ui_order.get('invoice_name', False)
        fields['invoice_vat'] = ui_order.get('invoice_vat', False)
        fields['invoice_address'] = ui_order.get('invoice_address', False)
        fields['invoice_email'] = ui_order.get('invoice_email', False)
        fields['invoice_contact'] = ui_order.get('invoice_contact', False)
        fields['invoice_note'] = ui_order.get('invoice_note', False)
        fields['invoice_request'] = ui_order.get('invoice_request', False)
        
        return fields
    
    @api.model
    def get_order_by_name(self, order_name):
        self._cr.execute(''' SELECT po.*, ll.level_name loyalty_level_name, sph.name promotion_name, hr.name cashier_name
                             FROM pos_order po LEFT JOIN hr_employee hr on po.cashier_id = hr.id
                             LEFT JOIN sale_promo_header sph on po.promotion_id = sph.id
                             LEFT JOIN loyalty_level ll on po.partner_loyalty_level_id = ll.id
                             WHERE pos_reference like '%s' and po.state in ('paid','done','invoiced') limit 1
                        '''%(order_name))
        result = self._cr.dictfetchall()
        if result:
            return_order = result
            self._cr.execute('''
                        SELECT pol.*, sph.name promotion_name, sph2.name promotion_condition_name,
                        pt.name product_name, pp.default_code, uu.name product_uom,
                        lr.name reward_name, spc.name combo_name FROM pos_order_line pol
                        JOIN product_product pp on pol.product_id = pp.id
                        JOIN product_template pt on pp.product_tmpl_id = pt.id
                        LEFT JOIN uom_uom uu on pol.uom_id = uu.id
                        LEFT JOIN sale_promo_header sph on pol.promotion_id = sph.id
                        LEFT JOIN sale_promo_header sph2 on pol.promotion_condition_id = sph2.id
                        LEFT JOIN sale_promo_combo spc on pol.combo_id = spc.id
                        LEFT JOIN loyalty_reward lr on pol.reward_id = lr.id
                        WHERE order_id = %s
                    '''%(str(return_order[0].get('id'))))
            orderlines = [x for x in self._cr.dictfetchall()]
            self._cr.execute('''
                        SELECT pp.*, ppm.name method_name, ppm.use_for FROM pos_payment pp 
                        JOIN pos_payment_method ppm on pp.payment_method_id = ppm.id
                        WHERE pos_order_id = %s order by id
                    '''%(str(return_order[0].get('id'))))
            paymentlines = [x for x in self._cr.dictfetchall()]
#             self._cr.execute('''
#                         SELECT hr.name
#                         FROM hr_employee hr
#                         JOIN pos_session ps ON hr.id = ps.cashier_id
#                         JOIN pos_order po ON ps.id = po.session_id and po.id = %s
#                     '''%(return_order[0]['id']))
            cashier_name = return_order[0].get('cashier_name', '')
            partner_vals = []
            if return_order[0].get('partner_id'):
                self._cr.execute('''
                            SELECT rp.*, ci.date_expired FROM res_partner rp
                            LEFT JOIN cardcode_info ci ON rp.id = ci.partner_id
                            WHERE rp.id = %s
                        '''%(str(return_order[0].get('partner_id'))))
                partner_vals = [x for x in self._cr.dictfetchall()]
#             self._cr.execute('''
#                         SELECT * FROM pos_order_line 
#                         WHERE order_id = %s and linked_order_line_id is null
#                     '''%(str(return_order[0].get('id'))))
#             orderlines = [x for x in self._cr.dictfetchall()]
            
            self = self.sudo()
            config_id = self.env['pos.session'].browse(return_order[0].get('session_id')).config_id
            return_order[0]['config_id'] = config_id.id
            return_order[0]['receipt_header'] = config_id.receipt_header
            return_order[0]['receipt_footer'] = config_id.receipt_footer
            return_order[0]['is_dollar_pos'] = config_id.is_dollar_pos
            return_order[0]['logo'] = config_id.logo
            
            return return_order, orderlines, paymentlines, cashier_name, partner_vals
        else:
            return False
    
    @api.model
    def get_order_config_logo_by_name(self, order_name):    
        config_id = self.env['pos.order'].search([('name','=',order_name)], limit=1).session_id.config_id
        return config_id.id, config_id.receipt_footer

    @api.model
    def _process_order(self, order, draft, existing_order):
        order = order['data']
        # if order['has_printed_label_first'] and order['linked_draft_order_be'] and \
        if order['linked_draft_order_be'] and \
            not order['pay_draft_order'] and order['state'] == 'draft' and not draft:
            draft = True
        pos_session = self.env['pos.session'].browse(order['pos_session_id'])
        if pos_session.state in ['closing_control', 'closed']:
            order['pos_session_id'] = self._get_valid_session(order).id

        pos_order = False
        # if order['has_printed_label_first'] and order['linked_draft_order_be']:
        if order['linked_draft_order_be']:
            order_to_write = self.env['pos.order'].search([
                ('name', '=', order['linked_draft_order_be']),('state','!=','cancel')])
            #remove dupplicate order
            if len(order_to_write) > 1:
                for order_dup in order_to_write:
                    if order_dup != order_to_write[0]:
                        # order_dup.cancel_order()
                        order_dup = order_dup.with_user(SUPERUSER_ID)
                        order_dup.write({'cancel_duplicate': True,
                                     'cancel_from_be': False,
                                     'state':'cancel'})
                        if order_dup.picking_id:
                            if order_dup.picking_id.state == 'done':
                                order_dup.picking_id.action_reopen_done()
                            order_dup.picking_id.action_cancel()
                            order_dup.picking_id.unlink()
                            
                order_to_write = order_to_write[0]
            if order_to_write and existing_order:
                if order_to_write.name == existing_order.name:
                    pos_order = existing_order
                if not order['pay_draft_order']:
                    return pos_order.id
            else:
                pos_order = self.create_order(order)
        else:
            if not existing_order:
                pos_order = self.create_order(order)
            else:
                pos_order = existing_order
                pos_order.lines.unlink()
                order['user_id'] = pos_order.user_id.id
                pos_order.write(self._order_fields(order))

        self._process_payment_lines(order, pos_order, pos_session, draft)

        if not draft:
            try:
                pos_order.refresh()
                pos_order.action_pos_order_paid()
                #Vuong: create loyalty point history and update to partner
                pos_order.action_pos_update_point()
                #create picking
                line_to_create_picking = self.env['ir.config_parameter'].sudo().get_param(
                    'maximum_orderline_create_picking_pos_direct', 0,
                )
                line_to_create_picking = int(line_to_create_picking)
                if line_to_create_picking and line_to_create_picking > 0 and len(order.get('lines', [])) <= line_to_create_picking:
                    pos_order.with_user(SUPERUSER_ID).create_picking(order['name'])
            except psycopg2.DatabaseError:
                # do not hide transactional errors, the order(s) won't be saved!
                raise
            except Exception as e:
                _logger.error('Could not fully process the POS Order: %s', tools.ustr(e))

        if pos_order.to_invoice and pos_order.state == 'paid':
            pos_order.action_pos_order_invoice()

        return pos_order.id
    
    def cancel_order(self):
        result = super(posOrder, self).cancel_order()
        for pos_order in self:
            if pos_order.state == 'cancel' and pos_order.order_in_call_center:
                order_count = self.check_draft_order(pos_order.session_id.id)
                pos_order.session_id.config_id._send_to_channel('pos.longpolling', ['callcenter', order_count])
        return result
    
    def create_order(self, order):
        values = self._order_fields(order)
        if values.get('order_in_call_center', False):
            pos_order = self.with_user(SUPERUSER_ID).create(values)
            #Notify from call center pos
            order_count = self.check_draft_order(pos_order.session_id.id)
            pos_order.session_id.config_id._send_to_channel('pos.longpolling', ['callcenter', order_count])
        else:
            pos_order = self.create(values)
        return pos_order

    @api.model
    def get_order_to_pay(self, order_name):
        order = self.search_read([('name', 'ilike', order_name)], [])
        if order:
            order_id = order and order[0].get('id')
            orderlines = self.env['pos.order.line'].search_read([
                ('order_id', '=', order_id)
            ], [])
            for line in orderlines:
                if line.get('option_ids', False):
                    options_values = []
                    for option_id in line.get('option_ids', False):
                        option = self.env['pos.order.line.option'].browse(option_id)
                        options_values.append({'option_id':option.option_id.id,
                                               'option_type':option.option_type})
                    line.update({'option_ids': options_values})
            return {
                'order': order and order[0],
                'orderlines': orderlines
            }
        else:
            return False
        
    def update_existing_order(self, order):
        return False

    @api.model
    def create_from_ui(self, orders, draft=False):
        order_ids = []
        for order in orders:
            existing_order = False
            if 'server_id' in order['data']:
                existing_order = self.env['pos.order'].search([
                    '|',
                    ('id', '=', order['data']['server_id']),
                    ('pos_reference', '=', order['data']['name'])
                ], limit=1)
            # Thai: Nếu POS Config được set là Sanbox
            # thì set existing_order = False
            # để tạo nhiều đơn hàng giống nhau
            session_id = order['data']['pos_session_id']
            config = self.env['pos.session'].search([
                ('id', '=', session_id)]).config_id
            if config.is_sandbox_env:
                existing_order = False
            if (existing_order and existing_order.state == 'draft') or not existing_order:
                if order['data']['state'] == 'cancel' and existing_order.state == 'draft':
                    existing_order.state = 'cancel'
                else:
                    order_ids.append(
                        self._process_order(order, draft, existing_order))
                    # Thái: Update lại thông tin ca bán hàng, mã tham chiếu đơn hàng
                    # cho các đơn treo ca trước
                    if existing_order:
                        existing_order.sudo().write({
                            'session_id': order['data']['pos_session_id'],
                            'name': order['data']['name'],
                            'pos_reference': order['data']['name'],
                            'note_label': order['data']['note_label'],
                            'has_printed_label_first': order['data']['has_printed_label_first'],
                            'date_last_order': datetime.now(),
                        })
#                         #Vuong: create loyalty point history and update to partner
#                         if existing_order.state == 'paid':
#                             existing_order.action_pos_update_point()
            #Create Log
            else:
                if not self.update_existing_order(order):
                    self.env['pos.order.duplicate.log'].create({'warehouse_id': config.warehouse_id and config.warehouse_id.id or False,
                                                                'name': order['data']['name'],
                                                                'date_order': order['data']['creation_date'].replace('T', ' ')[:19],
                                                                'amount_total': order['data']['amount_total'],
                                                                'log_data':order['data']})
                
        return self.env['pos.order'].search_read(
            domain=[('id', 'in', order_ids)],
            fields=['id', 'pos_reference']
        )

    def unlink(self):
        for order in self:
            if order.state in ['draft'] and order.has_printed_label_first:
                raise UserError(_('You can not delete this order because the label of this one was printed.'))
        return super(posOrder, self).unlink()

    @api.model
    def _payment_fields(self, order, ui_paymentline):
        fields = super(posOrder, self)._payment_fields(order, ui_paymentline)
        fields['currency_name'] = ui_paymentline['currency_name']
        fields['currency_origin_value'] = ui_paymentline['currency_origin_value']
        fields['exchange_rate'] = ui_paymentline['exchange_rate']
        fields['voucher_max_value'] = ui_paymentline['voucher_max_value']
        return fields
    
    @api.model
    def check_cashless_code(self, cashless_code):
        cardcode = self.env['cardcode.info'].search([('appear_code','=',cashless_code),('card_type','=','partner'),
                                                      ('state','=','using'),('partner_id.use_for_on_account','=',True),
                                                      ('date_created','=',False),('date_expired','=',False)], limit=1)
        if cardcode:
            return True
        else:
            return False
        
    @api.model
    def update_cashless_code(self, cashless_code_list, order_name):
        updated_code = self.env['cardcode.info'].search([('order_reference','=',order_name)],limit=1) or False 
        if updated_code:
            return True
        
        update_list = []
        #Check first
        for code in cashless_code_list:
            cashless_code = code[0]
            cardcode = self.env['cardcode.info'].search([('appear_code','=',cashless_code),('card_type','=','partner'),
                                                          ('state','=','using'),('partner_id.use_for_on_account','=',True),
                                                          ('date_created','=',False),('date_expired','=',False)], limit=1)
            if cardcode:
                update_list.append([cardcode, code[1]])
            else:
                return False
        
        #Update later
        today = self.env['res.users']._convert_user_datetime(
                        datetime.utcnow().strftime(DATETIME_FORMAT)).date()
        return_info = []
        for list in update_list:
            date_expired = today + relativedelta(days=list[1])
            code_update = list[0]
            code_update.with_user(SUPERUSER_ID).write({'date_created': today,
                               'date_expired': date_expired,
                               'order_reference': order_name})
            return_info.append([code_update.hidden_code, date_expired])
        return return_info        
    
    @api.model
    def update_done_product_coupon_code(self, product_coupon_code_list, order_name):
        updated_code = self.env['crm.voucher.info'].search([('product_coupon_order_ref','=',order_name)],limit=1) or False 
        if updated_code:
            return True
        
        update_list = []
        #Check first
        for code in product_coupon_code_list:
            coupon_code = code[0]
            coupon = self.env['crm.voucher.info'].search([('ean','=',coupon_code),('type','=','coupon'),('state','=','Create'),('publish_id.apply_for_themos_cup_promo','=',True),
                                                        ('effective_date_from','=',False),('effective_date_to','=',False)], limit=1)
            if coupon:
                update_list.append([coupon, code[1]])
            else:
                return False
        
        #Update later
        today = self.env['res.users']._convert_user_datetime(
                        datetime.utcnow().strftime(DATETIME_FORMAT)).date()
        for list in update_list:
            date_expired = today + relativedelta(days=list[1])
            code_update = list[0]
            code_update.with_user(SUPERUSER_ID).write({'effective_date_from': today,
                               'effective_date_to': date_expired,
                               'product_coupon_order_ref': order_name})
        return True
    
    
