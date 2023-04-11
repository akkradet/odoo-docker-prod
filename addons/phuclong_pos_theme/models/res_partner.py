# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import fields, models, api
from odoo.tools.translate import _
from odoo import SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    loyalty_level_id = fields.Many2one('loyalty.level', compute='_compute_loyalty_level', string='Loyalty Level',
                                       readonly=True, store=True)