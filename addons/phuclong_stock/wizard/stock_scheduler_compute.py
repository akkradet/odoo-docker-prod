# -*- coding: utf-8 -*-

from odoo import api, models, tools, fields
import logging
import threading
from datetime import datetime

_logger = logging.getLogger(__name__)


class StockSchedulerCompute(models.TransientModel):
    _inherit = 'stock.scheduler.compute'
    _description = 'Run Scheduler Manually'

#     company_id = fields.Many2one('res.company', string='Company',
#                                  default=lambda self: self.env.user.company_id, required=True)
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouse')

    def action_procurement_request(self):
        "Run ALL Scheduler Điều chỉnh route_ids fix cứng theo id"
        context = self._context and self._context.copy() or {}
        buy_route_id = self.env['ir.model.data'].get_object_reference('purchase_stock', 'route_warehouse0_buy')[1]
        current_today = self.env['res.users']._convert_user_datetime(datetime.today())
        context.update({'buy_phuclong': True,
                        'route_ids': buy_route_id,
                        'current_today': current_today
                        })
        threaded_calculation = threading.Thread(target=self.with_context(context)._procure_calculation_orderpoint, args=())
        threaded_calculation.start()
        return {'type': 'ir.actions.act_window_close'}

    def action_procurement_request_manually(self):
        "Run ALL Scheduler Manually"
        context = self._context and self._context.copy() or {}
        buy_route_id = self.env['ir.model.data'].get_object_reference('purchase_stock', 'route_warehouse0_buy')[1]
        current_today = self.env['res.users']._convert_user_datetime(datetime.today())
        context.update({'buy_phuclong': True,
                        'route_ids': buy_route_id,
                        'current_today': current_today,
                        'is_manually': True
                        })
        threaded_calculation = threading.Thread(target=self.with_context(context)._procure_calculation_orderpoint, args=())
        threaded_calculation.start()
        return {'type': 'ir.actions.act_window_close'}
