# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from lxml import etree
import json
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    vendor_document = fields.Char()
    date_done = fields.Datetime(inverse='_inverse_date_done')

    def _inverse_date_done(self):
        for pick in self:
            if pick.purchase_id:
                pick.purchase_id.picking_date_done = pick.date_done
