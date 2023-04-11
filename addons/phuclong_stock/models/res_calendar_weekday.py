# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResCalendarWeekday(models.Model):
    _name = 'res.calendar.weekday'
    _description = 'Calendar Weekday'
    _order = 'sequence asc'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    sequence = fields.Integer('Weekday number')
    name = fields.Char('Full weekday name', translate=True)
    abbr_name = fields.Char('Abbreviated weekday name', translate=True)
