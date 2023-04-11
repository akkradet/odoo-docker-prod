# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from statistics import mean
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
DATE_FORMAT = "%Y-%m-%d"

class PosSession(models.Model):
    _inherit = 'pos.session'

    use_barcode_scanner_to_open_session = fields.Boolean(
        'Open Session via Card',
        related='config_id.use_barcode_scanner_to_open_session')
    
    def update_cashier(self, cashier_id):
        session_with_cashier_opening = self.search([('id','!=', self.id),('state', '!=', 'closed'),('cashier_id', '=', cashier_id)], limit=1)
        if session_with_cashier_opening:
            error = _('Cashier has an opening session: %s, please close it before change session')%(session_with_cashier_opening.name)
            return error
        self._cr.execute('''UPDATE pos_session SET cashier_id = %s where id = %s'''%(cashier_id, self.id))
        return True
    
    def check_condition_open_cashbox(self):
        return True

    @api.model
    def get_session_detail(self, session_id):
        session_id = self.env['pos.session'].browse([session_id])
        value = {}
        list_order = self.env['pos.order'].search([
            ('state', 'in', ['paid', 'done' ,'invoiced']),
            ('session_id', '=', session_id.id)])
        list_order_line = self.env['pos.order.line'].search([
            ('order_id', 'in', list_order.ids),
        ])
        # get product list:
        product_ids = []
        for line in list_order_line:
            product_ids.append({
                'product': line.product_id,
                'qty': line.qty,
                'price_unit': line.price_unit
            })
        product_to_count = list_order_line.mapped('product_id')
        categs = product_to_count.mapped('categ_id').filtered(
            lambda c: c.type == 'normal'
        )
        amount_by_categ = []
        for cat in categs:
            cat_name = cat.name[0:23] + '...' if len(cat.name) > 23 else cat.name
            cat_qty = 0
            cat_amount = 0
            for item in product_ids:
                if item.get('product').categ_id.id == cat.id:
                    cat_qty += item.get('qty')
                    cat_amount += (item.get('qty')*item.get('price_unit'))
            amount_by_categ.append({
                'name': cat_name,
                'qty': cat_qty,
                'amount': cat_amount
            })

        # get canceled order list:
        canceled_order_total = 0
        canceled_order_total += sum(self.env['pos.order'].search([
            ('state', '=', 'cancel'),
            ('session_id', '=', session_id.id)]).mapped('amount_total'))

        # get number of order and partner
        num_of_order = len(list_order)
        num_of_partner = 0
        partners = self.env['pos.order'].read_group(
            domain=[
                ('session_id', '=', session_id.id),
                ('state', 'in', ['paid', 'done' ,'invoiced'])],
            fields=['partner_id'],
            groupby=['partner_id'])
        for item in partners:
            if item.get('partner_id', False):
                num_of_partner += 1
        
        avg_total_order = list_order\
            and mean(list_order.mapped('amount_total')) or 0
        total_surchase = list_order\
            and sum(list_order.mapped('total_surcharge')) or 0
        # get total discount via promotion and loyalty program
        promo_id = self.env['pos.order'].search([
            ('state', 'in', ['paid', 'done' ,'invoiced']),
            ('session_id', '=', session_id.id)]).filtered(
            lambda x: x.promotion_id
        ).mapped('promotion_id')
        promo_id |= self.env['pos.order.line'].search([
            ('order_id', 'in', list_order.ids),
        ]).filtered(
            lambda x: x.promotion_id
        ).mapped('promotion_id')
        promo_id |= self.env['pos.order.line'].search([
            ('order_id', 'in', list_order.ids),
        ]).filtered(
            lambda x: x.promotion_condition_id
        ).mapped('promotion_condition_id')
        discount_info = []
        gift_info = []
        if promo_id:
            for item in promo_id.filtered(lambda p: p.list_type == 'PRO'):
                amount = 0
                bill = []
                # Gift
                promo_gift_order_line = self.env['pos.order.line'].search([
                        ('order_id', 'in', list_order.ids),
                    ]).filtered(
                        lambda x: x.promotion_id.id == item.id
                        and x.is_promotion_line
                        and not x.is_manual_discount
                    )
                for l in promo_gift_order_line:
                    if l.price_unit == 0:
                        amount = abs(amount) + l.old_price
                        if l.order_id.id not in bill:
                            bill.append(l.order_id.id)
                gift_info.append({
                    'promo': item.name,
                    'amount': abs(amount),
                    'num_bill': len(bill)
                })
            for item in promo_id.filtered(lambda p: p.list_type == 'DIS'):
                amount = 0
                bill = []
                # discount order
                amount += sum(self.env['pos.order'].search([
                            ('state', 'in', ['paid', 'done' ,'invoiced']),
                            ('session_id', '=', session_id.id)
                        ]).filtered(
                    lambda x: x.promotion_id.id == item.id
                    ).mapped('discount_amount'))
                bill += self.env['pos.order'].search([
                            ('state', 'in', ['paid', 'done' ,'invoiced']),
                            ('session_id', '=', session_id.id)
                        ]).filtered(
                    lambda x: x.promotion_id.id == item.id
                    ).ids
                # discount line
                promo_discount_order_line = self.env['pos.order.line'].search([
                        ('order_id', 'in', list_order.ids),
                    ]).filtered(
                        lambda x: x.promotion_id.id == item.id
                        and not x.is_manual_discount
                    )
                for l in promo_discount_order_line:
                    if l.price_unit != 0 and (l.discount != 0 or l.discount_amount != 0) and not l.is_promotion_line:
                        amount = abs(amount) + (l.discount/100 * l.price_unit * l.qty) + l.discount_amount
                        if l.order_id.id not in bill:
                            bill.append(l.order_id.id)
                if amount != 0:
                    discount_info.append({
                        'promo': item.name,
                        'amount': abs(amount),
                        'num_bill': len(bill)
                    })
                    
        #Loyalty Gift info
        #1 - Reward
        promo_loyalty_reward_ids = self.env['pos.order.line'].search([
            ('order_id', 'in', list_order.ids),('loyalty_gift_type', '=', 'point_exchange'),('reward_id', '!=', False)
        ]).mapped('reward_id')
        for item in promo_loyalty_reward_ids:
            amount = 0
            bill = []
            promo_gift_order_line_loyalty = self.env['pos.order.line'].search([
                    ('order_id', 'in', list_order.ids),('loyalty_gift_type', '=', 'point_exchange'),('reward_id', '=', item.id)
                ])
            for l in promo_gift_order_line_loyalty:
                amount = abs(amount) + l.old_price
                if l.order_id.id not in bill:
                    bill.append(l.order_id.id)
            gift_info.append({
                'promo': item.name + ' -' + str(int(item.point_cost)) + ' điểm',
                'amount': abs(amount),
                'num_bill': len(bill)
            })
        #2 - Birthday Gift
        amount = 0
        bill = []
        promo_loyalty_birthday_gift_ids = self.env['pos.order.line'].search([
            ('order_id', 'in', list_order.ids),('loyalty_gift_type', '=', 'birthday_gift')
        ])
        if len(promo_loyalty_birthday_gift_ids):
            for l in promo_loyalty_birthday_gift_ids:
                amount = abs(amount) + l.old_price
                if l.order_id.id not in bill:
                    bill.append(l.order_id.id)
            gift_info.append({
                'promo': 'Quà tặng sinh nhật',
                'amount': abs(amount),
                'num_bill': len(bill)
            })            
                    
        # Get manual discount
        manual_discount = 0
        manual_discount_bill = []
        manual_discount += abs(sum(self.env['pos.order'].search([
            ('state', 'in', ['paid', 'done' ,'invoiced']),
            ('session_id', '=', session_id.id)]).filtered(
            lambda x: not x.promotion_id
            and x.discount_amount != 0
        ).mapped('discount_amount')))
        manual_discount_bill += self.env['pos.order'].search([
            ('state', 'in', ['paid', 'done' ,'invoiced']),
            ('session_id', '=', session_id.id)]).filtered(
            lambda x: not x.promotion_id
            and x.discount_amount != 0
        ).ids
        manual_discount_order_line = self.env['pos.order.line'].search([
            ('order_id', 'in', list_order.ids),
        ]).filtered(
            lambda x: x.is_manual_discount
        )
        for l in manual_discount_order_line:
            if l.discount and not l.discount_amount:
                manual_discount += abs(l.discount/100*l.qty*l.price_unit)
            if not l.discount and l.discount_amount:
                manual_discount += abs(l.discount_amount)
            # if l.price_unit != l.old_price:
            #     l_discount = l.qty*(l.old_price - l.price_unit)
            #     manual_discount = manual_discount + abs(l_discount)
            if l.order_id.id not in manual_discount_bill:
                manual_discount_bill.append(l.order_id.id)
        if manual_discount >= 0 and manual_discount_bill:
            discount_info.append({
                'promo': 'Giảm trực tiếp',
                'amount': abs(manual_discount),
                'num_bill': len(manual_discount_bill)
            })
        # Get loyalty discount
        order_w_partner = list_order.filtered(
            lambda x: x.partner_id
        )
        loyalty_res = {}
        if order_w_partner:
            order_line_w_partner = list_order_line.filtered(
                lambda x: x.order_id.id in order_w_partner.ids
                and x.loyalty_discount_percent != 0
                and x.is_loyalty_line
            )
            for line in order_line_w_partner:
                # Search loyalty rule:
                loyalty_level_history = self.env['loyalty.point.history'].sudo().search([
                    ('pos_order_id', '=', line.order_id.id)
                ])
                loyalty_level_id = False
                if loyalty_level_history and loyalty_level_history.prior_loyalty_level:
                    loyalty_level_id = loyalty_level_history.prior_loyalty_level
                else:
                    loyalty_level_id = line.order_id.partner_id.loyalty_level_id
#                 rules = self.env['loyalty.level.rule'].sudo().search([
#                     ('discount_percent', '=', line.loyalty_discount_percent),
#                     ('loyalty_level_id', '=', loyalty_level_id)
#                 ])
#                 rules.filtered(
#                     lambda r:
#                         (
#                             r.discount_type == 'product'
#                             and line.product_id in r.product_ids
#                         ) or (
#                             r.discount_type == 'category'
#                             and line.product_id.categ_id in r.category_ids
#                         )
#                     )
                if loyalty_level_id:
                    val_str = '%s%% - %s' % (
                        int(line.loyalty_discount_percent),
                        loyalty_level_id.display_name,
                        # rules[0].discount_type == 'product'
                        # and line.display_name
                        # or line.product_id.categ_id.name
                    )
                    if loyalty_res.get(val_str):
                        loyalty_res[val_str]['amount'] += \
                            line.loyalty_discount_percent/100 \
                            * line.price_unit \
                            * line.qty
                        if(line.order_id.id not in loyalty_res[val_str]['order']):
                            loyalty_res[val_str]['order'].append(line.order_id.id)
                    else:
                        loyalty_res.update({
                            (val_str[0:23] + '...') if len(val_str) > 23 else val_str: {
                                'amount':
                                    line.loyalty_discount_percent/100
                                    * line.price_unit * line.qty,
                                'order': [line.order_id.id]
                            }
                        })
            for item in loyalty_res:
                discount_info.append({
                    'promo': item,
                    'amount': abs(loyalty_res[item]['amount']),
                    'num_bill': len(loyalty_res[item]['order'])
                })
        # Get order order by journal:
        payment = self.env['pos.payment'].search([
            ('session_id', '=', session_id.id),
            ('amount', '>=', 0),
            ('state_pos', '=', 'paid')
        ])
        payment_method = payment.mapped('payment_method_id')
        order_by_journal = []
        for p in payment_method:
            payments = self.env['pos.payment'].search([
                ('session_id', '=', session_id.id),
                ('amount', '>=', 0),
                ('payment_method_id', '=', p.id),
                ('state_pos', '=', 'paid')
            ])
            order = []
            payment_amount = 0
            for payment in payments:
#                 if payment.pos_order_id.id not in order:
#                     order.append(payment.pos_order_id.id)
                payment_amount += payment.amount
            order_by_journal.append({
                'name': p.name,
                'count': len(payments),
                'amount': payment_amount
            })

        # Order group by cashier
        order_by_cashier = []
        for employee in list_order.mapped('cashier_id'):
            order_by_employee = list_order.filtered(
                lambda x: x.cashier_id.id == employee.id)
            payment_ids = order_by_employee.mapped('payment_ids')
            payment_by_employee = []
            for payment_method in payment_ids.mapped('payment_method_id'):
                payment_by_method = payment_ids.filtered(
                    lambda x: x.payment_method_id.id == payment_method.id)
                payment_by_employee.append({'method':payment_method.name,
                                            'count':len(payment_by_method),
                                            'amount': sum(payment_by_method.mapped('amount'))})
            order_by_cashier.append({
                'employee': employee.name,
                'bills': len(payment_ids),
                'amount': sum(order_by_employee.mapped('amount_total')),
                'payment_by_employee': payment_by_employee,
            })
            
         #Vuong: combo by qty
        combo_list = []
        if len(list_order_line):
            self._cr.execute('''select spc.name combo_name, sum(qty)/spc.sum_of_qty combo_qty from pos_order_line pol left join sale_promo_combo spc
                on pol.combo_id = spc.id where pol.combo_id is not null and pol.id in (%s)
                group by spc.name, spc.sum_of_qty
            '''%(' ,'.join(map(str, [x.id for x in list_order_line]))))
            
            combo_list = self._cr.dictfetchall()
                
        return {
            'bill_products_by_cate': amount_by_categ,
            'canceled_order_total': canceled_order_total,
            'num_of_order': num_of_order,
            'num_of_partner': num_of_partner,
            'avg_total_order': avg_total_order,
            'total_surchase': total_surchase,
            'discount_info': discount_info,
            'gift_info': gift_info,
            'order_by_journal': order_by_journal,
            'order_by_cashier': order_by_cashier,
            'combo_list': combo_list
        }

    def open_frontend_cb(self):
        if not self.ids:
            return {}
        for session in self:
            start_at = self.env['res.users']._convert_user_datetime(session.create_date)
            now = self.env['res.users']._convert_user_datetime(fields.Datetime.now())
            if start_at.date() != now.date():
                raise UserError('Bạn không thể tiếp tục bán hàng do ca bán hàng chỉ có hiệu lực trong ngày, hãy đóng ca bán hàng đang dang dở')
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url':   '/pos/web?config_id=%d' % self.config_id.id,
        }

    def action_pos_session_cashier_scanner(self):
        ctx = dict(
            default_session_id=self.id
        )
        return{
            'name': _('Cảnh báo'),
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'wizard.pos.cashier.scanner',
            'view_id': self.env.ref(
                'phuclong_pos_theme.wizard_pos_cashier_scanner').id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
        }

    def _check_if_no_draft_orders(self):
        # draft_orders = self.order_ids.filtered(lambda order: order.state == 'draft')
        # if draft_orders:
        #     raise UserError(_(
        #             'There are still orders in draft state in the session. '
        #             'Pay or cancel the following orders to validate the session:\n%s'
        #         ) % ', '.join(draft_orders.mapped('name'))
        #     )

        # Thái: Cho phép kết ca có đơn hàng Nháp
        return True

    @api.model
    def _get_from_date(self, date):
        date_format = "%Y-%m-%d 17:00:00"
        date = datetime.strptime(date, DATE_FORMAT)
        date = date - timedelta(days=1)
        from_date = date.strftime(date_format) 
        return from_date

    @api.model
    def get_date_revenue_by_warehouse(self, warehouse_id, date):
        config_ids = self.env['pos.config'].sudo().search([
            ('warehouse_id', '=', warehouse_id)
        ])
        sessions = self.env['pos.session'].sudo().search([
            ('config_id', 'in', config_ids.ids),
            ('start_at', '>=', self._get_from_date(date)),
            ('start_at', '<=', (date + ' 16:59:59')),
        ])
        value = {}
        list_order = self.env['pos.order'].search([
            ('state', 'in', ['paid', 'done' ,'invoiced']),
            ('session_id', 'in', sessions.ids)])
        list_order_draft = self.env['pos.order'].search([
            ('state', '=', 'draft'),
            ('session_id', 'in', sessions.ids)])
        list_order_line = self.env['pos.order.line'].search([
            ('order_id', 'in', list_order.ids),
        ])
        # Doanh thu theo ca:
        session_seq = 1
        session_amount = []
        for s in sessions.sorted(key=lambda s: s.id):
            orders_seq = list_order.filtered(
                lambda c: c.session_id.id == s.id
            )
            session_amount.append({
                'tag': 'session',
                'seq': session_seq,
                'amount': sum(orders_seq.mapped('amount_total')),
                'state': s.state
            })
            session_seq += 1
        session_amount.append({
            'tag': 'total',
            'seq': 0,
            'amount': sum(list_order.mapped('amount_total')),
            'state': False
        })
        # find order before 15:00
        session_amount.append({
            'tag': 'morning',
            'seq': 0,
            'amount': sum(
                self.env['pos.order'].search([
                    ('state', 'in', ['paid', 'done' ,'invoiced']),
                    ('session_id', 'in', sessions.ids),
                    ('date_order', '<=', (date + ' 08:00:00'))
                ]).mapped('amount_total')),
            'state': False
        })
        session_amount.append({
            'tag': 'after',
            'seq': 0,
            'amount': sum(
                self.env['pos.order'].search([
                    ('state', 'in', ['paid', 'done' ,'invoiced']),
                    ('session_id', 'in', sessions.ids),
                    ('date_order', '>', (date + ' 08:00:00'))
                ]).mapped('amount_total')),
            'state': False
        })
        # get product list:
        product_ids = []
        for line in list_order_line:
            product_ids.append({
                'product': line.product_id,
                'qty': line.qty,
                'price_unit': line.price_unit
            })
        product_to_count = list_order_line.mapped('product_id')
        categs = product_to_count.mapped('categ_id').filtered(
            lambda c: c.type == 'normal'
        )
        amount_by_categ = []
        for cat in categs:
            cat_name = cat.name[0:23] + '...' if len(cat.name) > 23 else cat.name
            cat_qty = 0
            cat_amount = 0
            for item in product_ids:
                if item.get('product').categ_id.id == cat.id:
                    cat_qty += item.get('qty')
                    cat_amount += (item.get('qty')*item.get('price_unit'))
            amount_by_categ.append({
                'name': cat_name,
                'qty': cat_qty,
                'amount': cat_amount
            })
        # get canceled order list:
        cancel_order = self.env['pos.order'].search([
            ('state', '=', 'cancel'),
            ('session_id', 'in', sessions.ids)])
        canceled_order_total = 0
        canceled_order_total += sum(cancel_order.mapped('amount_total'))
        canceled_order_len = len(cancel_order)
        # get number of order and partner
        num_of_order = len(list_order)
        num_of_partner = 0
        partners = self.env['pos.order'].read_group(
            domain=[
                ('session_id', 'in', sessions.ids),
                ('state', 'in', ['paid', 'done' ,'invoiced'])],
            fields=['partner_id'],
            groupby=['partner_id'])
        for item in partners:
            if item.get('partner_id', False):
                num_of_partner += 1
        avg_total_order = list_order\
            and mean(list_order.mapped('amount_total')) or 0
        total_surchase = list_order\
            and sum(list_order.mapped('total_surcharge')) or 0
        # get total discount via promotion and loyalty program
        promo_id = self.env['pos.order'].search([
            ('state', 'in', ['paid', 'done' ,'invoiced']),
            ('session_id', 'in', sessions.ids)]).filtered(
            lambda x: x.promotion_id
        ).mapped('promotion_id')
        promo_id |= self.env['pos.order.line'].search([
            ('order_id', 'in', list_order.ids),
        ]).filtered(
            lambda x: x.promotion_id
        ).mapped('promotion_id')
        promo_id |= self.env['pos.order.line'].search([
            ('order_id', 'in', list_order.ids),
        ]).filtered(
            lambda x: x.promotion_condition_id
        ).mapped('promotion_condition_id')
        discount_info = []
        gift_info = []
        if promo_id:
            for item in promo_id.filtered(lambda p: p.list_type == 'PRO'):
                amount = 0
                bill = []
                # Gift
                promo_gift_order_line = self.env['pos.order.line'].search([
                        ('order_id', 'in', list_order.ids),
                    ]).filtered(
                        lambda x: x.promotion_id.id == item.id
                        and x.is_promotion_line
                        and not x.is_manual_discount
                    )
                for l in promo_gift_order_line:
                    if l.price_unit == 0:
                        amount = abs(amount) + l.old_price
                        if l.order_id.id not in bill:
                            bill.append(l.order_id.id)
                gift_info.append({
                    'promo': item.name,
                    'amount': abs(amount),
                    'num_bill': len(bill)
                })
            for item in promo_id.filtered(lambda p: p.list_type == 'DIS'):
                amount = 0
                bill = []
                # discount order
                amount += sum(self.env['pos.order'].search([
                            ('state', 'in', ['paid', 'done' ,'invoiced']),
                            ('session_id', 'in', sessions.ids)
                        ]).filtered(
                    lambda x: x.promotion_id.id == item.id
                    ).mapped('discount_amount'))
                bill += self.env['pos.order'].search([
                            ('state', 'in', ['paid', 'done' ,'invoiced']),
                            ('session_id', 'in', sessions.ids)
                        ]).filtered(
                    lambda x: x.promotion_id.id == item.id
                    ).ids
                # discount line
                promo_discount_order_line = self.env['pos.order.line'].search([
                        ('order_id', 'in', list_order.ids),
                    ]).filtered(
                        lambda x: x.promotion_id.id == item.id
                        and not x.is_manual_discount
                    )
                for l in promo_discount_order_line:
                    if l.price_unit != 0 and (l.discount != 0 or l.discount_amount != 0) and not l.is_promotion_line:
                        amount = abs(amount) + (l.discount/100 * l.price_unit * l.qty) + l.discount_amount
                        if l.order_id.id not in bill:
                            bill.append(l.order_id.id)
                # Gift
                promo_gift_order_line = self.env['pos.order.line'].search([
                        ('order_id', 'in', list_order.ids),
                    ]).filtered(
                        lambda x: x.promotion_id.id == item.id
                        and x.is_promotion_line
                        and not x.is_manual_discount
                    )
                for l in promo_gift_order_line:
                    if l.price_unit == 0:
                        amount = abs(amount) + l.old_price
                        if l.order_id.id not in bill:
                            bill.append(l.order_id.id)
                if amount != 0:
                    discount_info.append({
                        'promo': item.name,
                        'amount': abs(amount),
                        'num_bill': len(bill)
                    })
                    
        #Loyalty Gift info
        #1 - Reward
        promo_loyalty_reward_ids = self.env['pos.order.line'].search([
            ('order_id', 'in', list_order.ids),('loyalty_gift_type', '=', 'point_exchange'),('reward_id', '!=', False)
        ]).mapped('reward_id')
        for item in promo_loyalty_reward_ids:
            amount = 0
            bill = []
            promo_gift_order_line_loyalty = self.env['pos.order.line'].search([
                    ('order_id', 'in', list_order.ids),('loyalty_gift_type', '=', 'point_exchange'),('reward_id', '=', item.id)
                ])
            for l in promo_gift_order_line_loyalty:
                amount = abs(amount) + l.old_price
                if l.order_id.id not in bill:
                    bill.append(l.order_id.id)
            gift_info.append({
                'promo': item.name + ' -' + str(int(item.point_cost)) + ' điểm',
                'amount': abs(amount),
                'num_bill': len(bill)
            })
        #2 - Birthday Gift
        amount = 0
        bill = []
        promo_loyalty_birthday_gift_ids = self.env['pos.order.line'].search([
            ('order_id', 'in', list_order.ids),('loyalty_gift_type', '=', 'birthday_gift')
        ])
        if len(promo_loyalty_birthday_gift_ids):
            for l in promo_loyalty_birthday_gift_ids:
                amount = abs(amount) + l.old_price
                if l.order_id.id not in bill:
                    bill.append(l.order_id.id)
            gift_info.append({
                'promo': 'Quà tặng sinh nhật',
                'amount': abs(amount),
                'num_bill': len(bill)
            })
                    
        # Get manual discount
        manual_discount = 0
        manual_discount_bill = []
        manual_discount += abs(sum(self.env['pos.order'].search([
            ('state', 'in', ['paid', 'done' ,'invoiced']),
            ('session_id', 'in', sessions.ids)]).filtered(
            lambda x: not x.promotion_id
            and x.discount_amount != 0
        ).mapped('discount_amount')))
        manual_discount_bill += self.env['pos.order'].search([
            ('state', 'in', ['paid', 'done' ,'invoiced']),
            ('session_id', 'in', sessions.ids)]).filtered(
            lambda x: not x.promotion_id
            and x.discount_amount != 0
        ).ids
        manual_discount_order_line = self.env['pos.order.line'].search([
            ('order_id', 'in', list_order.ids),
        ]).filtered(
            lambda x: x.is_manual_discount
        )
        for l in manual_discount_order_line:
            if l.discount and not l.discount_amount:
                manual_discount += abs(l.discount/100*l.qty*l.price_unit)
            if not l.discount and l.discount_amount:
                manual_discount += abs(l.discount_amount)
            # if l.price_unit != l.old_price:
            #     l_discount = l.qty*(l.old_price - l.price_unit)
            #     manual_discount = manual_discount + abs(l_discount)
            if l.order_id.id not in manual_discount_bill:
                manual_discount_bill.append(l.order_id.id)
        if manual_discount >= 0 and manual_discount_bill:
            discount_info.append({
                'promo': 'Giảm trực tiếp',
                'amount': abs(manual_discount),
                'num_bill': len(manual_discount_bill)
            })
        # Get loyalty discount
        order_w_partner = list_order.filtered(
            lambda x: x.partner_id
        )
        loyalty_res = {}
        if order_w_partner:
            order_line_w_partner = list_order_line.filtered(
                lambda x: x.order_id.id in order_w_partner.ids
                and x.loyalty_discount_percent != 0
                and x.is_loyalty_line
            )
            for line in order_line_w_partner:
                # Search loyalty rule:
                loyalty_level_history = self.env['loyalty.point.history'].sudo().search([
                    ('pos_order_id', '=', line.order_id.id)
                ])
                if loyalty_level_history and loyalty_level_history.prior_loyalty_level:
                    loyalty_level_id = loyalty_level_history.prior_loyalty_level
                else:
                    loyalty_level_id = line.order_id.partner_id.loyalty_level_id and line.order_id.partner_id.loyalty_level_id
                    
                if loyalty_level_id:
                    val_str = '%s%% - %s' % (
                        int(line.loyalty_discount_percent),
                        loyalty_level_id.display_name,
                    )
                    val_str = (val_str[0:23] + '...') if len(val_str) > 23 else val_str
                    if loyalty_res.get(val_str):
                        loyalty_res[val_str]['amount'] += \
                            line.loyalty_discount_percent/100 \
                            * line.price_unit \
                            * line.qty
                        if(line.order_id.id not in loyalty_res[val_str]['order']):
                            loyalty_res[val_str]['order'].append(line.order_id.id)
                    else:
                        loyalty_res.update({
                            (val_str[0:23] + '...') if len(val_str) > 23 else val_str: {
                                'amount':
                                    line.loyalty_discount_percent/100
                                    * line.price_unit * line.qty,
                                'order': [line.order_id.id]
                            }
                        })
#                 rules = self.env['loyalty.level.rule'].sudo().search([
#                     ('discount_percent', '=', line.loyalty_discount_percent),
#                     ('loyalty_level_id', '=', loyalty_level_id)
#                 ], limit=1)
#                 if rules:
#                     val_str = '%s%%-%s-%s' % (
#                         rules[0].discount_percent,
#                         rules[0].loyalty_level_id.display_name,
#                         rules[0].discount_type == 'product'
#                         and line.display_name
#                         or line.product_id.categ_id.name
#                     )
#                     val_str = (val_str[0:23] + '...') if len(val_str) > 23 else val_str
#                     if loyalty_res.get(val_str):
#                         loyalty_res[val_str]['amount'] += \
#                             line.loyalty_discount_percent/100 \
#                             * line.price_unit \
#                             * line.qty
#                         loyalty_res[val_str]['order'].append(line.order_id.id)
#                     else:
#                         loyalty_res.update({
#                             (val_str[0:23] + '...') if len(val_str) > 23 else val_str: {
#                                 'amount':
#                                     line.loyalty_discount_percent/100
#                                     * line.price_unit * line.qty,
#                                 'order': [line.order_id.id]
#                             }
#                         })
            for item in loyalty_res:
                discount_info.append({
                    'promo': item,
                    'amount': abs(loyalty_res[item]['amount']),
                    'num_bill': len(loyalty_res[item]['order'])
                })
        # Get order order by journal:
        payment = self.env['pos.payment'].search([
            ('session_id', 'in', sessions.ids),
            ('amount', '>=', 0),
            ('state_pos', '=', 'paid')
        ])
        payment_method = payment.mapped('payment_method_id')
        order_by_journal = []
        for p in payment_method:
            payments = self.env['pos.payment'].search([
                ('session_id', 'in', sessions.ids),
                ('amount', '>=', 0),
                ('payment_method_id', '=', p.id),
                ('state_pos', '=', 'paid')
            ])
            order = []
            payment_amount = 0
            for payment in payments:
#                 if payment.pos_order_id.id not in order:
#                     order.append(payment.pos_order_id.id)
                payment_amount += payment.amount
            order_by_journal.append({
                'name': p.name,
                'count': len(payments),
                'amount': payment_amount
            })

        pickings = list_order.mapped('picking_id').filtered(
            lambda p: p.state == 'done'
        )
        # Lấy thông tin Ly sử dụng:
        cup_move_line = self.env['stock.move'].sudo().search([
            ('picking_id', 'in', pickings.ids)
        ])
        # Ly giấy và ly nhựa sử dụng:
#         plastic_cup = sum(cup_move_line.filtered(
#             lambda p: p.product_id.product_tmpl_id.cup_type == 'plastic'
#         ).mapped('quantity_done'))
#         paper_cup = sum(cup_move_line.filtered(
#             lambda p: p.product_id.product_tmpl_id.cup_type == 'paper'
#         ).mapped('quantity_done'))
        cup_vals = []
        cup_products = cup_move_line.mapped('product_id').filtered(
            lambda p: p.product_tmpl_id.cup_type in ['plastic', 'paper']
        ).sorted(key=lambda l:l.product_tmpl_id.cup_type)
        for l in cup_products:
            cup_sum = sum(cup_move_line.filtered(
                lambda p: p.product_id.id == l.id
            ).mapped('quantity_done'))
            cup_vals.append({
                'name': l.product_tmpl_id.name,
                'sum': cup_sum or 0
            })
            
        # Lấy thông tin Nắp sử dụng:
        lid_products = cup_move_line.mapped('product_id').filtered(
            lambda p: p.product_tmpl_id.categ_id.fnb_type == 'lid'
        )
        lid_vals = []
        for l in lid_products:
            lid_sum = sum(cup_move_line.filtered(
                lambda p: p.product_id.id == l.id
            ).mapped('quantity_done'))
            lid_vals.append({
                'name': l.product_tmpl_id.name,
                'sum': lid_sum or 0
            })
        # Lấy thông tin Ly KH Không lấy:
        order_line_no_cup = list_order_line.filtered(
            lambda l: not l.cup_type and
            l.product_id.product_tmpl_id.fnb_type == 'drink'
        )
        no_cup_vals = {}
        list_no_cup = []
        for l in order_line_no_cup:
            product_tmpl = l.product_id.product_tmpl_id
            cup_sale_type = product_tmpl.cup_ids.filtered(
                lambda c: c.sale_type_id.id == l.order_id.sale_type_id.id
            )
            cup_line_ids = cup_sale_type and\
                cup_sale_type.cup_line_ids
            cup = cup_line_ids and cup_line_ids.sorted('sequence')[0]
            if cup:
                if cup.cup_id in no_cup_vals:
                    no_cup_vals[cup.cup_id]['num'] += l.qty
                else:
                    no_cup_vals.update({
                        cup.cup_id: {
                            'name': cup.cup_id.name,
                            'num': l.qty
                        }
                    })
        for item in no_cup_vals.values():
            list_no_cup.append(item)
#         cup_vals = {}
#         cup_paper = 0
#         cup_plastic = 0
#         for item in list_no_cup:
#             # Tổng số lượng ly giấy:
#             if item['cup'].cup_id.cup_type == 'paper':
#                 cup_paper += item['num']
#             # Tổng số lượng ly nhựa:
#             if item['cup'].cup_id.cup_type == 'plastic':
#                 cup_plastic += item['num']
        # Đổi ly
        order_lines_have_cup = list_order_line.filtered(
            lambda l: l.cup_type and
            l.product_id.product_tmpl_id.fnb_type == 'drink'
        )
        has_cup_vals = {}
        list_has_cup = []
        change_cup_paper = 0
        change_cup_plastic = 0
        for l in order_lines_have_cup:
            product_tmpl = l.product_id.product_tmpl_id
            cup_sale_type = product_tmpl.cup_ids.filtered(
                lambda c: c.sale_type_id.id == l.order_id.sale_type_id.id
            )
            cup = cup_sale_type and\
                cup_sale_type.cup_line_ids.sorted('sequence')[0]
            if cup.cup_type == 'paper' and l.cup_type != cup.cup_type:
                change_cup_paper += l.qty
            if cup.cup_type == 'plastic' and l.cup_type != cup.cup_type:
                change_cup_plastic += l.qty
                
        #Vuong: combo by qty
        combo_list = []
        if len(list_order_line):
            self._cr.execute('''select spc.name combo_name, sum(qty)/spc.sum_of_qty combo_qty from pos_order_line pol left join sale_promo_combo spc
                on pol.combo_id = spc.id where pol.combo_id is not null and pol.id in (%s)
                group by spc.name, spc.sum_of_qty
            '''%(' ,'.join(map(str, [x.id for x in list_order_line]))))
            
            combo_list = self._cr.dictfetchall()
        
        draft_bill = {}
        if len(list_order_draft):
            draft_bill.update({'count': len(list_order_draft),
                               'amount': sum(list_order_draft.mapped('amount_total'))})
        
        auto_paid_bill = {}
        auto_paid_order = list_order.filtered(lambda l: l.auto_paid_by_cron)
        if len(auto_paid_order):
            auto_paid_bill.update({'count': len(auto_paid_order),
                               'amount': sum(auto_paid_order.mapped('amount_total'))})
            
        values = {
            'warehouse_name': config_ids and config_ids[0].warehouse_id.name,
            'bill_products_by_cate': amount_by_categ,
            'canceled_order_total': canceled_order_total,
            'canceled_order_len': canceled_order_len,
            'num_of_order': num_of_order,
            'num_of_partner': num_of_partner,
            'avg_total_order': avg_total_order,
            'total_surchase': total_surchase,
            'discount_info': discount_info,
            'gift_info': gift_info,
            'order_by_journal': order_by_journal,
            'date_start_string': date,
            'session_amount': session_amount,
#             'plastic_cup': plastic_cup,
#             'paper_cup': paper_cup,
            'cups': cup_vals,
            'lids': lid_vals,
            'list_no_cup': list_no_cup,
            'change_cup_plastic': change_cup_plastic,
            'change_cup_paper': change_cup_paper,
            'combo_list':combo_list,
            'user_name': self.env.user.name,
            'draft_bill': draft_bill,
            'auto_paid_bill': auto_paid_bill,
        }
        return values


class pos_config(models.Model):
    _inherit = 'pos.config'

    def open_ui(self):
        self.ensure_one()
        pos_sessions_open = self.env['pos.session'].search([
            ('state', '=', 'opened'),
            ('user_id', '=', self._uid)
        ])
        for pos_sessions in pos_sessions_open:
            if pos_sessions and pos_sessions.create_date:
                start_at = self.env['res.users']._convert_user_datetime(pos_sessions.create_date)
                now = self.env['res.users']._convert_user_datetime(fields.Datetime.now())
                if start_at.date() != now.date():
                    raise UserError('Bạn không thể tiếp tục bán hàng do ca bán hàng chỉ có hiệu lực trong ngày, hãy đóng ca bán hàng đang dang dở')
            return super(pos_config, self).open_ui()
