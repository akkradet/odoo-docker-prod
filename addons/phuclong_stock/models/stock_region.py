# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockRegion(models.Model):
    _name = 'stock.region'
    _description = 'Stock Region'
    _order = 'id desc'
    
    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Region code", required=True)
    description = fields.Text(string="Description")
    # -------------------------------------------------------------------------
    # CONSTRAINS METHODS
    # -------------------------------------------------------------------------
    # _sql_constraints, @api.constrains
    _sql_constraints = [
        ('stock_region_code_uniq', 'unique (code)', _("A stock region with the same code already exists.")),
    ]
    
    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            # THANH: filter bank account
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        res = self.search(domain + args, limit=limit)
        return res.name_get()
    

