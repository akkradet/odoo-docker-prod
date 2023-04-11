# -*- coding: utf-8 -*-
import time
from datetime import datetime, timedelta

from odoo import api, models, tools, fields, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"


class WizardStockBalanceProduct(models.TransientModel):
    _name = "wizard.stock.balance.product"

    date_from = fields.Date(
        string="From Date",
        default=fields.Datetime.now)
    date_to = fields.Date(
        string="To Date",
        default=fields.Datetime.now)
    product_tmpl_id = fields.Many2one(
        'product.template',
        string="Product")

    @api.constrains('date_from', 'date_to')
    def _check_date(self):
        if self.date_to < self.date_from:
            raise UserError(_('From Date must be before To Date'))

    def action_report_print(self):
        return self.env.ref(
            'phuclong_stock.report_stock_balance_product').report_action(self)

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

    def get_product(self):
        sql = """
            SELECT sw.code AS warehouse_code,
                sw.name AS warehouse_name,
                pu.name uom_name,
                --- Opening Onhand ---
                SUM(foo.start_in_qty - foo.start_out_qty) opening_qty,
                --- Incoming ---
                SUM(foo.in_qty) in_qty,
                --- Outgoing ---
                SUM(foo.out_qty) out_qty,
                ---Closing Onhand---
                SUM(foo.start_in_qty - foo.start_out_qty
                    + foo.in_qty - foo.out_qty) closing_qty,
                pp.id product_id
            FROM product_product pp
                JOIN (
                    -- Đầu Kỳ IN --
                    SELECT sml.product_id,
                        stm.warehouse_id AS warehouse_id,
                        ---Opening---
                        0 start_out_qty,
                        SUM(sml.product_qty_done) start_in_qty,
                        ---Incoming---
                        0 in_qty,
                        --- Outgoing ---
                        0 out_qty
                    FROM stock_move_line sml
                        JOIN stock_move stm ON stm.id = sml.move_id
                        JOIN stock_location sl ON sl.id = sml.location_dest_id
                    WHERE sml.state = 'done'
                        AND sl.usage = 'internal'
                        AND DATE(timezone(
                            'UTC',stm.date::timestamp)) < '%(start_date)s'
                    GROUP BY sml.product_id, stm.warehouse_id

                    UNION ALL

                    -- Đầu Kỳ OUT --
                    SELECT sml.product_id,
                        stm.warehouse_id AS warehouse_id,
                        ---Opening---
                        SUM(sml.product_qty_done) start_out_qty,
                        0 start_in_qty,
                        ---Incoming---
                        0 in_qty,
                        --- Outgoing ---
                        0 out_qty
                    FROM stock_move_line sml
                        JOIN stock_move stm ON stm.id = sml.move_id
                        JOIN stock_location sl ON sl.id = sml.location_id
                    WHERE sml.state = 'done'
                        AND sl.usage = 'internal'
                        AND DATE(timezone(
                            'UTC',stm.date::timestamp)) < '%(start_date)s'
                    GROUP BY sml.product_id, stm.warehouse_id

                    UNION ALL

                    -- Trong kỳ IN --
                    SELECT sml.product_id,
                        stm.warehouse_id AS warehouse_id,
                        ---Opening---
                        0 start_out_qty,
                        0 start_in_qty,
                        ---Incoming---
                        SUM(sml.product_qty_done) in_qty,
                        ---- Outgoing ----
                        0 out_qty
                    FROM stock_move_line sml
                        JOIN stock_move stm ON stm.id = sml.move_id
                        JOIN stock_location sl ON sl.id = sml.location_dest_id
                    WHERE sml.state IN ('done')
                        AND sl.usage = 'internal'
                        AND date(timezone('UTC',stm.date::timestamp))
                            BETWEEN '%(start_date)s' AND '%(end_date)s'
                    GROUP BY sml.product_id, stm.warehouse_id

                        UNION ALL

                    -- Trong kỳ OUT--
                    SELECT sml.product_id,
                        stm.warehouse_id AS warehouse_id,
                        ---Opening---
                        0 start_out_qty,
                        0 start_in_qty,
                        ---Incoming---
                        0 in_qty,
                        ---- Outgoing ----
                        SUM(sml.product_qty_done) out_qty
                    FROM stock_move_line sml
                        JOIN stock_move stm ON stm.id = sml.move_id
                        JOIN stock_location sl ON sl.id = sml.location_id
                    WHERE sml.state = 'done'
                        AND sl.usage = 'internal'
                        AND date(timezone('UTC',stm.date::timestamp))
                            BETWEEN '%(start_date)s' AND '%(end_date)s'
                    GROUP BY sml.product_id, stm.warehouse_id
                    ) foo ON pp.id = foo.product_id
                JOIN product_template pt on pp.product_tmpl_id = pt.id
                JOIN uom_uom pu on pt.uom_id = pu.id
                JOIN stock_warehouse sw ON foo.warehouse_id = sw.id
            WHERE pt.id = %(product_tmpl_id)s
            GROUP BY sw.id,
                pu.id,
                pp.id
            ORDER BY sw.name
        """ % ({
            'start_date': self.date_from,
            'end_date': self.date_to,
            'product_tmpl_id': self.product_tmpl_id.id})
        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        return res
