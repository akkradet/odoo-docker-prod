# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResCalendarDaymonth(models.Model):
    _name = 'res.calendar.daymonth'
    _description = 'Calendar Daymonth'
    _order = 'day_of_month asc'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    day_of_month = fields.Integer('Day of the month')
#     orderpoint_ids = fields.Many2many('stock.warehouse.orderpoint',
#                                       'res_calendar_daymonth_orderpoint_rel',
#                                       'daymonth_id', 'orderpoint_id', string='Reordering Rule')

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------
    def name_get(self):
        res = []
        for rcs in self:
            name = str(rcs.day_of_month) or ''
            res.append((rcs.id, name))
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            # THANH: filter bank account
            domain = [('day_of_month', operator, name)]
        res = self.search(domain + args, limit=limit)
        return res.name_get()

