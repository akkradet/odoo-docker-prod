# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError
from lxml import etree
import base64, xlrd
class WizardCancelPosOrderReason(models.TransientModel):
    _name = "wizard.cancel.pos.order.reason"
    _description = 'WizardCancelPosOrderReason'

    cancel_reason = fields.Text(required=True)
    
    def apply_cancel_reason(self):
        active_id = self._context.get('active_id')
        order = self.env['pos.order'].browse(active_id)
        order.write({'cancel_reason':self.cancel_reason})
        order.with_context(cancel_from_wizard=True).cancel_order()
        

