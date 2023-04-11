# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, SUPERUSER_ID
from datetime import datetime
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _name = 'pos.order'
    _inherit = ["pos.order", "mail.thread", "mail.activity.mixin"]

    @api.model
    def _order_fields(self, ui_order):
        fields = super(PosOrder, self)._order_fields(ui_order)
        fields['sale_type_id'] = ui_order.get('sale_type_id', False)
        fields['note_label'] = ui_order.get('note_label', False)
        fields['operation_history_ids'] = ui_order.get(
            'operation_history_ids', False)
        fields['use_emp_coupon'] = ui_order.get('use_emp_coupon', False)
        fields['emp_coupon_code'] = ui_order.get('emp_coupon_code', False)
        fields['current_coupon_limit'] = ui_order.get(
            'current_coupon_limit', 0)
        fields['current_coupon_promotion'] = ui_order.get(
            'current_coupon_promotion', False)

        return fields

    @api.model
    def _payment_fields(self, order, ui_paymentline):
        fields = super(PosOrder, self)._payment_fields(order, ui_paymentline)
        fields['employee_id'] = ui_paymentline['employee_id']
        fields['on_account_partner_id'] = ui_paymentline['partner_id']
        fields['on_account_info'] = ui_paymentline['on_account_info']
        return fields

    def _get_invisible_cancel(self):
        user_admin = self.env.ref('base.user_admin')
        if self.env.user.id in (user_admin.id, SUPERUSER_ID):
            return False
        invisible_cancel = False
        for pos in self.filtered('date_order'):
            date_order = str(pos.date_order)
            date_order = datetime.strptime(date_order, "%Y-%m-%d %H:%M:%S")
            date_order = self.env[
                'res.users']._convert_user_datetime(date_order)
            current_date = self.env[
                'res.users']._convert_user_datetime(datetime.today())
            if date_order.date() != current_date.date():
                invisible_cancel = True
        return invisible_cancel

    @api.depends('date_order')
    def compute_invisible_cancel(self):
        for pos in self:
            invisible_cancel = pos._get_invisible_cancel()
            pos.invisible_cancel = invisible_cancel
            
    @api.depends('user_id')
    def compute_check_group_manager_pos(self):
        user = self.env.user
        for pos in self:
            check_group_manager_pos = False
            if user.has_group('phuclong_pos_base.group_store_accounting') or user.has_group('besco_pos_base.group_pos_store_manager'):
                check_group_manager_pos = True
            elif user.pos_config and user.pos_config.is_callcenter_pos:
                check_group_manager_pos = True
            pos.check_group_manager_pos = check_group_manager_pos

    sale_type_id = fields.Many2one(
        'pos.sale.type', string='Sale Type', readonly=True)
    note_label = fields.Char('Label', readonly=True)
    operation_history_ids = fields.One2many(
        'pos.operation.history', 'pos_order_id', string='Operation History')
    has_printed_label_first = fields.Boolean(
        'Has Printed Label First', default=False)
    linked_draft_order_be = fields.Char(
        string='Linked Draft Order', readonly=True)
    use_emp_coupon = fields.Boolean('Use Employee Coupon')
    emp_coupon_code = fields.Char('Employee Coupon Code')
    current_coupon_limit = fields.Integer('Current Coupon Limit')
    current_coupon_promotion = fields.Many2one(
        'sale.promo.lines', string='Current Coupon promotion')
    modify_payment_ids = fields.One2many(
        'pos.modify.payment.history', 'pos_order_id',
        string="Modify Payment",
        copy=False)
    auto_paid_by_cron = fields.Boolean(default=False, readonly=True)
    cancel_from_be = fields.Boolean(default=False, readonly=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('cancel', 'Cancelled'),
        ('paid', 'Paid'),
        ('done', 'Posted'),
        ('invoiced', 'Invoiced')],
        string='Status',
        readonly=True,
        copy=False,
        tracking=True,
        default='draft')
    invisible_cancel = fields.Boolean(
        string="Invisible Cancel",
        compute="compute_invisible_cancel")
    check_group_manager_pos = fields.Boolean(compute="compute_check_group_manager_pos")

    @api.model
    def _complete_values_from_session(self, session, values):
        values['name'] = values['pos_reference']
        values.setdefault('pricelist_id', session.config_id.pricelist_id.id)
        values.setdefault('fiscal_position_id',
                          session.config_id.default_fiscal_position_id.id)
        values.setdefault('company_id', session.config_id.company_id.id)
        return values

    def cancel_order(self):
        for order in self:
            if order.state == 'cancel':
                states = dict(
                    self._fields['state']._description_selection(self.env))
                return {
                    'type': 'ir.actions.act_window.message',
                    'title': _('Warning'),
                    'message': _("Pos Order %s is %s.") % (order.display_name, states.get(order.state, '')),
                    'close_button_title': False,
                    'buttons': [
                        {
                            'type': 'ir.actions.client',
                            'tag': 'reload',
                            'classes': 'btn-primary',
                            'name': _('Reload'),
                        }
                    ]
                }
            invisible_cancel = order._get_invisible_cancel()
            if invisible_cancel:
                raise UserError(_(
                    'You can only cancel the order '
                    'which has been ordered within today.'))
            for payment in order.payment_ids:
                today = fields.Date.today()
                date_order = order.date_order
                if today.month == date_order.month and today.year == date_order.year and payment.employee_id:
                    on_acount_amount = payment.employee_id.on_acount_amount + payment.amount
                    payment.employee_id.with_user(SUPERUSER_ID).write(
                        {'on_acount_amount': on_acount_amount})

                if payment.on_account_partner_id:
                    on_acount_amount = payment.on_account_partner_id.wallet_on_account + payment.amount
                    payment.on_account_partner_id.with_user(SUPERUSER_ID).write(
                        {'wallet_on_account': on_acount_amount})
            order.cancel_from_be = True
        res = super(PosOrder, self).cancel_order()
        for order in self:
            if order.session_id.state in ('closing_control', 'closed'):
                order.session_id.recompute_bank_amount()
        return res

    @api.model
    def create(self, vals):
        res = super(PosOrder, self).create(vals)
        return res


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    cup_id = fields.Many2one('product.product', readony=True)
    cup_type = fields.Selection(
        [('paper', 'Paper'), ('plastic', 'Plastic'),('themos', 'Themos')], string="Cup Type", readonly=True)
    option_ids = fields.One2many(
        'pos.order.line.option', 'line_id', string='Option Line', readony=True)
    is_topping_line = fields.Boolean('Is Topping Line')
    related_line_id = fields.Integer('Related Order Line')
    disable_promotion = fields.Boolean('Disable Promotion')
    disable_loyalty = fields.Boolean('Disable Loyalty')
    cashless_code = fields.Char()
    product_coupon_code = fields.Char()


class PosOrderLineOption(models.Model):
    _name = "pos.order.line.option"

    line_id = fields.Many2one(
        'pos.order.line', string='Line ID', required=True, ondelete='cascade')
    option_id = fields.Many2one(
        'product.material', string='Option', required=True)
    option_type = fields.Selection([('none', 'None'), ('below', 'Below'), (
        'normal', 'Normal'), ('over', 'Over')], string='Type', required=True)
