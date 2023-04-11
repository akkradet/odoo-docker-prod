# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    is_reordered_po = fields.Boolean(
        string='Is Reordered PO',
        readonly=True,
        default=False
    )
