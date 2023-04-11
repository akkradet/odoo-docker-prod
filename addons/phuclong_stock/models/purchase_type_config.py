# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class PurchaseTypeConfig(models.Model):
    _inherit = "purchase.type.config"

    is_used_for_orderpoint = fields.Boolean(
        string='Used for PO created from reordering rules',
        default=False
    )

    @api.constrains('is_used_for_orderpoint')
    def _check_used_for_orderpoint(self):
        for rcs in self:
            if rcs.is_used_for_orderpoint:
                rcs_id = self.env['purchase.type.config'].search([('id', '!=', rcs.id),
                                                                  ('is_used_for_orderpoint', '=', True),
                                                                  ])
                if rcs_id and self.is_used_for_orderpoint:
                    raise UserError(_("You can only have one purchase type used for reordering rules at any point in time."))
