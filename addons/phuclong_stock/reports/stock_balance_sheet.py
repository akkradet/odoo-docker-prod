# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class StockBalanceSheet(models.TransientModel):
    _inherit = "stock.balance.sheet"

    @api.model
    def default_get(self, fields):
        res = super(StockBalanceSheet, self).default_get(fields)
        if len(self.env.user.company_analytic_account_ids):
            user_id = self.env.user
            account_analytic_ids = user_id.company_analytic_account_ids.ids
            res['company_account_analytic_ids'] = [
                (6, 0, account_analytic_ids)]
        return res

    def get_ref_code(self, product_id):
        ref_code = ''
        if product_id:
            product_tmpl_id = self.env[
                'product.product'].browse(product_id).product_tmpl_id
            if product_tmpl_id and product_tmpl_id.ref_code:
                ref_code = product_tmpl_id.ref_code
        return ref_code

    def _stock_balance_sheet(self, start_date, end_date):
        super(StockBalanceSheet, self)._stock_balance_sheet(start_date, end_date)
        self.env.cr.execute('''
            UPDATE stock_balance_sheet_line set opening_qty = round(opening_qty, 6),
            in_qty = round(in_qty, 6), out_qty = round(out_qty, 6), closing_qty = round(closing_qty, 6)
            WHERE report_id = %(report_id)s
        ''' % ({'report_id': self.id}))