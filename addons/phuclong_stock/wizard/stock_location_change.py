# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class StockLocationChange(models.TransientModel):
    _name = "stock.location.change"
    _description = 'Stock Location Change'

    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    location_id = fields.Many2one('stock.location', string="Location")
    picking_id = fields.Many2one('stock.picking', string="Picking")
    pick_loc_id = fields.Many2one('stock.location', string="Pick Location")

    def confirm_change(self):
        value = {}
        if self.picking_id:
            if self.picking_id.location_id.usage == 'internal':
                value.update({'location_id': self.location_id.id})
            elif self.picking_id.location_dest_id and self.picking_id.location_dest_id.usage == 'internal':
                value.update({'location_dest_id': self.location_id.id})
            self.picking_id.write(value)
            self.picking_id.mapped('move_lines').write(value)
            if self.picking_id.picking_type_id and self.picking_id.picking_type_id.code == 'internal' and self.picking_id.picking_type_id.operation in ['transit_in', 'transit_out']:
                self.picking_id.action_assign()
        return True
