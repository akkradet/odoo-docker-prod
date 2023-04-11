# -*- coding: utf-8 -*-
from collections import namedtuple, OrderedDict, defaultdict
from odoo import api, fields, models, _, registry
from odoo.tools.misc import split_every
from odoo.osv import expression
from datetime import date, timedelta, datetime
# import datetime
from psycopg2 import OperationalError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare, float_round
from collections import OrderedDict
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)
#week_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    def _get_orderpoint_domain(self, company_id=False):
        # bo xung do main theo project Phuc Long
        context = self._context and self._context.copy() or {}
        res = super(ProcurementGroup, self)._get_orderpoint_domain(company_id=company_id)
        if context.get('buy_phuclong', False):
            if context.get('is_manually', False) and context.get('active_ids', False):
                res += [('id', 'in', context.get('active_ids', False))]
            else:
                current_date = self.env[
                    'res.users']._convert_user_datetime(fields.Datetime.now())
                # lst_current_date = [current_date.day, current_date.month, current_date.year]
                day_of_the_week = current_date.weekday()
                res += ['|', '&', ('week_month_toggle', '=', 'weekday'), ('weekday_ids.sequence', '=', day_of_the_week),
                        '&', ('week_month_toggle', '=', 'day_of_month'), ('day_of_month_ids', '=', current_date.day)]
        return res

    @api.model
    def _run_scheduler_tasks(self, use_new_cursor=False, company_id=False):
        # Minimum stock rules
        self.sudo()._procure_orderpoint_confirm(use_new_cursor=use_new_cursor, company_id=company_id)

        # Search all confirmed stock_moves and try to assign them
        domain = self._get_moves_to_assign_domain()
        moves_to_assign = self.env['stock.move'].search(domain, limit=None, order='priority desc, date_expected asc')
        for moves_chunk in split_every(100, moves_to_assign.ids):
            self.env['stock.move'].browse(moves_chunk)._action_assign()
            if use_new_cursor:
                self._cr.commit()

        if use_new_cursor:
            self._cr.commit()

        # Merge duplicated quants
        self.env['stock.quant']._quant_tasks()
        if use_new_cursor:
            self._cr.commit()

    @api.model
    def run_scheduler(self, use_new_cursor=False, company_id=False):
        try:
            if use_new_cursor:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))  # TDE FIXME
            self._run_scheduler_tasks(use_new_cursor=use_new_cursor, company_id=company_id)
        finally:
            if use_new_cursor:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return {}

    @api.model
    def run_procurement_act(self, use_new_cursor=False, company_id=False):
        try:
            if use_new_cursor:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))
            context = self._context and self._context.copy() or {}
            buy_route_id = self.env[
                'ir.model.data'].get_object_reference(
                    'purchase_stock', 'route_warehouse0_buy')[1]
            current_today = self.env[
                'res.users']._convert_user_datetime(fields.Datetime.now())
            context.update({
                'buy_phuclong': True,
                'route_ids': buy_route_id,
                'current_today': current_today})
            self.with_context(context).run_scheduler(
                use_new_cursor=use_new_cursor,
                company_id=company_id)
        finally:
            if use_new_cursor:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return {}

    @api.model
    def _procurement_from_orderpoint_get_groups(self, orderpoint_ids):
        # bo xung do main theo project Phuc Long
        context = self._context and self._context.copy() or {}
        res = super(ProcurementGroup, self)._procurement_from_orderpoint_get_groups(orderpoint_ids=orderpoint_ids)
        if context.get('buy_phuclong', False) and context.get('current_today', False):
            from_date = self._context.get('current_today', False)
            orderpoint_id = self.env['stock.warehouse.orderpoint'].browse(orderpoint_ids)
            to_date = from_date + timedelta(days=2*orderpoint_id.safety_cycle_days+2)
            res[0].update({'from_date': from_date,
                           'to_date': to_date})
        return res

    @api.model
    def _procure_orderpoint_confirm(self, use_new_cursor=False, company_id=False):
        """
        kế thừa lại hàm hốc _procure_orderpoint_confirm và điều chỉnh cho project Phúc Long
        """
        ctx = self._context.copy()
        if not ctx.get('buy_phuclong', False):
            return super(ProcurementGroup, self)._procure_orderpoint_confirm(use_new_cursor=use_new_cursor,
                                                                             company_id=company_id)
        if company_id and self.env.company.id != company_id:
            # To ensure that the company_id is taken into account for
            # all the processes triggered by this method
            # i.e. If a PO is generated by the run of the procurements the
            # sequence to use is the one for the specified company not the
            # one of the user's company
            self = self.with_context(company_id=company_id, force_company=company_id)
        OrderPoint = self.env['stock.warehouse.orderpoint']
        domain = self._get_orderpoint_domain(company_id=company_id)
        orderpoints_noprefetch = OrderPoint.with_context(prefetch_fields=False).search(domain,
            order=self._procurement_from_orderpoint_get_order()).ids
        while orderpoints_noprefetch:
            if use_new_cursor:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))
            OrderPoint = self.env['stock.warehouse.orderpoint']

            orderpoints = OrderPoint.browse(orderpoints_noprefetch[:1000])
            orderpoints_noprefetch = orderpoints_noprefetch[1000:]


            # Calculate groups that can be executed together
            location_data = OrderedDict()

            def makedefault():
                return {
                    'products': self.env['product.product'],
                    'orderpoints': self.env['stock.warehouse.orderpoint'],
                    'groups': []
                }

            for orderpoint in orderpoints:
                key = self._procurement_from_orderpoint_get_grouping_key([orderpoint.id])
                if not location_data.get(key):
                    location_data[key] = makedefault()
                location_data[key]['products'] += orderpoint.product_id
                location_data[key]['orderpoints'] += orderpoint
                location_data[key]['groups'] = self._procurement_from_orderpoint_get_groups([orderpoint.id])

            for location_id, location_data in location_data.items():
                location_orderpoints = location_data['orderpoints']
                product_context = dict(self._context,
                                       #location=location_orderpoints[0].location_id.id,
                                       warehouse=location_orderpoints[0].warehouse_id.id
                                       )
                product_average_context = dict(self._context,
                                               #location=location_orderpoints[0].location_id.id,
                                               warehouse=location_orderpoints[0].warehouse_id.id
                                               )
                product_weekly_context = dict(self._context,
                                              #location=location_orderpoints[0].location_id.id,
                                              warehouse=location_orderpoints[0].warehouse_id.id
                                              )
                date_format = "%Y-%m-%d 00:00:00"
                date_to = "%Y-%m-%d 23:59:59"
                if self._context.get('current_today', False):
                    current_today = self._context.get('current_today', False)
                    from_date = current_today - timedelta(days=7)
                    from_date = from_date.strftime(date_format)
                    from_date = self.env[
                        'res.users']._convert_date_datetime_to_utc(
                            from_date, datetime_format=True)
                    to_date = current_today - timedelta(days=1)
                    to_date = to_date.strftime(date_to)
                    to_date = self.env[
                        'res.users']._convert_date_datetime_to_utc(
                            to_date, datetime_format=True)
                    product_weekly_context.update({
                        'picking_type_id': self.env.ref('besco_pos_base.picking_type_posout').id or False,
                        'to_date': to_date,
                        'from_date': from_date,
                        })
                substract_quantity = location_orderpoints._quantity_in_progress()

                for group in location_data['groups']:
                    if group.get('from_date'):
#                         product_context['from_date'] = group['from_date'].strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        group_from_date = group['from_date'].strftime(date_format)
                        group_from_date = self.env[
                            'res.users']._convert_date_datetime_to_utc(
                                group_from_date, datetime_format=True)
                        product_context['from_date'] = group_from_date
                    if group['to_date']:
#                         product_context['to_date'] = group['to_date'].strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        group_to_date = group['to_date'].strftime(date_to)
                        group_to_date = self.env[
                            'res.users']._convert_date_datetime_to_utc(
                                group_to_date, datetime_format=True)
                        product_context['to_date'] = group_to_date
                    date_update = current_today.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    date_update = self.env[
                        'res.users']._convert_date_datetime_to_utc(
                            date_update, datetime_format=True)
                    product_quantity = location_data['products'].with_context(product_context)._product_available()
#                     print ('product_quantity ', product_quantity)
                    product_quantity_weekly = location_data['products'].with_context(product_weekly_context)._product_available()
#                     print ('product_quantity_weekly ', product_quantity_weekly)
                    for orderpoint in location_orderpoints:
                        try:
                            # chu kỳ
                            current_today = self._context.get('current_today', False)
                            cycle = orderpoint.safety_cycle_days
                            avg_to_date = current_today + timedelta(
                                days=(2*cycle)+2)
                            avg_to_date = avg_to_date.strftime(date_to)
                            avg_to_date = self.env[
                                'res.users']._convert_date_datetime_to_utc(
                                    avg_to_date, datetime_format=True)
                            product_average_context.update({
                                'product_average': True,
                                'to_date': avg_to_date,
                                })
                            product_quantity_average = location_data[
                                'products'].with_context(
                                    product_average_context)._product_available()
                            # Tồn kho thực tế
                            qty_available = product_quantity[orderpoint.product_id.id]['qty_available']
                            #print ('qty_available ', qty_available)
                            # Số lượng bán dự kiến
                            outgoing_qty = product_quantity_average[orderpoint.product_id.id]['outgoing_qty']
                            #print ('outgoing_qty ', outgoing_qty)
                            # Số lượng mua dự kiến
                            incoming_qty = product_quantity_average[orderpoint.product_id.id]['incoming_qty']
                            #print ('incoming_qty ', incoming_qty)
                            # Tồn kho dự kiến thực tế (stock move = done)
                            op_product_virtual = product_quantity[orderpoint.product_id.id]['virtual_available']
                            #print ('op_product_virtual ', op_product_virtual)
                            # Tồn kho dự kiến ((stock move khác [done, cancel]))
                            virtual_available = qty_available - outgoing_qty + incoming_qty
                            #print ('virtual_available ', virtual_available)
                            
                            if op_product_virtual is None:
                                continue
                            # điều kiện tồn kho dự kiến < SL tối thiểu mới chạy cung ung
#                             if float_compare(op_product_virtual, orderpoint.product_min_qty,
#                                              precision_rounding=orderpoint.product_uom.rounding) <= 0:
                            #qty_average = (product_quantity_average[orderpoint.product_id.id]['outgoing_qty'])/7
                            qty_average_weekly = (product_quantity_weekly[orderpoint.product_id.id]['outgoing_qty'])/7
                            qty_new = float_round((2*qty_average_weekly*(cycle+1) - virtual_available),
                                                  precision_rounding=orderpoint.product_uom.rounding)
                            # if float_compare(qty_new, 0.0, precision_rounding=orderpoint.product_uom.rounding) < 0:
                            #     continue

                            qty_new -= substract_quantity[orderpoint.id]
                            qty_rounded = float_round(qty_new,
                                                      precision_rounding=orderpoint.product_id.uom_id.rounding)
                            if qty_rounded < 0:
                                qty_rounded = 0.0
                            ctx.update({
                                'orderpoint_qty_multiple': orderpoint.qty_multiple
                            })
                            values = orderpoint._prepare_procurement_values(qty_rounded,
                                                                            **group['procurement_values'])
                            try:
                                with self._cr.savepoint():
                                    #TODO: make it batch
                                    if not qty_rounded:
                                        self.env['procurement.group'].with_context(ctx).run_zero([self.env['procurement.group'].Procurement(
                                            orderpoint.product_id, qty_rounded, orderpoint.product_uom,
                                            orderpoint.location_id, orderpoint.name, orderpoint.name,
                                            orderpoint.company_id, values)])
                                    else:
                                        self.env['procurement.group'].with_context(ctx).run([self.env['procurement.group'].Procurement(
                                            orderpoint.product_id, qty_rounded, orderpoint.product_uom,
                                            orderpoint.location_id, orderpoint.name, orderpoint.name,
                                            orderpoint.company_id, values)])
                                    orderpoint.update({
                                        'date_update': date_update,
                                        'virtual_available': virtual_available,
                                        'outgoing_qty': product_quantity_average[orderpoint.product_id.id]['outgoing_qty'],
                                        'incoming_qty': product_quantity_average[orderpoint.product_id.id]['incoming_qty'],
                                        'qty_available': qty_available,
                                        'product_weekly_outgoing_qty': product_quantity_weekly[orderpoint.product_id.id]['outgoing_qty'],
                                        'product_weekly_average_uom_sales_qty': qty_average_weekly,
                                    })
                            except UserError as error:
                                self.env['stock.rule']._log_next_activity(orderpoint.product_id, error.name)
                            self._procurement_from_orderpoint_post_process([orderpoint.id])
                            if use_new_cursor:
                                cr.commit()

                        except OperationalError:
                            if use_new_cursor:
                                orderpoints_noprefetch += [orderpoint.id]
                                cr.rollback()
                                continue
                            else:
                                raise

            try:
                if use_new_cursor:
                    cr.commit()
            except OperationalError:
                if use_new_cursor:
                    cr.rollback()
                    continue
                else:
                    raise

            if use_new_cursor:
                cr.commit()
                cr.close()
        return {}

    @api.model
    def run_zero(self, procurements):
        """ Method used in a procurement case. The purpose is to supply the
        product passed as argument in the location also given as an argument.
        In order to be able to find a suitable location that provide the product
        it will search among stock.rule.
        """
        actions_to_run = defaultdict(list)
        errors = []
        for procurement in procurements:
            procurement.values.setdefault('company_id', self.env.company)
            procurement.values.setdefault('priority', '1')
            procurement.values.setdefault('date_planned', fields.Datetime.now())
            rule = self._get_rule(procurement.product_id, procurement.location_id, procurement.values)
            if not rule:
                errors.append(_('No rule has been found to replenish "%s" in "%s".\nVerify the routes configuration on the product.') %
                    (procurement.product_id.display_name, procurement.location_id.display_name))
            else:
                action = 'pull' if rule.action == 'pull_push' else rule.action
                actions_to_run[action].append((procurement, rule))

        if errors:
            raise UserError('\n'.join(errors))

        for action, procurements in actions_to_run.items():
            if hasattr(self.env['stock.rule'], '_run_%s' % action):
                try:
                    getattr(self.env['stock.rule'], '_run_%s' % action)(procurements)
                except UserError as e:
                    errors.append(e.name)
            else:
                _logger.error("The method _run_%s doesn't exist on the procurement rules" % action)

        if errors:
            raise UserError('\n'.join(errors))
        return True
