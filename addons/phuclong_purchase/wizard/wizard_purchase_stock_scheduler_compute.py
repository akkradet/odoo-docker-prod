# -*- coding: utf-8 -*-

from odoo import api, models, tools, fields
import logging
import threading
from datetime import datetime

_logger = logging.getLogger(__name__)


class WizardPurchaseStockSchedulerCompute(models.TransientModel):
    _name = 'wizard.purchase.stock.scheduler.compute'
    _description = 'Purchase Confirm Stock Scheduler'

    purchase_id = fields.Many2one('purchase.order', string='Purchase')
    is_warning = fields.Boolean(string='The Warning', help="The Warning is manager and user")
    #orderpoint_id = fields.Many2one('stock.warehouse.orderpoint', 'Orderpoint')

    def action_purchase_confirm(self):
        if self.purchase_id:
            return self.purchase_id.button_confirm()
