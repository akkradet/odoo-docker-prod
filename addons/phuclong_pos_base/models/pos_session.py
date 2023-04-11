# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PosSession(models.Model):
    _inherit = 'pos.session'

    use_opening_balance = fields.Boolean(
        related='config_id.use_opening_balance', string='Use Opening Balance', store=True)
    cash_register_balance_start = fields.Monetary(
        related=False,
        string="Starting Balance",
        help="Total of opening cash control lines.",
        readonly=False)

    def action_pos_session_open(self):
        # second browse because we need to refetch the data from the DB for cash_register_id
        # we only open sessions that haven't already been opened
        for session in self.filtered(lambda session: session.state == 'opening_control'):
            session_with_cashier_opening = self.search([('id', '!=', session.id), ('state', '!=', 'closed'), (
                'cashier_id', '!=', False), ('cashier_id', '=', session.cashier_id.id)], limit=1)
            if session_with_cashier_opening:
                raise UserError(_('Cashier has an opening session: %s, please close it before change session') % (
                    session_with_cashier_opening.name))
            return self.env.ref('phuclong_pos_base.action_wizard_input_session_balance').read()[0]
#             session.open_session()
        return True

    def action_pos_session_closing_control(self):
        for session in self:
            if session.config_id.cash_control and session.config_id.use_opening_balance:
                total = session.cash_register_balance_end
                session.write({'cash_register_balance_end_real': total})
        return super(PosSession, self).action_pos_session_closing_control()

    def recompute_bank_amount(self):
        super(PosSession, self).recompute_bank_amount()
        for session in self:
            if session.config_id.cash_control and session.config_id.use_opening_balance:
                total = session.cash_register_balance_end
                session.write({'cash_register_balance_end_real': total})

    def action_show_payments_list(self):
        return {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.payment',
            'view_mode': 'tree,pivot,graph',
            'domain': [('session_id', '=', self.id), ('state_pos', 'not in', ['new', 'cancel'])],
            'context': {'search_default_groupby_payment_method_id': 1}
        }

    def get_pos_order_draft_to_auto_paid(self):
        self._cr.execute(
            "select id from pos_order where date(timezone('UTC',date_order::timestamp)) <= current_date and state = 'draft' ")
        return self._cr.fetchall()

    @api.model
    def auto_paid_pos_order_draft(self):
        self.env['stock.quant']._merge_quants()
        result = self.get_pos_order_draft_to_auto_paid()
        if len(result):
            order_ids = [x[0] for x in result]
            order_to_paid = self.env['pos.order'].browse(order_ids)
            pos_config = order_to_paid.mapped('config_id')
            for config in pos_config:
                self._cr.execute("""select id from pos_session where date(timezone('UTC',start_at::timestamp)) <= current_date
                                    and config_id = %s and state in ('opened', 'closing_control', 'closed') order by id desc limit 1""" % (config.id))
                session = self._cr.fetchone()
                session_id = session and session[0]
                if session_id:
                    pos_session = self.env['pos.session'].browse(session_id)
                    order_by_config = order_to_paid.filtered(
                        lambda l: l.config_id.id == config.id)
                    for order in order_by_config:
                        try:
                            vals_order = {'state': 'paid',
                                          'auto_paid_by_cron': True,
                                          'date_last_order': fields.Datetime.now()}
                            if order.session_id.id != session_id:
                                vals_order.update({'session_id': session_id})
                            order.mapped('payment_ids').unlink()
                            order.write(vals_order)
                            cash_payment_method = pos_session.payment_method_ids.filtered('is_cash_count')[
                                :1]
                            if cash_payment_method:
                                payment_vals = {
                                    'pos_order_id': order.id,
                                    'amount': order.amount_total,
                                    'payment_date': order.date_order,
                                    'payment_method_id': cash_payment_method.id,
                                }
                                order.add_payment(payment_vals)
                        except Exception:
                            pass
