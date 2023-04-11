# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class dateOfWeek(models.Model):
    _name = 'day.of.week.config'

    name = fields.Char('Name', required=True)
    value = fields.Char('Name', required=True)