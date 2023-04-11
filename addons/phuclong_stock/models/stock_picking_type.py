# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    def get_action_picking_tree_waiting(self):
        action = super(StockPickingType,
                       self).get_action_picking_tree_waiting()
        context = action['context'] or {}
        context.update({'create': self.allow_to_create_dashboard})
        action['context'] = context
        return action

    def get_action_picking_tree_late(self):
        action = super(StockPickingType,
                       self).get_action_picking_tree_late()
        context = action['context'] or {}
        context.update({'create': self.allow_to_create_dashboard})
        action['context'] = context
        return action

    def get_action_picking_tree_backorder(self):
        action = super(StockPickingType,
                       self).get_action_picking_tree_backorder()
        context = action['context'] or {}
        context.update({'create': self.allow_to_create_dashboard})
        action['context'] = context
        return action

    def get_action_picking_tree_ready(self):
        action = super(StockPickingType,
                       self).get_action_picking_tree_ready()
        context = action['context'] or {}
        context.update({'create': self.allow_to_create_dashboard})
        action['context'] = context
        return action

    def get_stock_picking_action_picking_type(self):
        action = super(StockPickingType,
                       self).get_stock_picking_action_picking_type()
        context = action['context'] or {}
        context.update({'create': self.allow_to_create_dashboard})
        action['context'] = context
        return action
