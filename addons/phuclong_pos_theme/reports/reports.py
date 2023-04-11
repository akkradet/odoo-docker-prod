# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import time
from datetime import datetime, timedelta
import collections
import functools
import operator
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
FORMAT = {}

_logger = logging.getLogger(__name__)


class reportPosRevenueWizard(models.TransientModel):
    _name = "wizard.report.pos.date.revenue"

    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Stores', require=True)
    date = fields.Date('Date', require=True)
    error = fields.Boolean(string='Error')
    warning = fields.Text()
    warning_html = fields.Html()
    error_html = fields.Html()
    warning_state = fields.Selection([('warning', 'Has Warning'),
                                      ('warning_1', 'Warning Level 1'),
                                      ('warning_2', 'Warning Level 2'),
                                      ('none', 'None')], default='none')

    def print_date_revenue_report(self):
        return

    def button_warning_level_1(self):
        self.write({'warning_state': 'warning_1'})
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.report.pos.date.revenue',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def button_warning_level_2(self):
        self.write({'warning_state': 'warning_2',
                    'warning_html': _('If you do not process your pending bill at the end of the day, you will have 1 report. Continue ?')})
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.report.pos.date.revenue',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.onchange('warehouse_id', 'date')
    def onchange_check_draft_order(self):
        self.write({'error': False, 'error_html': False, 'warning_html': False})
        if self.warehouse_id and self.date:
            self._cr.execute('''
                SELECT po.name
                FROM pos_order po
                JOIN pos_session ps ON ps.id = po.session_id
                JOIN pos_config pc ON pc.id = ps.config_id
                WHERE po.state in ('draft') 
                AND pc.warehouse_id = %(warehouse_id)s
                AND timezone('UTC', po.date_order::timestamp) between '%(date_order)s 00:00:00' and '%(date_order)s 23:59:59'
            ''' % ({
                'warehouse_id': self.warehouse_id.id,
                'date_order': self.date
            }))
            list_pos = self._cr.dictfetchall()
            if list_pos:
                list_pos_html = '<ul>'
                for x in list_pos:
                    list_pos_html += '<li style="color:red;">%s</li>' % x['name']
                list_pos_html += '</ul>'
                warning_html = _(
                    '<p>There are some pending order:<p>') + list_pos_html
                self.write({'warning_html': warning_html,
                            'warning_state': 'warning'})
                return
            self._cr.execute('''
                SELECT po.id pos_id, pc.warehouse_id
                FROM pos_order po
                    JOIN pos_session ps ON ps.id = po.session_id
                    JOIN pos_config pc ON pc.id = ps.config_id
                    JOIN pos_order_line pol ON pol.order_id = po.id
                    JOIN product_product pp ON pp.id = pol.product_id 
                    JOIN product_template pt ON pp.product_tmpl_id = pt.id 
                    
                WHERE po.state in ('paid','done','invoiced') 
                    AND (pt.type IN ('product', 'consu') OR (pt.type = 'service' AND pt.fnb_type IN ('drink', 'food', 'topping')))
                    AND po.amount_total >= 0
                    AND pc.warehouse_id = %(warehouse_id)s
                    AND timezone('UTC',po.date_order::timestamp) between '%(date_order)s 00:00:00' and '%(date_order)s 23:59:59'
                    AND po.picking_id IS NULL AND po.picking_return_id IS NULL
                LIMIT 1
            ''' % ({
                'warehouse_id': self.warehouse_id.id,
                'date_order': self.date
            }))
            res_1 = self._cr.dictfetchall()
            res_2 = False
            res_3 = False
            if not res_1:
                self._cr.execute('''
                    SELECT po.id pos_id
                    FROM pos_order po
                        JOIN pos_session ps ON ps.id = po.session_id
                        JOIN pos_config pc ON pc.id = ps.config_id
                        JOIN pos_order_line pol ON pol.order_id = po.id
                        JOIN product_product pp ON pp.id = pol.product_id 
                        JOIN product_template pt ON pp.product_tmpl_id = pt.id 
                        JOIN stock_picking sp ON po.picking_id = sp.id 
                        
                    WHERE po.state in ('paid','done','invoiced') 
                        AND (pt.type IN ('product', 'consu') OR (pt.type = 'service' AND pt.fnb_type IN ('drink', 'food', 'topping')))
                        AND po.amount_total >= 0
                        AND pc.warehouse_id = %(warehouse_id)s
                        AND timezone('UTC',po.date_order::timestamp) between '%(date_order)s 00:00:00' and '%(date_order)s 23:59:59'
                        AND po.picking_id IS NOT NULL AND sp.state != 'done'
                    LIMIT 1
                ''' % ({
                    'warehouse_id': self.warehouse_id.id,
                    'date_order': self.date
                }))
                res_2 = self._cr.dictfetchall()
            if not res_1 and not res_2:
                self._cr.execute('''
                    SELECT po.id pos_id
                    FROM pos_order po
                        JOIN pos_session ps ON ps.id = po.session_id
                        JOIN pos_config pc ON pc.id = ps.config_id
                        JOIN pos_order_line pol ON pol.order_id = po.id
                        JOIN product_product pp ON pp.id = pol.product_id 
                        JOIN product_template pt ON pp.product_tmpl_id = pt.id 
                        JOIN stock_picking sp ON po.picking_return_id = sp.id 
                        
                    WHERE po.state in ('paid','done','invoiced') 
                        AND (pt.type IN ('product', 'consu') OR (pt.type = 'service' AND pt.fnb_type IN ('drink', 'food', 'topping')))
                        AND po.amount_total >= 0
                        AND pc.warehouse_id = %(warehouse_id)s
                        AND timezone('UTC',po.date_order::timestamp) between '%(date_order)s 00:00:00' and '%(date_order)s 23:59:59'
                        AND po.picking_return_id IS NOT NULL AND sp.state != 'done'
                    LIMIT 1
                ''' % ({
                    'warehouse_id': self.warehouse_id.id,
                    'date_order': self.date
                }))
                res_3 = self._cr.dictfetchall()
            if res_1 or res_2 or res_3:
                error_html = '<p style="color:red">' + \
                    _('Some Delivery Orders are not done yet. Please wait for a while so that the system can process these delivery orders.') + '</p>'
                self.write({'error': True, 'error_html': error_html,
                            'warning_state': 'none'})
                return
        if self.warning_state != 'none':
            self.write({'warning_state': 'none'})


class reportPosRevenueWizard(models.TransientModel):
    _name = "wizard.report.pos.revenue"

    apply_type = fields.Selection([('all_warehouse', 'All Warehouse'), ('select_warehouse',
                                                                        'Select Warehouse')], string="Apply Type", required=True, default="select_warehouse")

    @api.onchange('apply_type')
    def _onchange_apply_type(self):
        if self.apply_type == 'all_warehouse':
            self.warehouse_ids = [(6, 0, self.get_all_warehouse().ids)]
        else:
            self.warehouse_ids = [(6, 0, [])]

    def get_all_warehouse(self):
        return self.env['stock.warehouse'].with_context(user_access=True).search([])

    warehouse_ids = fields.Many2many(
        'stock.warehouse',
        'revenue_report_warehouse_rel',
        'wizard_id', 'warehouse_id',
        string='Stores')
    date_from = fields.Date('Date Time From', require=True)
    date_to = fields.Date('Date Time To')
    start_hour = fields.Float(string='Start Hour', default=0.0)
    end_hour = fields.Float(string='End Hour', default=23.983)
    type = fields.Selection([
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('payment_method', 'Payment Method'),
        ('revenue_product', 'Product'),
        ('revenue_product_vat', 'Product VAT'),
        ('revenue_stores', 'Revenue Stores'),
        ('payment_method_bill', 'Payment Method By Bill'),
        ('payment_method_day', 'Payment By Day'),
        ('combo', 'Revenue Combo'),
        ('discount', 'Discount')
    ], string='Report Type',
        default='hourly',
    )
    combo_id = fields.Many2one('sale.promo.combo', string='Combo')
    no_vat = fields.Boolean('No VAT')

    def export_report_by_hours(self):
        self.ensure_one()
        report_id = False
        if self.type == 'daily':
            report_id = self.env.ref(
                'phuclong_pos_theme.report_pos_revenue')
        elif self.type == 'hourly':
            report_id = self.env.ref(
                'phuclong_pos_theme.report_pos_hourly')
        elif self.type == 'revenue_product':
            report_id = self.env.ref(
                'phuclong_pos_theme.report_pos_revenue_product')
        elif self.type == 'revenue_product_vat':
            report_id = self.env.ref(
                'phuclong_pos_theme.report_pos_revenue_product_vat')
        elif self.type == 'revenue_stores':
            report_id = self.env.ref(
                'phuclong_pos_theme.report_pos_revenue_store')
        elif self.type == 'payment_method_bill':
            report_id = self.env.ref(
                'phuclong_pos_theme.report_pos_payment_method_bill')
        elif self.type == 'payment_method':
            report_id = self.env.ref(
                'phuclong_pos_theme.report_pos_payment_method')
        elif self.type == 'combo':
            report_id = self.env.ref(
                'phuclong_pos_theme.report_pos_combo')
        elif self.type == 'discount':
            report_id = self.env.ref(
                'phuclong_pos_theme.report_pos_discount')
        else:
            report_id = self.env.ref(
                'phuclong_pos_theme.report_pos_payment_by_day')
        if report_id:
            if self.env.user.has_group('phuclong_pos_base.group_store_accounting') or self.env.user.has_group('besco_pos_base.group_pos_store_manager'):
                queue = self.env['pos.report.queue.config'].get_queue(
                    self.type, (self.date_to - self.date_from).days + 1, len(self.warehouse_ids))
                if queue:
                    report_name = report_id._get_report_download_filename(
                        self.ids)
                    output_id = self.env['pos.report.queue.output'].create({
                        'ir_actions_report_id': report_id.id,
                        'report_name': report_name,
                        'warehouse_ids': [(6, 0, self.warehouse_ids.ids)],
                        'date_from': self.date_from,
                        'date_to': self.date_to,
                        'start_hour': self.start_hour,
                        'end_hour': self.end_hour,
                        'type': self.type,
                        'no_vat': self.no_vat,
                        'combo_id': self.combo_id and self.combo_id.id or False,
                    })
                    action = self.env.ref(
                        'phuclong_pos_theme.pos_report_queue_output_action').read()[0]
                    if output_id:
                        action['res_id'] = output_id.id
                        action['view_mode'] = 'form'
                        action['views'] = [(False, 'form')]
                    return action
            return report_id.report_action(self)

    def get_date_start(self):
        date_from = self.date_from
        if self.type == 'hourly':
            from_date_str_fm = self.date_from.strftime("%d/%m/%Y") + \
                ' {0:02.0f}:{1:02.0f}:00'
            date_from = from_date_str_fm.format(
                *divmod(float(self.start_hour) * 60, 60))
        else:
            from_date_str_fm = self.date_from.strftime("%d/%m/%Y") + \
                ' 00:00:00'
            date_from = from_date_str_fm.format(
                *divmod(float(self.start_hour) * 60, 60))
        return date_from

    def get_date_end(self):
        date_to = self.date_to
        if self.type == 'hourly':
            to_date_str_fm = self.date_to.strftime("%d/%m/%Y") + \
                ' {0:02.0f}:{1:02.0f}:00'
            date_to = to_date_str_fm.format(
                *divmod(float(self.end_hour) * 60, 60))
        else:
            to_date_str_fm = self.date_to.strftime("%d/%m/%Y") + \
                ' 23:59:59'
            date_to = to_date_str_fm.format(
                *divmod(float(self.end_hour) * 60, 60))
        return date_to

    def get_date_start_string(self):
        date = self.date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)
        date = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
        return date.strftime('%d/%m/%Y')

    def get_date_end_string(self):
        date = self.date_to.strftime(DEFAULT_SERVER_DATE_FORMAT)
        date = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
        return date.strftime('%d/%m/%Y')

    def get_current_date(self):
        date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')

    def get_current_datetime(self):
        date = time.strftime(DATETIME_FORMAT)
        date = self.env['res.users']._convert_user_datetime(date)
        return date.strftime('%d/%m/%Y %H:%M:%S')

    def get_str_date(self, date):
        date = datetime.strptime(date, '%d-%m-%Y')
        return date.strftime('%d/%m/%Y')

    def get_warehouse_selected(self):
        res = []
        for item in self.warehouse_ids:
            res.append(
                {
                    'warehouse_id': item.id,
                    'warehouse_name': item.name,
                    'warehouse_code': item.code,
                })
        return res

    def get_payment_method(self):
        sql = '''
                SELECT pp.payment_method_id, ppm.name || ' (' || currency_name || ')' method_name,
                currency_name FROM pos_payment pp JOIN pos_order po
                ON pp.pos_order_id = po.id AND po.warehouse_id in (%s)
                JOIN pos_payment_method ppm on pp.payment_method_id = ppm.id
                AND po.state in ('paid', 'done', 'invoiced')
                AND currency_name is not null and currency_name != ''
                AND DATE(timezone('UTC',po.date_order::timestamp)) between '%s' and '%s'
                GROUP BY pp.payment_method_id, ppm.name, ppm.use_for, currency_name
                ORDER BY ppm.use_for, currency_name
                ''' % (' ,'.join(map(str, [x.id for x in self.warehouse_ids])), self.date_from, self.date_to)
        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        #         method_ids = [x for x in result]
        #         method = self.env['pos.payment.method'].search([('id', 'in', method_ids)], order="use_for")
        return result

    def get_price_order_line(self, pos_line):
        pos = self.env['pos.order.line'].sudo().search_read(
            [('id', '=', pos_line)], ['price_unit'])
        return pos and pos[0]['price_unit'] or 0

    def get_payment_by_method(self, method_ids):
        sql = '''
                SELECT warehouse_id, payment_method_id, currency_name, sum(amount) amount FROM
                (SELECT case when (currency_name is null or currency_name = '') then 'VND' else currency_name end currency_name,
                amount, payment_method_id, ppm.name, ppm.use_for, po.warehouse_id
                FROM pos_payment pp JOIN pos_order po
                ON pp.pos_order_id = po.id AND po.warehouse_id in (%s)
                JOIN pos_payment_method ppm on pp.payment_method_id = ppm.id
                AND po.state in ('paid', 'done', 'invoiced') 
                AND payment_method_id in (%s)
                AND DATE(timezone('UTC',po.date_order::timestamp)) between '%s' and '%s') foo
                GROUP BY payment_method_id, name, use_for, currency_name, warehouse_id
                ORDER BY use_for, currency_name
                ''' % (' ,'.join(map(str, [x.id for x in self.warehouse_ids])), ' ,'.join(map(str, method_ids)), self.date_from, self.date_to)
        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        return result

    def get_order_payment_by_warehouse(self, warehouse_id=False):
        sql = '''
        select pos.name as pos_name, to_char(timezone('UTC',pos.date_order::timestamp), 'DD-MM-YYYY HH24:MI:SS') date_order,
        sale.name as sale_type, pay_method.name as pay_method, sw.code warehouse_code, sw.name warehouse_name,
        sum(pos_pay.amount) as amount, currency_name, sum(pos_pay.amount)/exchange_rate currency_origin_value, exchange_rate
        from pos_payment pos_pay
        left join pos_order pos on pos.id = pos_pay.pos_order_id
        left join pos_sale_type sale on sale.id = pos.sale_type_id
        left join pos_payment_method pay_method on pay_method.id = pos_pay.payment_method_id
        join stock_warehouse sw on pos.warehouse_id = sw.id
        where pos_pay.pos_order_id in (
                    select id
                    from pos_order
                    where
                        warehouse_id in (%(warehouse_ids)s) and
                        state in ('paid', 'done', 'invoiced')
                        and timezone('UTC',date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
                    )
        group by sw.id, pos_name, pos.date_order, sale.name, pay_method.name, currency_name, currency_origin_value, exchange_rate
        order by sw.code, pos.name
        ''' % ({
            'warehouse_ids': ' ,'.join(map(str, [x.id for x in self.warehouse_ids])),
            'date_from': self.date_from,
            'date_to': self.date_to,
        })
        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        return res

    def get_order_payment_by_day(self):
        sql = '''
        select sw.code warehouse_code, sw.name warehouse_name, aaa.code analytic_account_code,
        to_char(timezone('UTC',pos.date_order::timestamp), 'DD-MM-YYYY') as date_order, pay_method.name as pay_method,
        sum(pos_pay.amount) as total, count(distinct(pos.id)) num_bill
        from pos_payment pos_pay
        left join pos_order pos on pos.id = pos_pay.pos_order_id
        join stock_warehouse sw on pos.warehouse_id = sw.id
        JOIN account_analytic_account aaa on sw.account_analytic_id = aaa.id
        left join pos_payment_method pay_method on pay_method.id = pos_pay.payment_method_id
        where pos.warehouse_id in (%(warehouse_ids)s) and pos.state in ('paid', 'done', 'invoiced')
        and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
        group by sw.code, sw.name, aaa.code, to_char(timezone('UTC',pos.date_order::timestamp), 'DD-MM-YYYY'), pay_method.name
        ''' % ({
            'warehouse_ids': ' ,'.join(map(str, [x.id for x in self.warehouse_ids])),
            'date_from': self.date_from,
            'date_to': self.date_to,
        })
        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        return res

    def get_order_group_product_revenue_store_vat(self):
        sql = '''
        select
            res.warehouse_id, sw.name warehouse_name, sw.code warehouse_code,
            to_char(timezone('UTC',res.date::timestamp), 'DD/MM/YYYY') as date_order,
            pp.category_lv1,
            sum(res.price_total)/1.1*0.1 price_tax,
            (SUM(res.amount_surcharge)) as amount_surcharge,
            (sum(res.price_sub_total) + SUM(COALESCE(res.amount_surcharge, 0))) as price_sub_total,
            sum(res.total_discount) as total_discount,
            sum(res.price_total) as price_total
        from report_pos_order res
        left join product_product pp on pp.id = res.product_id
        left join pos_order pos on pos.id = res.order_id
        left join pos_order_line pos_l on pos_l.id = res.id
        join stock_warehouse sw on res.warehouse_id = sw.id
        where res.warehouse_id in (%(warehouse_ids)s) and timezone('UTC', res.date::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
        and res.state in ('paid', 'done', 'invoiced')
        and pp.category_lv1 is not null
        and pos.invoice_request IS TRUE
        group by
            res.warehouse_id, sw.name, sw.code,
            pp.category_lv1,
            to_char(timezone('UTC',res.date::timestamp), 'DD/MM/YYYY')
        order by res.warehouse_id,
            to_char(timezone('UTC',res.date::timestamp), 'DD/MM/YYYY'),
            pp.category_lv1
        ''' % ({
            'warehouse_ids': ' ,'.join(map(str, [x.id for x in self.warehouse_ids])),
            'date_from': self.date_from,
            'date_to': self.date_to,
        })
        self._cr.execute(sql)
        res_group = self._cr.dictfetchall()

        sql_detail = '''
        select
            res.product_id,
            res.warehouse_id,
            to_char(timezone('UTC',res.date::timestamp), 'DD/MM/YYYY') as date_order,
            uom.id as uom_id, uom.name as uom_name,
            pp.default_code,
            pt.ref_code,
            pp.category_lv1,
            categ.name as categ_name, pt.name as product_name,
            sum(res.product_qty) as qty,
            pos_l.price_unit as price_unit,
            sum(price_total) as price_total,
            (SUM(res.amount_surcharge)) as amount_surcharge,
            (sum(res.price_sub_total) + SUM(COALESCE(res.amount_surcharge, 0))) as price_sub_total,
            sum(res.price_total)/1.1*0.1 price_tax,
            sum(res.total_discount) as total_discount,
            sum(res.price_total) as price_total,
            pos.name as pos_name,
            pos.invoice_name,
            pos.invoice_vat,
            pos.invoice_address,
            pos.invoice_email,
            pos.invoice_contact,
            pos.invoice_note
        from report_pos_order res
        left join pos_order pos on pos.id = res.order_id
        left join pos_order_line pos_l on pos_l.id = res.id
        left join product_product pp on pp.id = res.product_id
        left join product_template pt on pt.id = pp.product_tmpl_id
        left join product_category categ on categ.id = pt.categ_id
        left join uom_uom uom on uom.id = pt.uom_id
        where res.warehouse_id in (%(warehouse_ids)s) and timezone('UTC', res.date::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
        and res.state in ('paid', 'done', 'invoiced')
        and pos.invoice_request IS TRUE
        group by res.product_id,
            res.warehouse_id,
            to_char(timezone('UTC',res.date::timestamp), 'DD/MM/YYYY'),
            uom.name, uom.id,
            pp.category_lv1,
            pp.default_code, pt.ref_code,
            categ.name, pp.display_name,pt.name,
            pos_l.price_unit,
            pos.name,
            pos.invoice_name,
            pos.invoice_vat,
            pos.invoice_address,
            pos.invoice_contact,
            pos.invoice_email,
            pos.invoice_note
        ''' % ({
            'warehouse_ids': ' ,'.join(map(str, [x.id for x in self.warehouse_ids])),
            'date_from': self.date_from,
            'date_to': self.date_to,
        })
        self._cr.execute(sql_detail)
        res_detail = self._cr.dictfetchall()

        for res in res_group:
            res['detail'] = list(filter(lambda p: p['warehouse_id'] == res['warehouse_id']
                                        and p['category_lv1'] == res['category_lv1']
                                        and p['date_order'] == res['date_order'],
                                        res_detail))
        return res_group

    def get_order_group_product_revenue_store(self):
        no_vat = ''
        if self.no_vat:
            no_vat = ''' and pos.invoice_request IS NOT TRUE  '''
        sql = '''
        select
            res.warehouse_id, sw.name warehouse_name, sw.code warehouse_code,
            to_char(timezone('UTC',res.date::timestamp), 'DD/MM/YYYY') as date_order,
            pp.category_lv1,
            sum(res.price_total)/1.1*0.1 price_tax,
            (SUM(res.amount_surcharge)) as amount_surcharge,
            (sum(res.price_sub_total) + SUM(COALESCE(res.amount_surcharge, 0))) as price_sub_total,
            sum(res.total_discount) as total_discount,
            sum(res.price_total) as price_total
        from report_pos_order res
        left join product_product pp on pp.id = res.product_id
        left join pos_order pos on pos.id = res.order_id
        left join pos_order_line pos_l on pos_l.id = res.id
        join stock_warehouse sw on res.warehouse_id = sw.id
        where res.warehouse_id in (%(warehouse_ids)s) and timezone('UTC', res.date::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
        and res.state in ('paid', 'done', 'invoiced')
        and pp.category_lv1 is not null
        %(no_vat)s
        group by
            res.warehouse_id, sw.name, sw.code,
            pp.category_lv1,
            to_char(timezone('UTC',res.date::timestamp), 'DD/MM/YYYY')
        order by res.warehouse_id,
            to_char(timezone('UTC',res.date::timestamp), 'DD/MM/YYYY'),
            pp.category_lv1
        ''' % ({
            'warehouse_ids': ' ,'.join(map(str, [x.id for x in self.warehouse_ids])),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'no_vat': no_vat
        })
        self._cr.execute(sql)
        res_group = self._cr.dictfetchall()

        sql_detail = '''
        select
            res.product_id,
            res.warehouse_id,
            to_char(timezone('UTC',res.date::timestamp), 'DD/MM/YYYY') as date_order,
            uom.id as uom_id, uom.name as uom_name,
            pp.default_code,
            pt.ref_code,
            pp.category_lv1,
            categ.name as categ_name, pt.name as product_name,
            sum(res.product_qty) as qty,
            pos_l.price_unit as price_unit,
            sum(price_total) as price_total,
            (SUM(res.amount_surcharge)) as amount_surcharge,
            (sum(res.price_sub_total) + SUM(COALESCE(res.amount_surcharge, 0))) as price_sub_total,
            sum(res.price_total)/1.1*0.1 price_tax,
            sum(res.total_discount) as total_discount,
            sum(res.price_total) as price_total
        from report_pos_order res
        left join pos_order pos on pos.id = res.order_id
        left join pos_order_line pos_l on pos_l.id = res.id
        left join product_product pp on pp.id = res.product_id
        left join product_template pt on pt.id = pp.product_tmpl_id
        left join product_category categ on categ.id = pt.categ_id
        left join uom_uom uom on uom.id = pt.uom_id
        where res.warehouse_id in (%(warehouse_ids)s) and timezone('UTC', res.date::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
        and res.state in ('paid', 'done', 'invoiced')
        %(no_vat)s
        group by res.product_id,
            res.warehouse_id,
            to_char(timezone('UTC',res.date::timestamp), 'DD/MM/YYYY'),
            uom.name, uom.id,
            pp.category_lv1,
            pp.default_code, pt.ref_code,
            categ.name, pp.display_name,pt.name,
            pos_l.price_unit
        ''' % ({
            'warehouse_ids': ' ,'.join(map(str, [x.id for x in self.warehouse_ids])),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'no_vat': no_vat
        })
        self._cr.execute(sql_detail)
        res_detail = self._cr.dictfetchall()

        for res in res_group:
            res['detail'] = list(filter(lambda p: p['warehouse_id'] == res['warehouse_id']
                                        and p['category_lv1'] == res['category_lv1']
                                        and p['date_order'] == res['date_order'],
                                        res_detail))

        return res_group

    def get_order_group_revenue_store(self):
        sql = '''
         select
            res.warehouse_id, sw.name warehouse_name, sw.code warehouse_code,
            to_char(timezone('UTC',pos.date_order::timestamp), 'DD/MM/YYYY') as date_order,
            pp.category_lv1,
            sum(res.price_total)/1.1*0.1 price_tax,
            sum(price_total) as price_total,
            (SUM(res.amount_surcharge)) as amount_surcharge,
            (sum(res.price_sub_total) + SUM(COALESCE(res.amount_surcharge, 0))) as price_sub_total,
            sum(res.total_discount) as total_discount,
            sum(res.price_total) as price_total
        from report_pos_order res
        left join product_product pp on pp.id = res.product_id
        left join pos_order pos on pos.id = res.order_id
        left join pos_order_line pos_l on pos_l.id = res.id
        join stock_warehouse sw on res.warehouse_id = sw.id
                
        where res.warehouse_id in (%(warehouse_ids)s) and timezone('UTC', res.date::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
        and res.state in ('paid', 'done', 'invoiced')
        group by
            res.warehouse_id, sw.name, sw.code,
            pp.category_lv1, to_char(timezone('UTC',pos.date_order::timestamp), 'DD/MM/YYYY'), timezone('UTC',pos.date_order::timestamp)::date
        order by timezone('UTC',pos.date_order::timestamp)::date
        ''' % ({
            'warehouse_ids': ' ,'.join(map(str, [x.id for x in self.warehouse_ids])),
            'date_from': self.date_from,
            'date_to': self.date_to,
        })
        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        return res

    def get_order_product_by_warehouse(self, warehouse_ids=False, date_order=False, category=False):
        if not warehouse_ids:
            warehouse_ids = self.warehouse_ids.ids
        if type(warehouse_ids) != list:
            warehouse_ids = [warehouse_ids]
        warehouse_ids_domain = ' ,'.join(map(str, [x for x in warehouse_ids]))
        if date_order:
            date_order = datetime.strptime(date_order, "%d/%m/%Y").date()
        select = ''
        group_by = ''
        left_join = ''
        where_category = ''
        if self.type == 'revenue_stores':
            select = """
            pos_l.id as pos_l, pos_l.price_unit, sum(res.price_total)/1.1*0.1 price_tax,
            pos.name as pos_name, to_char(timezone('UTC',pos.date_order::timestamp), 'DD/MM/YYYY HH24:MI:SS') as date_order,
            partner.name as partner_name, case when pt.fnb_type = 'drink' then concat(option_material.option_name , case when option_material.option_name != '' then ', ' end, 
                case when pos_l.cup_type is not null then (case when pos_l.cup_type != (select pcl.cup_type from product_cup_line pcl join product_cup_default pcd on pcl.cup_default_id = pcd.id 
                join product_template pt on pcd.product_id = pt.id join product_product pp on pp.product_tmpl_id = pt.id 
                join pos_order_line pol on pol.product_id = pp.id where pol.id = pos_l.id and pcd.sale_type_id = pos.sale_type_id order by pcl.sequence limit 1) then 
                (case when pos_l.cup_type = 'paper' then 'Ly giấy' when pos_l.cup_type = 'plastic' then 'Ly nhựa' when pos_l.cup_type = 'themos' then 'Ly giữ nhiệt' end) else '' end)
            else 'Không lấy Ly' end) else '' end as options,"""
            group_by = """ ,pos_l.id, pos_l.price_unit ,pos.name, pos.date_order, pos.sale_type_id, pt.fnb_type,
                partner.name, option_material.option_name
                order by res.warehouse_id, pos.date_order, pos.name """
            left_join = '''
                left join pos_order pos on pos.id = res.order_id
                left join pos_order_line pos_l on pos_l.id = res.id
                left join res_partner partner on partner.id = res.partner_id
                left join (select foo.id line_id, string_agg(concat(case when option_type = 'over' then 'Nhiều ' 
                    when option_type = 'below' then 'Ít ' when option_type = 'normal' then '' else 'Không ' end, 
                    foo.name, case when option_type = 'normal' then ' bình thường' else '' end) , ', ') option_name
                    from (select pol.id, pm.id material_id, pm.name from pos_order_line pol join product_product pp 
                    on pol.product_id = pp.id join product_template pt on pp.product_tmpl_id = pt.id
                    join product_material pm on pm.product_custom_id = pt.id
                    where pol.warehouse_id in (%(warehouse_ids_domain)s) and timezone('UTC', pol.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59') as foo
                    left join pos_order_line_option polo on foo.material_id = polo.option_id and foo.id = polo.line_id where polo.option_type != 'normal'
                    group by foo.id) option_material
                on pos_l.id = option_material.line_id
            ''' % ({
                'warehouse_ids_domain': warehouse_ids_domain,
                'date_from': self.date_from,
                'date_to': self.date_to,
                #                 'date_from': date_order if self.type == 'revenue_stores' else self.date_from,
                #                 'date_to': date_order if self.type == 'revenue_stores' else self.date_to,
            })
#             where_category = '''AND pp.category_lv1 = '%s' ''' % (category)

        sql = '''
        select
            %(select)s
            res.product_id,
            res.warehouse_id,
            sw.name warehouse_name,
            sw.code warehouse_code,
            uom.id as uom_id, uom.name as uom_name,
            pp.default_code,
            pt.ref_code,
            ps.name size_name,
            pp.category_lv1,
            categ.name as categ_name, pt.name as product_name,
            sum(res.product_qty) as qty,
            sum(price_total) as price_total,
            (SUM(res.amount_surcharge)) as amount_surcharge,
            (sum(res.price_sub_total) + SUM(COALESCE(res.amount_surcharge, 0))) as price_sub_total,
            sum(res.total_discount) as total_discount,
            sum(res.price_total) as price_total
        from report_pos_order res
        join stock_warehouse sw on res.warehouse_id = sw.id
        left join product_product pp on pp.id = res.product_id
        left join product_template pt on pt.id = pp.product_tmpl_id
        left join product_category categ on categ.id = pt.categ_id
        left join uom_uom uom on uom.id = pt.uom_id
        left join product_size ps on ps.id = pt.size_id
        %(left_join)s
        where res.warehouse_id in (%(warehouse_ids_domain)s) and timezone('UTC', res.date::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
        %(where_category)s
        and res.state in ('paid', 'done', 'invoiced')
        group by res.product_id,
            res.warehouse_id, sw.name, sw.code,
            uom.name, uom.id,
            pp.category_lv1,
            pp.default_code, pt.ref_code, ps.name,
            categ.name, pp.display_name,pt.name
            %(group_by)s
        ''' % ({
            'warehouse_ids_domain': warehouse_ids_domain,
            'date_from': self.date_from,
            'date_to': self.date_to,
            #             'date_from': date_order if self.type == 'revenue_stores' else self.date_from,
            #             'date_to': date_order if self.type == 'revenue_stores' else self.date_to,
            'select': select,
            'group_by': group_by,
            'left_join': left_join,
            'where_category': where_category
        })
        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        return res

    def get_order_line_by_warehouse(self, warehouse_id=False):
        where_combo = ''
        if self.combo_id:
            where_combo = 'and pol.combo_id = %s' % (self.combo_id.id)

        sql = """
        SELECT to_char(timezone('UTC',date_order::timestamp),'dd/mm/YYYY') date_order, warehouse_name, combo_name, product_name as name_product, qty, price_unit, total, concat(combo_seq, '.', position_combo) as stt
        FROM(
            SELECT po.date_order, po.warehouse_id, po.id as pos_id, pol.combo_id, pol.fe_uid, pol.id as pol_id,
            pol.product_id, pol.qty as qty, pol.price_unit, pol.price_subtotal_incl as total, 
            war.name warehouse_name, com.name combo_name, pro.display_name product_name, po.id as pos_id, pol.combo_id as combo_id, pol.combo_seq as combo_seq, pol.fe_uid,
            row_number() OVER(PARTITION BY po.id, pol.combo_id, pol.combo_seq ORDER BY pol.fe_uid ASC) AS position_combo
            from pos_order_line as pol
                join pos_order as po on pol.order_id = po.id
                join product_product as pro on pro.id = pol.product_id
                join stock_warehouse as war on war.id = po.warehouse_id
                join sale_promo_combo as com on com.id = pol.combo_id
            WHERE po.state in ('paid', 'done', 'invoiced') and po.warehouse_id in (%(warehouse_ids)s)
            and pol.combo_id is not null %(where_combo)s
            and timezone('UTC',po.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
            ORDER BY war.code, po.date_order, pol.fe_uid ASC
        ) as group_table
        """ % ({
            'warehouse_ids': ','.join(map(str, [x.id for x in self.warehouse_ids])),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'where_combo': where_combo
        })
        self._cr.execute(sql)
        return self._cr.dictfetchall()

    def get_combo_by_warehouse(self, warehouse_id=False):
        where_combo = ''
        if self.combo_id:
            where_combo = 'and pol.combo_id = %s' % (self.combo_id.id)

        sql = """
        select warehouse_name, date_order, combo_id, combo_name, count(pos_id) as sum_qty, sum(sum_price_total) as sum_price_total
        from 
            (select to_char(timezone('UTC',pos.date_order::timestamp),'dd/mm/YYYY') date_order, pol.combo_id, com.name as combo_name, 
            war.code warehouse_code, war.name warehouse_name,
            sum(pol.qty) as sum_qty, sum(pol.price_subtotal_incl) as sum_price_total, pos.id as pos_id, pol.combo_seq as combo_seq
            from pos_order_line as pol
                join pos_order as pos on pol.order_id = pos.id
                join sale_promo_combo as com on com.id = pol.combo_id
                join stock_warehouse as war on war.id = pos.warehouse_id
            where pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id in (%(warehouse_ids)s)
            and pol.combo_id is not null %(where_combo)s
            and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
            group by war.code, war.name, pos.date_order, pol.combo_id, com.name, pos.id, pol.combo_seq
            order by war.code) as group_table
        group by warehouse_code, warehouse_name, date_order, combo_id, combo_name
        """ % ({
            'warehouse_ids': ','.join(map(str, [x.id for x in self.warehouse_ids])),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'where_combo': where_combo
        })
        self._cr.execute(sql)
        return self._cr.dictfetchall()

    def get_discount_by_warehouse(self, warehouse_id):
        sql = """
        SELECT to_char(date_order,'dd-mm-YYYY') date_order, warehouse_name, name_discount, count(pos_id) as qty_pos, pos_id,
        (discount_price + pos_discount) as total_discount, discount_price, pos_discount
        FROM 
            ((select timezone('UTC',pos.date_order::timestamp) as date_order, war.name as warehouse_name, pos.id as pos_id,
            sal_head.name as name_discount,
         CASE WHEN sal_line.modify_type = 'disc_percent' THEN sum((pol.price_unit * pol.qty) * (sal_line.discount_value / 100))
         WHEN sal_line.modify_type = 'disc_value' THEN sum(sal_line.discount_value)
         END as discount_price, 0 as pos_discount
        from pos_order as pos
        join pos_order_line as pol on pos.id = pol.order_id
        join sale_promo_header as sal_head on sal_head.id = pos.promotion_id
        join sale_promo_lines as sal_line on sal_line.id = pol.promotion_line_id
        join stock_warehouse as war on war.id = pos.warehouse_id
        where pos.promotion_id is not null and pos.discount_amount < 0 and (pol.discount_amount = 0 and pol.discount = 0 and pol.loyalty_discount_percent = 0)
          and pol.promotion_line_id is not null and pol.is_condition_line = False and pol.is_promotion_line is not True and pol.promotion_id is null
          and pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id = %(warehouse_id)s
         and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
         GROUP BY sal_head.name, pos.id, war.name, pos.date_order, sal_line.modify_type
        order by date_order ASC)
         
         UNION ALL
         
         (select timezone('UTC',pos.date_order::timestamp) as date_order, war.name as warehouse_name, pos.id as pos_id, sal_head.name as name_discount,
          sum(sal_line.discount_value) as discount_price, 0 as pos_discount 
        from pos_order_line as pol
        join pos_order as pos on pos.id = pol.order_id
        join sale_promo_header as sal_head on sal_head.id = pol.promotion_id
        join sale_promo_lines as sal_line on sal_line.id = pol.promotion_line_id
        join stock_warehouse as war on war.id = pos.warehouse_id
          join hr_employee as emp on emp.id = pos.cashier_id
        where pos.promotion_id is null and (pol.discount_amount = 0 and pol.discount = 0 and pol.loyalty_discount_percent = 0)
         and pol.promotion_line_id is not null and pol.promotion_id is not null and sal_line.modify_type = 'fix_value'
          and pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id = %(warehouse_id)s
          and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
         GROUP BY sal_head.name, pos.id, war.name, pos.date_order
         order by date_order ASC)
         
         UNION ALL
         
         (select timezone('UTC',pos.date_order::timestamp) as date_order, war.name as warehouse_name, pos.id as pos_id, sal.name as name_discount,
        CASE WHEN pol.discount_amount > 0 THEN sum(pol.discount_amount)
        WHEN pol.discount > 0 THEN sum((pol.price_unit * pol.qty) * (pol.discount / 100))
        END as discount_price, pos.discount_amount as pos_discount
        from pos_order_line as pol
        join pos_order as pos on pos.id = pol.order_id
        join sale_promo_header as sal on sal.id = pos.promotion_id
        join stock_warehouse as war on war.id = pos.warehouse_id
        join hr_employee as emp on emp.id = pos.cashier_id
        where pos.promotion_id is not null and pos.discount_amount < 0 and (pol.discount_amount > 0 or pol.discount > 0)
            and pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id = %(warehouse_id)s
          and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
         GROUP BY sal.name, pos.id, war.name, pos.date_order, pol.discount_amount, pol.discount
          order by date_order ASC)
         
         UNION ALL
         
         (select timezone('UTC',pos.date_order::timestamp) as date_order, war.name as warehouse_name, pos.id as pos_id, concat(pol.loyalty_discount_percent,'%(add_percent)s ', loy.level_name) as name_discount,  
         sum((pol.qty * pol.price_unit) * ((100 - pol.discount) / 100) * (pol.loyalty_discount_percent / 100)) as discount_price, 0 as pos_discount
        from pos_order_line as pol
        join pos_order as pos on pos.id = pol.order_id
        join res_partner as par on par.id = pos.partner_id
        join loyalty_level as loy on loy.id = par.loyalty_level_id
        join stock_warehouse as war on war.id = pos.warehouse_id
        join hr_employee as emp on emp.id = pos.cashier_id
        where pos.promotion_id is null and pol.is_loyalty_line = True and pos.partner_id is not null and pol.loyalty_discount_percent > 0
            and pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id = %(warehouse_id)s
          and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
         GROUP BY pol.loyalty_discount_percent, pos.id, war.name, pos.date_order, pol.discount_amount, pol.discount, loy.level_name
         order by date_order ASC)
         
         UNION ALL
         
         (select timezone('UTC',pos.date_order::timestamp) as date_order, war.name as warehouse_name, pos.id as pos_id, sal.name as name_discount,
        sum(pl.list_price) as discount_price, 0 as pos_discount
        from pos_order_line as pol
        join pos_order as pos on pos.id = pol.order_id
        join sale_promo_header as sal on sal.id = pol.promotion_id
        join stock_warehouse as war on war.id = pos.warehouse_id
        join hr_employee as emp on emp.id = pos.cashier_id
        join product_product as pro on pro.id = pol.product_id
        join product_template as pl on pl.id = pro.product_tmpl_id
        where pol.is_promotion_line = True and pol.promotion_id is not null
            and pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id = %(warehouse_id)s
          and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
          GROUP BY pos.id, war.name, pos.date_order, sal.name
         order by date_order ASC)
        
        ) as group_table
        group by date_order, warehouse_name, name_discount, pos_id, discount_price, pos_discount
        """
        self._cr.execute(sql % ({
            'warehouse_id': warehouse_id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'add_percent': "%"
        }))
        return self._cr.dictfetchall()

    def get_discount_by_warehouses(self):
        sql = """
            SELECT date_order, warehouse_name, name_discount, sum(qty_pos) as qty_pos, sum(total_discount) as total_discount FROM (
            SELECT to_char(date_order,'dd-mm-YYYY') date_order, warehouse_name, name_discount, count(pos_id) as qty_pos, sum(total_discount) as total_discount
            FROM ((select timezone('UTC',pos.date_order::timestamp) as date_order, war.name as warehouse_name, pos.id as pos_id, sal_head.name as name_discount,
            pos.discount_amount as total_discount
            from pos_order as pos
            join pos_order_line as pol on pos.id = pol.order_id
            join sale_promo_header as sal_head on sal_head.id = pos.promotion_id
            join stock_warehouse as war on war.id = pos.warehouse_id
            where pos.promotion_id is not null and pos.discount_amount < 0
            and pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id in (%(warehouse_ids)s)
            and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
            GROUP BY sal_head.name, pos.id, war.name, pos.date_order
            order by date_order ASC)
            UNION ALL
            (select timezone('UTC',pos.date_order::timestamp) as date_order, war.name as warehouse_name, pos.id as pos_id, concat(pol.loyalty_discount_percent, '%(add_percent)s ', loy.level_name) as name_discount,  
            sum((pol.qty * pol.price_unit) * ((100 - pol.discount) / 100) * (pol.loyalty_discount_percent / 100)) * (-1) as total_discount
            from pos_order as pos
            join pos_order_line as pol on pos.id = pol.order_id
            join res_partner as par on par.id = pos.partner_id
            join loyalty_level as loy on loy.id = pos.partner_loyalty_level_id
            join stock_warehouse as war on war.id = pos.warehouse_id
            where pos.promotion_id is null and pos.partner_id is not null and pol.loyalty_discount_percent > 0
            and pol.is_loyalty_line = True
            and pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id in (%(warehouse_ids)s)
            and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
            GROUP BY pol.loyalty_discount_percent, pos.id, war.name, pos.date_order, pol.discount_amount, pol.discount, loy.level_name
            order by date_order ASC)
            UNION ALL
            (select timezone('UTC',pos.date_order::timestamp) as date_order, war.name as warehouse_name, pos.id as pos_id, sal.name as name_discount,
            sum(pol.qty * (pol.old_price - pol.price_unit)) * (-1) as total_discount
            from pos_order as pos
            join pos_order_line as pol on pos.id = pol.order_id
            join sale_promo_header as sal on sal.id = pol.promotion_id
            join stock_warehouse as war on war.id = pos.warehouse_id
            where pos.promotion_id is null and pol.promotion_id is not null
            and pol.is_promotion_line = True and (pol.is_loyalty_line is null or pol.is_loyalty_line != True)
            and pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id in (%(warehouse_ids)s)
            and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
            GROUP BY pos.id, war.name, pos.date_order, sal.name
            order by date_order ASC)
            UNION ALL
            (select timezone('UTC',pos.date_order::timestamp) as date_order, war.name as warehouse_name, pos.id as pos_id, sal.name as name_discount,
            CASE WHEN pol.discount_amount > 0 THEN sum(pol.discount_amount) * (-1)
            WHEN pol.discount > 0 THEN sum((pol.price_unit * pol.qty) * (pol.discount / 100)) * (-1)
            END as total_discount
            from pos_order as pos
            join pos_order_line as pol on pos.id = pol.order_id
            join sale_promo_header as sal on sal.id = pol.promotion_id
            join stock_warehouse as war on war.id = pos.warehouse_id
            where pos.promotion_id is null
            and (pol.is_manual_discount is null or pol.is_manual_discount != True) and (pol.is_promotion_line is null or pol.is_promotion_line != True) and (pol.is_loyalty_line is null or pol.is_loyalty_line != True)
            and (pol.discount > 0 or pol.discount_amount > 0) and pol.promotion_id is not null
            and pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id in (%(warehouse_ids)s)
            and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
            GROUP BY pos.id, war.name, pos.date_order, sal.name, pol.discount_amount, pol.discount
            order by date_order ASC)
            UNION ALL
            (select timezone('UTC',pos.date_order::timestamp) as date_order, war.name as warehouse_name, pos.id as pos_id, 'Giảm giá trực tiếp' as name_discount,
            CASE WHEN pol.discount_amount > 0 THEN sum(pol.discount_amount) * (-1)
            WHEN pol.discount > 0 THEN sum((pol.price_unit * pol.qty) * (pol.discount / 100)) * (-1)
            WHEN pos.discount_amount < 0 THEN pos.discount_amount
            ELSE sum((pol.old_price - pol.price_unit) * pol.qty) * (-1)
            END as total_discount
            from pos_order as pos
            join pos_order_line as pol on pos.id = pol.order_id
            join stock_warehouse as war on war.id = pos.warehouse_id
            where pos.promotion_id is null
            and pol.is_manual_discount = True and (pol.is_promotion_line is null or pol.is_promotion_line != True) and (pol.is_loyalty_line is null or pol.is_loyalty_line != True)
            and pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id in (%(warehouse_ids)s)
            and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
            GROUP BY pos.id, war.name, pos.date_order, pol.discount_amount, pol.discount
            order by date_order ASC)
            ) as foo_1
            GROUP BY date_order, warehouse_name, name_discount) as foo_2
            GROUP BY date_order, warehouse_name, name_discount
            order by date_order ASC, warehouse_name, name_discount
        """
        self._cr.execute(sql % ({
            'warehouse_ids': ','.join(map(str, [x.id for x in self.warehouse_ids])),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'add_percent': "%"
        }))
        return self._cr.dictfetchall()

    def get_detail_discount_by_warehouses(self):
        sql = """
            SELECT date_order, warehouse_name, name_bill, name_discount, type_discount, pol_discount, sum(pol_discount_amount) as pol_discount_amount, discount_loyalty, sum(discount_price) as discount_price, cashier_name
            FROM (
            SELECT to_char(date_order,'dd-mm-YYYY') date_order, warehouse_name, name_bill, name_discount, type_discount, pol_discount, sum(pol_discount_amount) as pol_discount_amount, discount_loyalty, sum(discount_price) as discount_price, cashier_name
            FROM ((select timezone('UTC',pos.date_order::timestamp) as date_order, war.name as warehouse_name, pos.name as name_bill, sal_head.name as name_discount,
            'Giảm giá lượng tiền' as type_discount,
            '0' as pol_discount,
            pos.discount_amount as pol_discount_amount,
            '0' as discount_loyalty,
            pos.discount_amount as discount_price,
            emp.name as cashier_name
            from pos_order as pos
            join pos_order_line as pol on pos.id = pol.order_id
            join sale_promo_header as sal_head on sal_head.id = pos.promotion_id
            join stock_warehouse as war on war.id = pos.warehouse_id
            join hr_employee as emp on emp.id = pos.cashier_id
            where pos.promotion_id is not null and pos.discount_amount < 0
            and pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id in (%(warehouse_ids)s)
            and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
            GROUP BY sal_head.name, pos.name, war.name, pos.date_order, pos.discount_amount, emp.name
            order by date_order ASC)
            UNION ALL
            (select timezone('UTC',pos.date_order::timestamp) as date_order, war.name as warehouse_name, pos.name as name_bill, concat(pol.loyalty_discount_percent, '%(add_percent)s ', loy.level_name) as name_discount,  
            'Giảm giá loyalty' as type_discount,
            '0' as pol_discount,
            0 as pol_discount_amount,
            concat(pol.loyalty_discount_percent, ' %(add_percent)s') as discount_loyalty,
            sum((pol.qty * pol.price_unit) * ((100 - pol.discount) / 100) * (pol.loyalty_discount_percent / 100)) * (-1) as discount_price,
            emp.name as cashier_name
            from pos_order_line as pol
            join pos_order as pos on pos.id = pol.order_id
            join res_partner as par on par.id = pos.partner_id
            join loyalty_level as loy on loy.id = pos.partner_loyalty_level_id
            join stock_warehouse as war on war.id = pos.warehouse_id
            join hr_employee as emp on emp.id = pos.cashier_id
            where pos.promotion_id is null and pos.partner_id is not null and pol.loyalty_discount_percent > 0
            and pol.is_loyalty_line = True
            and pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id in (%(warehouse_ids)s)
            and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
            GROUP BY pol.loyalty_discount_percent, pos.name, war.name, pos.date_order, pol.discount_amount, pol.discount, loy.level_name, emp.name
            order by date_order ASC)
            UNION ALL
            (select timezone('UTC',pos.date_order::timestamp) as date_order, war.name as warehouse_name, pos.name as name_bill, sal.name as name_discount,
            'Quà tặng' as type_discount,
            CASE WHEN pol.old_price > 0 THEN concat(((1 - pol.qty * pol.price_unit/pol.old_price)*100)::integer, ' %(add_percent)s') 
            ELSE '100 %(add_percent)s'
            END as pol_discount,
            0 as pol_discount_amount,
            '0' as discount_loyalty,
            sum(pol.qty * (pol.old_price - pol.price_unit)) * (-1) as discount_price,
            emp.name as cashier_name
            from pos_order_line as pol
            join pos_order as pos on pos.id = pol.order_id
            join sale_promo_header as sal on sal.id = pol.promotion_id
            join stock_warehouse as war on war.id = pos.warehouse_id
            join hr_employee as emp on emp.id = pos.cashier_id
            where pos.promotion_id is null and pol.promotion_id is not null
            and pol.is_promotion_line = True and (pol.is_loyalty_line is null or pol.is_loyalty_line != True)
            and pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id in (%(warehouse_ids)s)
            and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
            GROUP BY pos.name, war.name, pos.date_order, sal.name, emp.name, pol.qty, pol.price_unit, pol.old_price
            order by date_order ASC)
            UNION ALL
            (select timezone('UTC',pos.date_order::timestamp) as date_order, war.name as warehouse_name, pos.name as name_bill, sal.name as name_discount,
            CASE WHEN pol.discount_amount > 0 THEN 'Giảm giá lượng tiền'
            WHEN pol.discount > 0 THEN concat('Giảm giá', ' %(add_percent)s')
            END as type_discount,
            CASE WHEN pol.discount_amount > 0 THEN '0'
            WHEN pol.discount > 0 THEN concat(pol.discount, ' %(add_percent)s')
            END as pol_discount,
            CASE WHEN pol.discount_amount > 0 THEN pol.discount_amount
            WHEN pol.discount > 0 THEN 0
            END as pol_discount_amount,
            '0' as discount_loyalty,
            CASE WHEN pol.discount_amount > 0 THEN sum(pol.discount_amount) * (-1)
            WHEN pol.discount > 0 THEN sum((pol.price_unit * pol.qty) * (pol.discount / 100)) * (-1)
            END as discount_price,
            emp.name as cashier_name
            from pos_order_line as pol
            join pos_order as pos on pos.id = pol.order_id
            join sale_promo_header as sal on sal.id = pol.promotion_id
            join stock_warehouse as war on war.id = pos.warehouse_id
            join hr_employee as emp on emp.id = pos.cashier_id
            where pos.promotion_id is null
            and (pol.is_manual_discount is null or pol.is_manual_discount != True) and (pol.is_promotion_line is null or pol.is_promotion_line != True) and (pol.is_loyalty_line is null or pol.is_loyalty_line != True)
            and (pol.discount > 0 or pol.discount_amount > 0) and pol.promotion_id is not null
            and pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id in (%(warehouse_ids)s)
            and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
            GROUP BY pos.name, war.name, pos.date_order, sal.name, pol.discount_amount, pol.discount, emp.name
            order by date_order ASC)
            UNION ALL
            (select timezone('UTC',pos.date_order::timestamp) as date_order, war.name as warehouse_name, pos.name as name_bill, 'Giảm giá trực tiếp' as name_discount,
            CASE WHEN pol.discount_amount > 0 THEN 'Giảm giá lượng tiền'
            WHEN pol.discount > 0 THEN concat('Giảm giá', ' %(add_percent)s')
            ELSE 'Giảm giá lượng tiền'
            END as type_discount,
            CASE WHEN pol.discount_amount > 0 THEN '0'
            WHEN pol.discount > 0 THEN concat(pol.discount, ' %(add_percent)s')
            ELSE '0'
            END as pol_discount,
            CASE WHEN pol.discount_amount > 0 THEN pol.discount_amount
            WHEN pol.discount > 0 THEN 0
            WHEN pos.discount_amount < 0 THEN pos.discount_amount
            ELSE sum((pol.old_price - pol.price_unit) * pol.qty) * (-1)
            END as pol_discount_amount,
            '0' as discount_loyalty,
            CASE WHEN pol.discount_amount > 0 THEN sum(pol.discount_amount) * (-1)
            WHEN pol.discount > 0 THEN sum((pol.price_unit * pol.qty) * (pol.discount / 100)) * (-1)
            WHEN pos.discount_amount < 0 THEN pos.discount_amount
            ELSE sum((pol.old_price - pol.price_unit) * pol.qty) * (-1)
            END as discount_price,
            emp.name as cashier_name
            from pos_order_line as pol
            join pos_order as pos on pos.id = pol.order_id
            join stock_warehouse as war on war.id = pos.warehouse_id
            join hr_employee as emp on emp.id = pos.cashier_id
            where pos.promotion_id is null
            and pol.is_manual_discount = True and (pol.is_promotion_line is null or pol.is_promotion_line != True) and (pol.is_loyalty_line is null or pol.is_loyalty_line != True)
            and pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id in (%(warehouse_ids)s)
            and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
            GROUP BY pos.name, war.name, pos.date_order, pol.discount_amount, pol.discount, emp.name, pos.discount_amount, pos.id
            order by date_order ASC)) as foo_1
            GROUP BY date_order, warehouse_name, name_bill, type_discount, name_discount, pol_discount, discount_loyalty, cashier_name) as foo_2
            GROUP BY date_order, warehouse_name, name_bill, type_discount, name_discount, pol_discount, discount_loyalty, cashier_name
            order by date_order ASC
        """
        self._cr.execute(sql % ({
            'warehouse_ids': ','.join(map(str, [x.id for x in self.warehouse_ids])),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'add_percent': "%"
        }))
        return self._cr.dictfetchall()

    def get_detail_discount_by_warehouse(self, warehouse_id):
        sql = """
        SELECT to_char(date_order,'dd-mm-YYYY') date_order, warehouse_name, name_discount, name_bill, type_discount, pol_discount, pol_discount_amount, discount_loyalty, discount_price, cashier_name, pol_id FROM(
            (select timezone('UTC',pos.date_order::timestamp) as date_order, war.name as warehouse_name, sal_head.name as name_discount, pos.name as name_bill,
             'Giảm giá lượng tiền' as type_discount, concat(pol.discount,'%(add_percent)s') as pol_discount, sal_line.discount_value as pol_discount_amount,
             concat(pol.loyalty_discount_percent,'%(add_percent)s') as discount_loyalty, sal_line.discount_value as discount_price,
            emp.name as cashier_name, pol.id as pol_id, pos.id as pos_id
            from pos_order_line as pol
            join pos_order as pos on pos.id = pol.order_id
            join sale_promo_header as sal_head on sal_head.id = pol.promotion_id
            join sale_promo_lines as sal_line on sal_line.id = pol.promotion_line_id
            join stock_warehouse as war on war.id = pos.warehouse_id
              join hr_employee as emp on emp.id = pos.cashier_id
            where pos.promotion_id is null and (pol.discount_amount = 0 and pol.discount = 0 and pol.loyalty_discount_percent = 0)
             and pol.promotion_line_id is not null and pol.promotion_id is not null and sal_line.modify_type = 'fix_value'
              and pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id = %(warehouse_id)s
              and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59')
            
            UNION ALL
            
            
            (select timezone('UTC',pos.date_order::timestamp) as date_order, war.name as warehouse_name, sal_head.name as name_discount, pos.name as name_bill,
             CASE WHEN sal.modify_type = 'disc_percent' THEN 'Giảm giá %(add_percent)s'
             WHEN sal.modify_type = 'disc_value' or sal.modify_type = 'fix_value' THEN 'Giảm giá lượng tiền'
             END as type_discount,
             CASE WHEN sal.modify_type = 'disc_percent' THEN concat(sal.discount_value,'%(add_percent)s')
             ELSE concat(pol.discount,'%(add_percent)s')
             END as pol_discount,
             CASE WHEN sal.modify_type = 'disc_value' or sal.modify_type = 'fix_value' THEN sal.discount_value
             ELSE pol.discount_amount
             END as pol_discount_amount,
             concat(pol.loyalty_discount_percent,'%(add_percent)s') as discount_loyalty,
             CASE WHEN sal.modify_type = 'disc_percent' THEN (pol.price_unit * pol.qty) * (sal.discount_value / 100)
             WHEN sal.modify_type = 'disc_value' or sal.modify_type = 'fix_value' THEN sal.discount_value
             END as discount_price,
            emp.name as cashier_name, pol.id as pol_id, pos.id as pos_id
            from pos_order as pos
            join pos_order_line as pol on pos.id = pol.order_id
            join sale_promo_lines as sal on sal.id = pol.promotion_line_id
            join sale_promo_header as sal_head on sal_head.id = pos.promotion_id
            join stock_warehouse as war on war.id = pos.warehouse_id
              join hr_employee as emp on emp.id = pos.cashier_id
            where pos.promotion_id is not null and pos.discount_amount < 0 and (pol.discount_amount = 0 and pol.discount = 0 and pol.loyalty_discount_percent = 0)
             and pol.promotion_line_id is not null and pol.is_condition_line = False and pol.is_promotion_line is not True and pol.promotion_id is null
              and pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id = %(warehouse_id)s
              and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59')
            
            UNION ALL
            
            (select timezone('UTC',pos.date_order::timestamp) as date_order, war.name as warehouse_name, sal.name as name_discount, pos.name as name_bill,
            CASE
            WHEN pol.discount_amount > 0 or pos.discount_amount < 0 THEN 'Giảm giá lượng tiền'
            WHEN pol.discount > 0 THEN 'Giảm giá %(add_percent)s'
            END as type_discount,
            concat(pol.discount,'%(add_percent)s') as pol_discount, pol.discount_amount as pol_discount_amount, concat(pol.loyalty_discount_percent,'%(add_percent)s') as discount_loyalty, 
            CASE WHEN pol.discount_amount > 0 THEN pol.discount_amount
            WHEN pol.discount > 0 THEN (pol.price_unit * pol.qty) * (pol.discount / 100)
            END as discount_price, emp.name as cashier_name, pol.id as pol_id, pos.id as pos_id
            from pos_order_line as pol
            join pos_order as pos on pos.id = pol.order_id
            join sale_promo_header as sal on sal.id = pos.promotion_id
            join stock_warehouse as war on war.id = pos.warehouse_id
            join hr_employee as emp on emp.id = pos.cashier_id
            where pos.promotion_id is not null and pos.discount_amount < 0 and (pol.discount_amount > 0 or pol.discount > 0)
                and pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id = %(warehouse_id)s
              and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59')
        
            UNION ALL
        
            (select timezone('UTC',pos.date_order::timestamp) as date_order, war.name as warehouse_name, concat(pol.loyalty_discount_percent,'%(add_percent)s ', loy.level_name) as name_discount, 
             pos.name as name_bill, 'Giảm giá loyalty' as type_discount,
             concat(pol.discount,'%(add_percent)s') as pol_discount, pol.discount_amount as pol_discount_amount, concat(pol.loyalty_discount_percent,'%(add_percent)s') as discount_loyalty, 
             (pol.qty * pol.price_unit) * ((100 - pol.discount) / 100) * (pol.loyalty_discount_percent / 100) as discount_price, emp.name as cashier_name, pol.id as pol_id, pos.id as pos_id
            from pos_order_line as pol
            join pos_order as pos on pos.id = pol.order_id
            join res_partner as par on par.id = pos.partner_id
            join loyalty_level as loy on loy.id = par.loyalty_level_id
            join stock_warehouse as war on war.id = pos.warehouse_id
            join hr_employee as emp on emp.id = pos.cashier_id
            where pos.promotion_id is null and pol.is_loyalty_line = True and pos.partner_id is not null and pol.loyalty_discount_percent > 0
                and pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id = %(warehouse_id)s
              and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59')
            
            UNION ALL
            
            (select timezone('UTC',pos.date_order::timestamp) as date_order, war.name as warehouse_name, sal.name as name_discount, pos.name as name_bill,
             'Quà tặng' as type_discount, '100%(add_percent)s' as pol_discount, 0 as pol_discount_amount, concat(pol.loyalty_discount_percent,'%(add_percent)s') as discount_loyalty, 
            pl.list_price as discount_price, emp.name as cashier_name, pol.id as pol_id, pos.id as pos_id
            from pos_order_line as pol
            join pos_order as pos on pos.id = pol.order_id
            join sale_promo_header as sal on sal.id = pol.promotion_id
            join stock_warehouse as war on war.id = pos.warehouse_id
            join hr_employee as emp on emp.id = pos.cashier_id
            join product_product as pro on pro.id = pol.product_id
            join product_template as pl on pl.id = pro.product_tmpl_id
            where pol.is_promotion_line = True and pol.promotion_id is not null
                and pos.state in ('paid', 'done', 'invoiced') and pos.warehouse_id = %(warehouse_id)s
              and timezone('UTC',pos.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59')
            
        ) as group_table
        order by pol_id ASC
        """
        self._cr.execute(sql % ({
            'warehouse_id': warehouse_id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'add_percent': "%"
        }))
        return self._cr.dictfetchall()

    def get_order_by_warehouse(self, warehouse_id=False, from_hour=False, to_hour=False):
        sql = '''
        select
            sw.id warehouse_id,
            sw.name warehouse_name,
            sw.code warehouse_code,
            pos_order.num_bill as num_bill,
            pos_order.total as amount_total,
            pos_order.discount as order_discount,
            pos_order.surcharge as surcharge,
            order_line.old as orderline_old_price,
            round(order_line.discount_line, 5) as discount_line,
            pos_order.date_order
        from (
            select
                count(id) num_bill,
                sum(amount_total) total,
                sum(discount_amount) discount,
                sum(total_surcharge) surcharge,
                to_char(timezone('UTC',date_order::timestamp), 'DD/MM/YYYY') date_order,
                warehouse_id
            from pos_order
            where
                warehouse_id in (%(warehouse_ids)s) and
                state in ('paid', 'done', 'invoiced') and
                timezone('UTC',date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
            group by to_char(timezone('UTC',date_order::timestamp), 'DD/MM/YYYY'), warehouse_id
            order by date_order
            ) as pos_order
            join (
                select
                    sum(price_unit*qty) as old,
                    sum(price_unit*qty-price_subtotal_incl) as discount_line,
                    sum(price_subtotal_incl) as total_line,
                    to_char(timezone('UTC',date_order::timestamp), 'DD/MM/YYYY') date_order,
                    warehouse_id
                from pos_order_line
                where order_id in (
                    select id
                    from pos_order
                    where
                        warehouse_id in (%(warehouse_ids)s) and
                        state in ('paid', 'done', 'invoiced') and
                        timezone('UTC',date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
                    )
                group by to_char(timezone('UTC',date_order::timestamp), 'DD/MM/YYYY'), warehouse_id
                order by date_order
            ) as order_line
        on order_line.date_order = pos_order.date_order and order_line.warehouse_id = pos_order.warehouse_id
        join stock_warehouse sw on pos_order.warehouse_id = sw.id
        order by sw.code
        ''' % ({
            'warehouse_ids': ','.join(map(str, [x.id for x in self.warehouse_ids])),
            'date_from': self.date_from,
            'date_to': self.date_to
        })
        self._cr.execute(sql)
        res = []
        num_bill = 0
        total = 0
        total_discount = 0
        total_after_discount = 0
        for i in self._cr.dictfetchall():
            discount_order = i['order_discount']
            discount_line = i['discount_line']
            total_discount = abs(discount_order and discount_order or 0) + \
                abs(discount_line and discount_line or 0)
            total_bill = i['orderline_old_price'] + \
                (i['surcharge'] if i['surcharge'] else 0)
            total_average = total_bill / i['num_bill']
            res.append(
                {
                    'warehouse_name': i['warehouse_name'],
                    'warehouse_code': i['warehouse_code'],
                    'num_bill': i['num_bill'],
                    'total': total_bill,
                    'total_average': total_average,
                    'discount': total_discount,
                    'total_after_discount': i['amount_total'],
                    'date_order': i['date_order']
                })

        return res

    def get_order_by_payment_method_warehouse(self):
        sql = '''
        select
            sw.id warehouse_id,
            sw.name warehouse_name,
            sw.code warehouse_code,
            pos_order.num_bill as num_bill,
            old + coalesce(pos_order.surcharge, 0) as total,
            abs(round(order_line.discount_line, 5)) + abs(pos_order.discount) as discount,
            pos_order.total as total_after_discount
        from (
            select
                count(id) num_bill,
                sum(amount_total) total,
                sum(discount_amount) discount,
                sum(total_surcharge) surcharge,
                warehouse_id
            from pos_order
            where
                warehouse_id in (%(warehouse_ids)s) and
                state in ('paid', 'done', 'invoiced') and
                timezone('UTC',date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
            group by warehouse_id
            ) as pos_order
            join (
                select
                    sum(price_unit*qty) as old,
                    sum(price_unit*qty-price_subtotal_incl) as discount_line,
                    sum(price_subtotal_incl) as total_line,
                    warehouse_id
                from pos_order_line
                where order_id in (
                    select id
                    from pos_order
                    where
                        warehouse_id in (%(warehouse_ids)s) and
                        state in ('paid', 'done', 'invoiced') and
                        timezone('UTC',date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
                    )
                group by warehouse_id
            ) as order_line
        on order_line.warehouse_id = pos_order.warehouse_id
        join stock_warehouse sw on pos_order.warehouse_id = sw.id
        order by sw.code
        ''' % ({
            'warehouse_ids': ','.join(map(str, [x.id for x in self.warehouse_ids])),
            'date_from': self.date_from,
            'date_to': self.date_to
        })
        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        return res

    def get_list_hours(self):
        res = []
        start_hour = '{0:02.0f}:{1:02.0f}'.format(
            *divmod(float(self.start_hour) * 60, 60))
        end_hour = '{0:02.0f}:{1:02.0f}'.format(
            *divmod(float(self.end_hour) * 60, 60))
        for item in range(int(self.start_hour), int(self.end_hour) + 2):
            if item == int(self.start_hour):
                hour = start_hour
            elif item == (int(self.end_hour) + 1):
                hour = end_hour
            else:
                hour = '{0:02.0f}:{1:02.0f}'.format(
                    *divmod(float(item) * 60, 60))
            res.append(
                {
                    'hour': hour,
                })
        return res

    def get_order_by_warehouse_range_time(self):
        res = []
        list_hour = self.get_list_hours()
        from_hours = list_hour[0].get('hour')
        to_hours = list_hour[len(list_hour)-1].get('hour')
        day_from = self.date_from.strftime(
            "%Y-%m-%d") + str(' %s') % (from_hours)
        day_to = self.date_to.strftime("%Y-%m-%d") + str(' %s') % (to_hours)
        sql = '''
        select
            sw.id warehouse_id,
            sw.name warehouse_name,
            sw.code warehouse_code,
            pos_order.num_bill as num_bill,
            pos_order.total as amount_total,
            pos_order.discount as order_discount,
            pos_order.surcharge as surcharge,
            order_line.old as orderline_old_price,
            round(order_line.discount_line, 5) as discount_line,
            pos_order.date_order, concat(pos_order.hour_order,':','00') hour_from, concat(pos_order.hour_order+1,':','00') hour_to
            from (
                select
                    count(id) num_bill,
                    sum(amount_total) total,
                    sum(discount_amount) discount,
                    sum(total_surcharge) surcharge,
                    to_char(timezone('UTC',date_order::timestamp), 'DD/MM/YYYY') date_order,
                    date_part('hour', timezone('UTC',pos_order.date_order::timestamp)) hour_order,
                    warehouse_id
                from pos_order
                where
                    warehouse_id in (%(warehouse_ids)s) and
                    state in ('paid', 'done', 'invoiced') and
                    timezone('UTC',date_order::timestamp) between '%(date_from)s' and '%(date_to)s'
                group by to_char(timezone('UTC',date_order::timestamp), 'DD/MM/YYYY'), warehouse_id, date_part('hour', timezone('UTC',date_order::timestamp))
                order by date_order, date_part('hour', timezone('UTC',date_order::timestamp))
                ) as pos_order
                join (
                    select
                        sum(price_unit*qty) as old,
                        sum(price_unit*qty-price_subtotal_incl) as discount_line,
                        sum(price_subtotal_incl) as total_line,
                        to_char(timezone('UTC',date_order::timestamp), 'DD/MM/YYYY') date_order,
                        date_part('hour', timezone('UTC',date_order::timestamp)) hour_order,
                        warehouse_id
                    from pos_order_line
                    where order_id in (
                        select id
                        from pos_order
                        where
                            warehouse_id in (%(warehouse_ids)s) and
                            state in ('paid', 'done', 'invoiced') and
                            timezone('UTC',date_order::timestamp) between '%(date_from)s' and '%(date_to)s'
                        )
                    group by to_char(timezone('UTC',date_order::timestamp), 'DD/MM/YYYY'), warehouse_id, date_part('hour', timezone('UTC',date_order::timestamp))
                order by date_order, date_part('hour', timezone('UTC',date_order::timestamp))
                ) as order_line
            on order_line.hour_order = pos_order.hour_order and order_line.date_order = pos_order.date_order and order_line.warehouse_id = pos_order.warehouse_id
        join stock_warehouse sw on pos_order.warehouse_id = sw.id
        order by sw.code, pos_order.date_order, pos_order.hour_order
        ''' % ({
            'warehouse_ids': ','.join(map(str, [x.id for x in self.warehouse_ids])),
            'date_from': day_from,
            'date_to': day_to
        })
        self._cr.execute(sql)
        for i in self._cr.dictfetchall():
            discount_order = i['order_discount']
            discount_line = i['discount_line']
            total_discount = abs(discount_order) + abs(discount_line)
            res.append(
                {
                    'num_bill': i['num_bill'],
                    'total': i['orderline_old_price'] + (i['surcharge'] if i['surcharge'] else 0),
                    'discount': total_discount,
                    'total_after_discount': i['amount_total'],
                    'date_order': i['date_order'],
                    'from_hour': i['hour_from'],
                    'to_hour': i['hour_to'],
                    'warehouse_name': i['warehouse_name'],
                    'warehouse_code': i['warehouse_code'],
                })
        return res

    def get_report_pos_discount_total(self):
        total = {}
        name_discounts = []
        for res in self:
            warehouses = res.get_warehouse_selected()
            for store in warehouses:
                warehouse_id = store['warehouse_id']
                discounts = res.get_discount_by_warehouse(warehouse_id)
                for discount in discounts:
                    date_order = datetime.strptime(
                        discount['date_order'], '%d-%m-%Y').strftime('%d%m%Y')
                    name_discount = discount['name_discount']
                    if name_discount in name_discounts:
                        name_discount_index = name_discounts.index(
                            name_discount)
                    else:
                        name_discounts.append(name_discount)
                        name_discount_index = len(name_discounts) - 1
                    check = '%s_%s_%s' % (
                        date_order, warehouse_id, name_discount_index)
                    if total.get(check, False):
                        total[check]['qty_pos'] += discount['qty_pos']
                        total[check]['total_discount'] += discount['total_discount']
                    else:
                        total[check] = {
                            'date_order': discount['date_order'],
                            'warehouse_name': discount['warehouse_name'],
                            'name_discount': name_discount,
                            'qty_pos': discount['qty_pos'],
                            'total_discount': discount['total_discount'],
                        }
        return [total[key] for key in total]

    def get_report_pos_discount_detail(self):
        detail = {}
        name_discounts = []
        name_bills = []
        for res in self:
            warehouses = res.get_warehouse_selected()
            for store in warehouses:
                warehouse_id = store['warehouse_id']
                discounts = res.get_detail_discount_by_warehouse(warehouse_id)
                for discount in discounts:
                    name_discount = discount['name_discount']
                    name_bill = discount['name_bill']
                    if name_discount in name_discounts:
                        name_discount_index = name_discounts.index(
                            name_discount)
                    else:
                        name_discounts.append(name_discount)
                        name_discount_index = len(name_discounts) - 1
                    if name_bill in name_bills:
                        name_bill_index = name_bills.index(
                            name_bill)
                    else:
                        name_bills.append(name_bill)
                        name_bill_index = len(name_bills) - 1
                    check = '%s_%s' % (name_discount_index, name_bill_index)
                    if detail.get(check, False):
                        detail[check]['pol_discount_amount'] += discount['pol_discount_amount']
                        detail[check]['discount_price'] += discount['discount_price']
                    else:
                        detail[check] = {
                            'date_order': discount['date_order'],
                            'warehouse_name': discount['warehouse_name'],
                            'name_discount': name_discount,
                            'name_bill': discount['name_bill'],
                            'type_discount': discount['type_discount'],
                            'pol_discount': discount['pol_discount'],
                            'pol_discount_amount': discount['pol_discount_amount'],
                            'discount_loyalty': discount['discount_loyalty'],
                            'discount_price': discount['discount_price'],
                            'cashier_name': discount['cashier_name'],
                        }
        return [detail[key] for key in detail]


class report_pos_payment_method(models.AbstractModel):
    _name = 'report.phuclong_pos_theme.report_pos_payment_method'
    _inherit = 'report.odoo_report_xlsx.abstract'

    # Định dạng page
    def page_setup(self, sheet):
        sheet.set_landscape()
        sheet.set_paper(9)
        sheet.center_horizontally()
        sheet.set_row(0, 45.6)
        sheet.set_row(4, 45.6)

    # Định dạng format
    def make_format(self, workbook):
        header_title = workbook.add_format({'font_size': 22,
                                            'bold': True,
                                            # 'fg_color': '#D3D3D3',
                                            })
        header_title.set_align('center')
        #         header_title.set_align('bottom')
        header_title.set_font_name('Arial')
        line_italic = workbook.add_format({'font_size': 12,
                                           #    'italic': True,
                                           'bold': True,
                                           })
        line_italic.set_font_name('Arial')
        line_italic.set_align('center')
        line_left = workbook.add_format({'font_size': 12,
                                         'bold': True,
                                         })
        line_left.set_font_name('Arial')
        line_left.set_align('left')

        line_normal = workbook.add_format({'font_size': 12,
                                           })
        line_normal.set_font_name('Arial')
        line_normal.set_align('left')
        # line_italic.set_align('vcenter')
        table_bold = workbook.add_format({'font_size': 15,
                                          'align': 'vcenter',
                                          'bold': True,
                                          'fg_color': '#D3D3D3',
                                          })
        table_bold.set_border()
        table_bold.set_font_name('Arial')
        table_bold.set_text_wrap()
        table_bold.set_align('center')
        table_content = workbook.add_format(
            {'font_size': 13, 'align': 'vcenter', })
        table_content.set_font_name('Arial')
        table_content.set_border()
        # table_content.set_text_wrap()
        table_content.set_align('center')

        table_content_left = workbook.add_format(
            {'font_size': 13, 'align': 'vcenter', })
        table_content_left.set_font_name('Arial')
        table_content_left.set_border()
        table_content_left.set_align('left')

        table_number = workbook.add_format({'font_size': 13,
                                            'align': 'vright', })
        table_number.set_font_name('Arial')
        table_number.set_border()
        table_number.set_align('right')
        table_number.set_num_format('#,##0')

        table_number_int = workbook.add_format({'font_size': 13,
                                                'align': 'vright', })
        table_number_int.set_font_name('Arial')
        table_number_int.set_border()
        table_number_int.set_align('right')

        FORMAT.update({'header_title': header_title,
                       'line_italic': line_italic,
                       'line_left': line_left,
                       'line_normal': line_normal,
                       'table_bold': table_bold,
                       'table_content': table_content,
                       'table_content_left': table_content_left,
                       'table_number': table_number,
                       'table_number_int': table_number_int
                       })

    def generate_header(self, sheet, rcs):
        sheet.merge_range('A1:H1', 'BẢNG BÁO CÁO DOANH THU BÁN HÀNG THEO PHƯƠNG THỨC THANH TOÁN',
                          FORMAT.get('header_title'))
        sheet.merge_range('A2:H2', 'Ngày in: ' +
                          rcs.get_current_datetime(), FORMAT.get('line_italic'))
        sheet.write_rich_string(1, 0, 'Ngày in: ', FORMAT.get(
            'line_normal'), rcs.get_current_datetime(), FORMAT.get('line_italic'))
        sheet.write_rich_string(2, 3, 'Từ ngày: ', FORMAT.get(
            'line_normal'), rcs.get_date_start_string(), FORMAT.get('line_left'))
        sheet.write_rich_string(2, 4, 'Đến ngày: ', FORMAT.get(
            'line_normal'), rcs.get_date_end_string(), FORMAT.get('line_left'))
        return 3

    def general_data(self, sheet, rcs, rowpos):
        sheet.write(rowpos, 0, 'STT', FORMAT.get('table_bold'))
        sheet.write(rowpos, 1, 'Mã cửa hàng', FORMAT.get('table_bold'))
        sheet.write(rowpos, 2, 'Tên cửa hàng', FORMAT.get('table_bold'))
        sheet.write(rowpos, 3, 'Số lượng bill ', FORMAT.get('table_bold'))
        sheet.write(rowpos, 4, 'Tổng doanh thu', FORMAT.get('table_bold'))
        sheet.write(rowpos, 5, 'Giảm giá', FORMAT.get('table_bold'))
        sheet.write(rowpos, 6, 'Doanh thu sau giảm giá',
                    FORMAT.get('table_bold'))

        for r in range(7):
            sheet.set_column(rowpos, r, 25)
        sheet.set_column('A:A', 8)
        col = 7
        method_ids = []
        methods = rcs.get_payment_method()
        if not len(methods):
            return
        for method in methods:
            method_ids.append(method['payment_method_id'])
            sheet.write(
                rowpos, col, method['method_name'], FORMAT.get('table_bold'))
            sheet.set_column(rowpos, col, 25)
            col += 1
        sheet.set_column(rowpos, col, 25)
        rowpos += 1
        warehouses = rcs.get_warehouse_selected()
        i = 0
        payment_list = rcs.get_payment_by_method(method_ids)
        for warehouse in rcs.get_order_by_payment_method_warehouse():
            i += 1
            sheet.write(rowpos, 0, i, FORMAT.get('table_number_int'))
            sheet.write(rowpos, 1, warehouse['warehouse_code'], FORMAT.get(
                'table_content_left'))
            sheet.write(rowpos, 2, warehouse['warehouse_name'], FORMAT.get(
                'table_content_left'))
            sheet.write(rowpos, 3, warehouse['num_bill']
                        or '', FORMAT.get('table_number_int'))
            sheet.write(rowpos, 4, warehouse['total']
                        or '', FORMAT.get('table_number'))
            sheet.write(rowpos, 5, warehouse['discount']
                        or '', FORMAT.get('table_number'))
            sheet.write(
                rowpos, 6, warehouse['total_after_discount'] or '', FORMAT.get('table_number'))

            col_ware = 7
            for method in methods:
                amount_total = 0
                payment = list(filter(lambda p: p['warehouse_id'] == warehouse['warehouse_id']
                                      and p['payment_method_id'] == method['payment_method_id']
                                      and p['currency_name'] == method['currency_name'],
                                      payment_list))
                if(len(payment)):
                    amount_total = payment[0]['amount']
                sheet.write(rowpos, col_ware, amount_total or '',
                            FORMAT.get('table_number'))
                col_ware += 1
            rowpos += 1

    def generate_xlsx_report(self, workbook, data, orders):
        self.make_format(workbook)
        for rcs in orders:
            sheet = workbook.add_worksheet('sheet1')
            self.page_setup(sheet)
            rowpos = self.generate_header(sheet, rcs)
            rowpos = self.general_data(sheet, rcs, rowpos + 1)


class ReportPosCancelWizard(models.TransientModel):
    _name = "wizard.report.pos.cancel"

    warehouse_ids = fields.Many2many(
        'stock.warehouse',
        'pos_cancel_report_warehouse_rel',
        'wizard_id', 'warehouse_id',
        string='Stores')
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')

    def get_current_datetime(self):
        date = time.strftime(DATETIME_FORMAT)
        date = self.env['res.users']._convert_user_datetime(date)
        return date.strftime('%d/%m/%Y %H:%M:%S')

    def get_date_start(self):
        from_date_str_fm = self.date_from.strftime("%d/%m/%Y") + ' 00:00:00'
        return from_date_str_fm

    def get_date_end(self):
        to_date_str_fm = self.date_to.strftime("%d/%m/%Y") + ' 23:59:59'
        return to_date_str_fm

    def export_report(self):
        return self.env.ref(
            'phuclong_pos_theme.report_pos_cancel').report_action(self)

    def get_order_cancel_group_by_store(self):
        sql = '''
        SELECT
            res.warehouse_id,
            sw.name warehouse_name,
            sw.code warehouse_code,
            to_char(timezone(
                'UTC',pos.date_order::timestamp), 'DD/MM/YYYY') AS date_order,
            pp.category_lv1,
            sum(res.price_total)/1.1*0.1 price_tax,
            sum(price_total) as price_total,
            (SUM(res.amount_surcharge)) as amount_surcharge,
            (sum(res.price_sub_total) + SUM(
                COALESCE(res.amount_surcharge, 0))) as price_sub_total,
            sum(res.total_discount) as total_discount,
            sum(res.price_total) as price_total
        FROM report_pos_order res
            LEFT JOIN product_product pp ON pp.id = res.product_id
            LEFT JOIN pos_order pos ON pos.id = res.order_id
            LEFT JOIN pos_order_line pos_l ON pos_l.id = res.id
            JOIN stock_warehouse sw ON res.warehouse_id = sw.id
        WHERE res.warehouse_id IN (%(warehouse_ids)s)
            AND timezone('UTC', res.date::timestamp)
                BETWEEN '%(date_from)s 00:00:00' AND '%(date_to)s 23:59:59'
            AND res.state = 'cancel'
        GROUP BY res.warehouse_id,
            sw.name, sw.code,
            pp.category_lv1,
            to_char(timezone('UTC',pos.date_order::timestamp), 'DD/MM/YYYY'),
            timezone('UTC',pos.date_order::timestamp)::date
        ORDER BY timezone('UTC',pos.date_order::timestamp)::date
        ''' % ({
            'warehouse_ids': ' ,'.join(
                map(str, [x.id for x in self.warehouse_ids])),
            'date_from': self.date_from,
            'date_to': self.date_to,
        })
        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        return res

    def get_order_product_by_warehouse(
            self, warehouse_id,
            date_order=False, category=False):
        if date_order:
            date_order = datetime.strptime(date_order, "%d/%m/%Y").date()
        select = ''
        group_by = ''
        left_join = ''
        where_category = ''
        select = """
        pos_l.id as pos_l,
        sum(res.price_total)/1.1*0.1 price_tax,
        pos.name as pos_name,
        pos.cancel_reason,
        to_char(timezone(
            'UTC',pos.date_order::timestamp),
            'DD/MM/YYYY HH24:MI:SS') as date_order,
        partner.name as partner_name,
        case when pt.fnb_type = 'drink' then concat(option_material.option_name , case when option_material.option_name != '' then ', ' end, 
            case when pos_l.cup_type is not null then (case when pos_l.cup_type != (select pcl.cup_type from product_cup_line pcl join product_cup_default pcd on pcl.cup_default_id = pcd.id 
            join product_template pt on pcd.product_id = pt.id join product_product pp on pp.product_tmpl_id = pt.id 
            join pos_order_line pol on pol.product_id = pp.id where pol.id = pos_l.id and pcd.sale_type_id = pos.sale_type_id order by pcl.sequence limit 1) then 
            (case when pos_l.cup_type = 'paper' then 'Ly giấy' when pos_l.cup_type = 'plastic' then 'Ly nhựa' when pos_l.cup_type = 'themos' then 'Ly giữ nhiệt' end) else '' end)
        else 'Không lấy Ly' end) else '' end as options,"""
        group_by = """ ,pos_l.id ,pos.name, pos.cancel_reason, pos.date_order, pos.sale_type_id, pt.fnb_type,
            partner.name, option_material.option_name
            order by pos.date_order, pos.name """
        left_join = '''
            left join pos_order pos on pos.id = res.order_id
            left join pos_order_line pos_l on pos_l.id = res.id
            left join res_partner partner on partner.id = res.partner_id
            left join (select foo.id line_id, string_agg(concat(case when option_type = 'over' then 'Nhiều ' 
                when option_type = 'below' then 'Ít ' when option_type = 'normal' then '' else 'Không ' end, 
                foo.name, case when option_type = 'normal' then ' bình thường' else '' end) , ', ') option_name
                from (select pol.id, pm.id material_id, pm.name from pos_order_line pol join product_product pp 
                on pol.product_id = pp.id join product_template pt on pp.product_tmpl_id = pt.id
                join product_material pm on pm.product_custom_id = pt.id
                where pol.warehouse_id = %(warehouse_id)s and timezone('UTC', pol.date_order::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59') as foo
                left join pos_order_line_option polo on foo.material_id = polo.option_id and foo.id = polo.line_id
                group by foo.id) option_material
            on pos_l.id = option_material.line_id
        ''' % ({
            'warehouse_id': warehouse_id,
            'date_from': date_order,
            'date_to': date_order,
        })
        where = 'AND pos.cancel_from_be = TRUE'
        where_category = '''AND pp.category_lv1 = '%s' ''' % (category)

        sql = '''
        select
            %(select)s
            res.product_id,
            res.warehouse_id,
            uom.id as uom_id, uom.name as uom_name,
            pp.default_code,
            pt.ref_code,
            pp.category_lv1,
            categ.name as categ_name, pt.name as product_name,
            sum(res.product_qty) as qty,
            sum(price_total) as price_total,
            (SUM(res.amount_surcharge)) as amount_surcharge,
            (sum(res.price_sub_total) + SUM(COALESCE(res.amount_surcharge, 0))) as price_sub_total,
            sum(res.total_discount) as total_discount,
            sum(res.price_total) as price_total
        from report_pos_order res
        left join product_product pp on pp.id = res.product_id
        left join product_template pt on pt.id = pp.product_tmpl_id
        left join product_category categ on categ.id = pt.categ_id
        left join uom_uom uom on uom.id = pt.uom_id
        %(left_join)s
        where res.warehouse_id = %(warehouse_id)s and timezone('UTC', res.date::timestamp) between '%(date_from)s 00:00:00' and '%(date_to)s 23:59:59'
        %(where_category)s
        %(where)s
        and res.state = 'cancel'
        group by res.product_id,
            res.warehouse_id,
            uom.name, uom.id,
            pp.category_lv1,
            pp.default_code, pt.ref_code,
            categ.name, pp.display_name,pt.name
            %(group_by)s
        ''' % ({
            'warehouse_id': warehouse_id,
            'date_from': date_order,
            'date_to': date_order,
            'select': select,
            'group_by': group_by,
            'left_join': left_join,
            'where_category': where_category,
            'where': where
        })
        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        return res

    def get_price_order_line(self, pos_line):
        pos = self.env['pos.order.line'].sudo().search_read([
            ('id', '=', pos_line)], ['price_unit'])
        return pos and pos[0]['price_unit'] or 0

    def get_order_line(self, pos_line):
        pos = self.env['pos.order.line'].sudo().search([
            ('id', '=', pos_line)], limit=1)
        return pos

    def get_cancel_reason(self, order_line_id, cancel_reason):
        if cancel_reason:
            order_line = self.env['pos.order.line'].browse(order_line_id)
            if order_line_id == order_line.order_id.lines[0].id:
                return cancel_reason
        return ''

    def get_str_datetime(self, datetime):
        date = self.env['res.users']._convert_user_datetime(datetime)
        return date.strftime('%d/%m/%Y %H:%M:%S')
