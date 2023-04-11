# -*- coding: utf-8 -*-
from odoo import fields, models, api
from datetime import datetime, date
DATETIME_fm = "%Y-%m-%d %H:%M:%S"
from odoo.exceptions import UserError, ValidationError



class POSBanner(models.Model):
    _name = "pos.banner.config"

    name = fields.Char('Banner Name')
    warehouse_ids = fields.Many2many(
        'stock.warehouse',
        'banner_warehouse_rel',
        'banner_id', 'warehouse_id',
        string='Stores')
    start_date = fields.Datetime(string='Start Date', required=True)
    end_date = fields.Datetime(string='End Date', required=True)
    logo = fields.Binary('Receipt Logo', copy=False)
    # state = fields.Selection([
    #     ('invalid', 'Invalid'),
    #     ('valid', 'Valid')
    #     ], string='State', default='valid')
    active = fields.Boolean('Active', default=True)

    @api.constrains('start_date', 'end_date')
    def _check_date(self):
        if self.start_date > self.end_date:
            raise UserError('End date must be after Start date!')
