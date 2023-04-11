# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockOverProcessedTransfer(models.TransientModel):
    _inherit = 'stock.overprocessed.transfer'

    def _compute_overprocessed_product_name(self):
        for wizard in self:
            if wizard.picking_id:
                moves = wizard.picking_id._get_overprocessed_stock_moves()
                wizard.overprocessed_product_name = _('You have processed different from what was initially planned for the product(s) %s.') % ", ".join([
                    display_name for display_name in moves.mapped('product_id.display_name')])
            else:
                wizard.overprocessed_product_name = ''

    def action_confirm(self):
        self.ensure_one()
        if self.picking_id:
            action = self.picking_id.with_context(
                skip_overprocessed_check=True).button_validate()
            if action['res_model'] == 'stock.backorder.confirmation':
                wiz = self.env['stock.backorder.confirmation'].browse(
                    action['res_id'])
                wiz.write({
                    'date_done': self.date_done,
                    'responsible': self.responsible
                })
                if action['context'].get('internal_invisible', False):
                    return wiz.process_cancel_backorder()
                else:
                    return action
            if action['res_model'] == 'stock.immediate.transfer':
                wiz = self.env['stock.immediate.transfer'].browse(
                    action['res_id'])
                wiz.write({
                    'date_done': self.date_done,
                    'responsible': self.responsible
                })
                return wiz.with_context(action['context']).process()
            return action
