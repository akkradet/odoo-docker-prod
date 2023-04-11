# -*- coding: utf-8 -*-
from collections import Counter
from odoo.tools import pycompat
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round, float_compare, float_is_zero


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

#     state = fields.Selection(related='move_id.state', store=True, related_sudo=False, index=True, copy=False)
    move_id = fields.Many2one('stock.move', 'Stock Move', help="Change to a better name",
                              ondelete='cascade', index=True, copy=False)

    def _action_reopen_done(self):
        ml_to_delete = self.env['stock.move.line']
        Quant = self.env['stock.quant']
        # THANH 31/07/2020 - allow user Administrator actions like SUPERUSER_ID
        admin_uid = self.env.ref('base.user_admin').id
        for ml in self.filtered(lambda l: l.product_id.product_tmpl_id.type == 'product'):
            if not ml.location_dest_id.should_bypass_reservation():
                if not self._context.get('move_origin'):
                    forecast_quantity = Quant.with_context(tracking=ml.lots_visible)._get_available_quantity(ml.product_id, ml.location_dest_id,
                                                                                                             lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id if ml.location_dest_id.consignment_location else None, strict=True)
                    if (forecast_quantity - ml.product_qty_done) < 0:
                        if self.env.user.id not in (SUPERUSER_ID, admin_uid) and not self.env.user.has_group('phuclong_stock.group_reopen_inventory_adjustment'):
                            raise UserError(_(
                                'You cannot reopen operation of product %s on location destination %s. It will affect inventory.') % (
                                ml.product_id.display_name, ml.location_dest_id.name))

                Quant.with_context(reopen_done=True)._update_available_quantity(ml.product_id, ml.location_dest_id, -ml.product_qty_done,
                                                                                lot_id=ml.lot_id, package_id=ml.result_package_id, owner_id=ml.owner_id,
                                                                                move_line_id=ml, quant_ids=ml.quant_ids)

            if not ml.location_id.should_bypass_reservation():
                Quant.with_context(reopen_done=True)._update_available_quantity(ml.product_id, ml.location_id, ml.product_qty_done,
                                                                                lot_id=ml.lot_id, package_id=ml.result_package_id, owner_id=ml.owner_id,
                                                                                move_line_id=ml, quant_ids=ml.quant_ids)
            ml_to_delete |= ml
        return ml_to_delete
