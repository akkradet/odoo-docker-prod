# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.safe_eval import safe_eval


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    region_stock_id = fields.Many2one(
        'stock.region', string='Region', required=True)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', '|', ('name', operator, name), ('code', operator, name), ('account_analytic_id.code', operator, name)]
        warehouses = self.search(domain + args, limit=limit)
        return warehouses.name_get()

    @api.model
    def create(self, values):
        # Add code here
        warehouse_id = super(StockWarehouse, self).create(values)
        if warehouse_id:
            global_rules = warehouse_id._get_global_route_rules_values()
            depends = [depend for depends in [value.get(
                'depends', []) for value in global_rules.values()] for depend in depends]
            if any(rule in values for rule in global_rules) or\
                    any(depend in values for depend in depends):
                warehouse_id._create_or_update_global_routes_rules()
            if warehouse_id.company_account_analytic_id:
                user_ids = self.env['res.users'].sudo().search([('company_analytic_account_ids', '=',
                                                                 warehouse_id.company_account_analytic_id.id), ('working_all_warehouse', '=', True)])
                for user in user_ids:
                    warehouses = []
                    if user.warehouses_dom:
                        warehouses = safe_eval(user.warehouses_dom)
                    warehouses.append(warehouse_id.id)
                    domain = "[%s]" % (
                        ','.join(map(str, [i for i in warehouses])))
                    user.sudo().warehouses_dom = domain
        return warehouse_id
