# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, SUPERUSER_ID

class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def default_get(self, fields):
        rec = super(PosConfig, self).default_get(fields)
        rec.update({
            'use_closing_balance': False,
        })
        return rec
    
    def _format_currency_amount(self, amount):
        pre = post = u''
        if self.currency_id.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=self.currency_id.symbol or '')
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=self.currency_id.symbol or '')
        return u' {pre}{0}{post}'.format(amount, pre=pre, post=post)
    
    def generate_last_order_paid_noti(self, pos_config, session_ids):
        noti = ''
        pos_order_auto_paid = self.env['pos.order'].sudo().search([('session_id', 'in', session_ids),
                                                            ('auto_paid_by_cron', '=', True)], order="config_id, id")
        if len(pos_order_auto_paid):
            list_order_string = '\n'.join(map(str, [('- ' + x.name) for x in pos_order_auto_paid]))
            total_amount = sum(pos_order_auto_paid.mapped('amount_total'))
#             currency_id = pos_order_auto_paid[0].currency_id
            total_amount = '{:,.0f}'.format(total_amount)
            total_amount_format = pos_config._format_currency_amount(total_amount)
            noti = 'Có %s bill treo được hệ thống xử lý, Tổng tiền: %s\n'%(len(pos_order_auto_paid), total_amount_format) + list_order_string
        return noti

    @api.depends('session_ids')
    def _compute_last_session(self):
        PosSession = self.env['pos.session']
        for pos_config in self:
            last_order_auto_paid_noti = ''
            session = PosSession.search_read(
                [('config_id', '=', pos_config.id), ('state', '=', 'closed')],
                ['cash_register_balance_end_real', 'stop_at', 'cash_register_id'],
                order="stop_at desc", limit=1)
            
            #Vuong: get nofi order auto paid
            session_ids = []
            pos_config_in_store = self.sudo().search([('warehouse_id', '=', pos_config.warehouse_id.id)])
            for config in pos_config_in_store:
                session_id = PosSession.sudo().search(
                [('config_id', '=', config.id), ('state', 'in', ['closing_control','closed'])],
                order="id desc", limit=1)
                if session_id:
                    session_ids.append(session_id.id)
            if len(session_ids):    
                last_order_auto_paid_noti = self.generate_last_order_paid_noti(pos_config, session_ids)
            
            pos_config.last_order_auto_paid_noti = last_order_auto_paid_noti
            if session:
                pos_config.last_session_closing_date = session[0]['stop_at'].date()
                pos_config.last_session_closing_cash = session[0]['cash_register_balance_end_real']
                pos_config.last_session_closing_cashbox = False
            else:
                pos_config.last_session_closing_cash = 0
                pos_config.last_session_closing_date = False
                pos_config.last_session_closing_cashbox = False
                
    last_order_auto_paid_noti = fields.Text(compute='_compute_last_session')
    
#     def search(self, args, offset=0, limit=None, order=None, count=False):
#         context = self._context or {}
#         if context.get('config_user',False):
#             user_with_config = self.with_user(SUPERUSER_ID).env['res.users'].search([('pos_config', '!=', False)])
#             if len(user_with_config):
#                 config_used = user_with_config.mapped('pos_config')
#                 if len(config_used):
#                     args += [('id','not in',config_used.ids)]
#         return super(PosConfig, self).search(args, offset, limit, order, count=count)
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        context = self._context or {}
        if context.get('config_user',False):
            user_with_config = self.with_user(SUPERUSER_ID).env['res.users'].search([('pos_config', '!=', False)])
            if len(user_with_config):
                config_used = user_with_config.mapped('pos_config')
                if len(config_used):
                    args += [('id','not in',config_used.ids)]
        return super(PosConfig, self).name_search(name, args, operator, limit)


    
    