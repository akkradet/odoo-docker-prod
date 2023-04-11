# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _, SUPERUSER_ID
from odoo.exceptions import UserError
import time
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    @api.depends('qty', 'old_price')
    def _compute_old_price_total(self):
        for record in self:
            if record.old_price:
                record.old_price_total = record.old_price * record.qty
            else:
                record.old_price_total = 0.0

    @api.depends('is_loyalty_line', 'is_birthday_promotion', 'loyalty_discount_percent', 'price_unit')
    def _compute_loyalty_gift_type(self):
        for record in self:
            loyalty_gift_type = False
            if record.is_loyalty_line and not record.loyalty_discount_percent and not record.price_unit:
                if record.is_birthday_promotion:
                    loyalty_gift_type = 'birthday_gift'
                else:
                    loyalty_gift_type = 'point_exchange'
            record.loyalty_gift_type = loyalty_gift_type

    partner_id = fields.Many2one('res.partner', related="order_id.partner_id",
                                 string="Customer Name", store=True, readonly=True)
    appear_code_id = fields.Many2one(
        'cardcode.info', related="order_id.partner_id.appear_code_id", string="Appear Code", store=True, readonly=True)
    loyalty_gift_type = fields.Selection([('point_exchange', 'Point Exchange'), ('birthday_gift', 'Birthday Gift')],
                                         compute="_compute_loyalty_gift_type", string="Loyalty Gift Type", default=False, store=True, readonly=True)
    old_price_total = fields.Float(
        string="Amount", compute="_compute_old_price_total", store=True, readonly="True")
    warehouse_id = fields.Many2one(
        'stock.warehouse', related="order_id.warehouse_id", string="Store", store=True, readonly=True)
    date_order = fields.Datetime(
        related="order_id.date_order", string="Gift Date", store=True, readonly=True)
    loyalty_point_cost = fields.Float('Point Cost', readonly=True)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    partner_expired_date = fields.Date(readonly=True)
    partner_insert_type = fields.Selection([('scan', 'Scan'), ('search','Search')])

    @api.model
    def _order_fields(self, ui_order):
        fields = super(PosOrder, self)._order_fields(ui_order)
        fields['partner_expired_date'] = ui_order.get('partner_expired_date', False)
        fields['partner_insert_type'] = ui_order.get('partner_insert_type', False)
        return fields

    def cancel_order(self):
        if not self._context.get('from_cancel_order', False):
            for order in self:
                if order.partner_id and order.loyalty_points > 0:
                    partner_id = order.partner_id
                    total_point_act = partner_id.total_point_act - order.loyalty_points
                    if(total_point_act < 0):
                        raise UserError(
                            _('Availability point is not enough for deduction, you cannot cancel this order'))
                    loyalty_id = self.env['loyalty.point.history'].sudo().search([
                        ('bill_id', '=', order.id),
                        ('order_type', '=', 'POS Order'),
                        ('method', '=', 'upgrade'),
                    ], limit=1)
                    if loyalty_id:
                        pos_id = self.sudo().search([
                            ('partner_id', '=', order.partner_id.id),
                            ('state', 'not in', ['cancel'])
                        ], order='create_date DESC', limit=1)
                        if pos_id.id != order.id:
                            context = dict(self._context.copy() or {})
                            context.update({
                                'from_cancel_order': True
                            })
                            return {
                                'type': 'ir.actions.act_window.message',
                                'title': _('Warning'),
                                'message': _("An order for a new Loyalty level has applied. if canceled this order, the Loyalty expiration date will not be updated."),
                                'close_button_title': False,
                                'buttons': [
                                    {
                                        'type': 'method',
                                        'name': _('Confirm'),
                                        'model': self._name,
                                        'method': 'cancel_order',
                                        # list of arguments to pass positionally
                                        'args': [self.ids],
                                        # dictionary of keyword arguments
                                        'kwargs': {'context': context},
                                        # button style
                                        'classes': 'btn-primary'
                                    },
                                    {
                                        'type': 'ir.actions.act_window_close',
                                        'name': _('Cancel'),
                                    }
                                ]
                            }
                        else:
                            self = self.with_context(from_loyalty_id=loyalty_id.id, not_update_partner=True)
        result = super(PosOrder, self).cancel_order()
        if self._context.get('from_loyalty_id', False):
            loyalty_id = self.env['loyalty.point.history'].sudo().browse(self._context.get('from_loyalty_id'))
            if loyalty_id and loyalty_id.current_change_date_level:
                self.mapped('partner_id').write({
                    'change_date_level': loyalty_id.current_change_date_level,
                    'expired_date': loyalty_id.current_expired_date
                })
        
        lines = self.lines.filtered(lambda l: l.cashless_code)
        for line in lines:
            code_update = self.env['cardcode.info'].sudo().search([('appear_code','=',line.cashless_code)])
            if code_update:
                code_update.with_user(SUPERUSER_ID).write({'date_created': False,
                                   'date_expired': False,
                                   'order_reference': False})
        return result

    @api.model
    def check_reward_loyalty_using(self, partner_id):
        d = datetime.now().date()
        d1 = datetime.strftime(d, "%Y-%m-%d %H:%M:%S")
        d2 = datetime.strftime(d, "%Y-%m-%d 23:59:59")
        partner = self.env['res.partner'].browse(partner_id)
        if partner.card_code_pricelist_id:
            order_use_partner_pricelist = self.env['pos.order'].search([('date_order', '>=', d1), ('date_order', '<=', d2), ('partner_id', '=', partner_id),
                                                                   ('state', 'in', ['paid', 'done', 'invoiced'])], order='id desc', limit=1)
            if len(order_use_partner_pricelist):
                order_date = self.env['res.users']._convert_user_datetime(
                    order_use_partner_pricelist.date_order.strftime(DATETIME_FORMAT))
                order_date = order_date.strftime('%H:%M:%S')
                return [order_use_partner_pricelist.warehouse_id.name, order_date, 'pricelist']
            else:
                return []
        else:
            order_line_reward = self.env['pos.order.line'].search([('date_order', '>=', d1), ('date_order', '<=', d2), ('reward_id', '!=', False),
                                                                   ('order_id.state', 'in', ['paid', 'done', 'invoiced']), ('partner_id', '=', partner_id)], limit=1)
            if len(order_line_reward):
                order_date = self.env['res.users']._convert_user_datetime(
                    order_line_reward.date_order.strftime(DATETIME_FORMAT))
                order_date = order_date.strftime('%H:%M:%S')
                return [order_line_reward.warehouse_id.name, order_date, 'reward']
            else:
                return []

    def action_pos_update_point(self):
        orders = self.filtered(lambda l: l.state != 'cancel')
        if not orders:
            return
        self._cr.execute('''
            SELECT 'POS Order' order_type, id, loyalty_points, point_won, year_discount_birth
            FROM pos_order po
            WHERE id in (%s) and partner_id is not null
                and not exists(select bill_id from loyalty_point_history where order_type = 'POS Order' and bill_id = po.id)
                and (loyalty_points !=0 or year_discount_birth != 0)
        ''' % (' ,'.join(map(str, orders.ids))))
        for order in self._cr.dictfetchall():
            order_type = order['order_type']
            if order_type == 'POS Order':
                order_obj = self.env['pos.order'].browse(order['id'])
            else:
                order_obj = self.env['sale.order'].browse(order['id'])
            partner = order_obj.partner_id

            prior_point_act = partner.total_point_act or 0.0
            exchange_point = order['loyalty_points'] or 0.0
            point_won = order['point_won'] or 0.0
            year_discount_birth = partner.year_discount_birth or 0.0
            current_point_act_before = partner.current_point_act
            current_point_act = partner.current_point_act + point_won
            partner_total_point_act = partner.total_point_act + exchange_point
            count_discount_birth = partner.count_discount_birth
            if order['year_discount_birth'] and order['year_discount_birth'] > 0:
                if order['year_discount_birth'] != partner.year_discount_birth:
                    year_discount_birth = order['year_discount_birth']
                    count_discount_birth = 1
                else:
                    count_discount_birth += 1
            if order['loyalty_points'] != 0:
                partner.write({
                    'total_point_act': partner_total_point_act,
                    'current_point_act': current_point_act,
                    'year_discount_birth': year_discount_birth,
                    'count_discount_birth': count_discount_birth,
                })
                vals = {
                    'partner_id': partner.id,
                    'mobile': partner.mobile,
                    'bill_id': order_obj.id,
                    'bill_amount': order_obj.amount_total,
                    'bill_date': order_obj.date_order,
                    'order_type': order_type,
                    'exchange_point': exchange_point,
                    'point_up': point_won,
                    'point_down': exchange_point - point_won,
                    'prior_point_act': prior_point_act,
                    'current_point_act': partner_total_point_act,
                    'prior_total_point_act': current_point_act_before,
                    'current_total_point_act': current_point_act,
                }
                self.with_user(
                    SUPERUSER_ID).env['loyalty.point.history'].create(vals)
            else:
                partner.write({
                    'year_discount_birth': year_discount_birth,
                    'count_discount_birth': count_discount_birth,
                })
