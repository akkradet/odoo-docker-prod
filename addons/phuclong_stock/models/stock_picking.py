# -*- coding: utf-8 -*-
import json
from lxml import etree
from itertools import groupby
from operator import itemgetter

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare, float_round, float_is_zero
from odoo.exceptions import UserError, ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def init(self):
        action_ids = self.env['ir.actions.act_window'].search([
            ('res_model', '=', 'stock.picking'),
            ('view_mode', 'ilike', 'kanban'),
        ])
        for action_id in action_ids:
            action_id.write(
                {'view_mode': ','.join([mode for mode in action_id.view_mode.split(',') if mode != 'kanban'])})
        return super(StockPicking, self).init()

    scheduled_date = fields.Datetime(compute='_compute_scheduled_date')

    def _check_inventory(self):
        if self.date_done and self.state in ('draft', 'waiting', 'confirmed'):
            return
        else:
            return super(StockPicking, self)._check_inventory()

    @api.constrains('scheduled_date', 'date')
    def _check_scheduled_date_date(self):
        for rec in self:
            if rec.scheduled_date and rec.date and rec.scheduled_date < rec.date:
                raise ValidationError(
                    _("Scheduled Date must be equal or later than Creation Date"))

    move_lines = fields.One2many(
        'stock.move', 'picking_id', string="Stock Moves", copy=False)
    move_line_ids = fields.One2many(
        'stock.move.line', 'picking_id', 'Operations', copy=True)

    def action_generate_backorder_wizard(self):
        self = self.with_context(internal_invisible=True)
        return super(StockPicking, self).action_generate_backorder_wizard()

    def do_unreserve(self):
        result = super(StockPicking, self).do_unreserve()
        picking_ids = self.filtered(
            lambda p: p.picking_type_id and p.picking_type_id.code == 'internal' and p.picking_type_id.operation in ['transit_in', 'transit_out'])
        if picking_ids:
            return picking_ids.action_change_location()
        return result
    
    def action_reopen_done(self):
        result = super(StockPicking, self).action_reopen_done()
        picking_type_id = self.env.ref('besco_stock.picking_type_internal_move')
        for pick in self:
            if pick.picking_type_id == picking_type_id:
                pick.action_set_draft_lim()
        return result
    
    def action_set_draft_lim(self):
        for pick in self:
            pick.write({'state': 'draft'})
            pick.move_lines.write({'state': 'draft'})
            pick.move_line_ids.write({'move_id': False})
            pick.move_lines.unlink()
        return 

    def action_change_location(self):
        for order in self:
            action = self.env.ref(
                'phuclong_stock.action_stock_location_change').read()[0]
            default_pick_loc_id = False
            if self.location_id.usage == 'internal':
                default_pick_loc_id = self.location_id.id
            elif self.location_dest_id and self.location_dest_id.usage == 'internal':
                default_pick_loc_id = self.location_dest_id.id
            action['context'] = {
                'default_picking_id': self.id,
                'default_warehouse_id': self.warehouse_id.id,
                'default_pick_loc_id': default_pick_loc_id}
        return action

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        ret_val = super(StockPicking, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(ret_val['arch'])
        if view_type == 'tree':
            internal_move_type = self.env.ref(
                'besco_stock.picking_type_internal_move')
            if internal_move_type and self._context.get('default_picking_type_id', False):
                if internal_move_type.id == self._context.get('default_picking_type_id', False):
                    for node in doc.xpath("//field[@name='location_dest_id']"):
                        modifiers = json.loads(node.get("modifiers"))
                        modifiers['column_invisible'] = False
                        node.set("modifiers", json.dumps(modifiers))
                        node.set("string", _('To Location'))
        ret_val['arch'] = etree.tostring(doc, encoding='unicode')
        return ret_val

    def copy(self, default=None):
        default = dict(default or {})
        internal_move_type = self.env.ref(
            'besco_stock.picking_type_internal_move')
        if internal_move_type and self._context.get('default_picking_type_id', False):
            if internal_move_type.id == self._context.get('default_picking_type_id', False):
                return super(StockPicking, self).copy(default)
        if self._context.get('skip_overprocessed_check', False):
            return super(StockPicking, self).copy(default)
        raise UserError(
            _('You can not copy this kind of document (Picking from origin document)'))

    def _check_available_qty(self):
        mess = ""
        keys_in_groupby = [
            'product_id', 'location_id', 'lot_id', 'package_id', 'owner_id']
        precision_digits = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')

        def _keys_in_sorted(ml):
            return (
                ml.product_id.id, ml.location_id.id, ml.lot_id.id,
                ml.package_id.id, ml.owner_id.id)
        grouped_move_lines_in = {}
        for k, g in groupby(sorted(
                self.mapped('move_line_ids'),
                key=_keys_in_sorted),
                key=itemgetter(*keys_in_groupby)):
            qty_done = 0
            for ml in g:
                qty_done += ml.product_uom_id._compute_quantity(
                    ml.qty_done, ml.product_id.product_tmpl_id.uom_id,
                    product=ml.product_id)
            grouped_move_lines_in[k] = qty_done
        for (
                product_id, location_id,
                lot_id, package_id,
                owner_id), quantity in grouped_move_lines_in.items():
            available_quantity = self.env[
                'stock.quant']._get_available_quantity(
                    product_id, location_id,
                    lot_id=lot_id,
                    package_id=package_id, owner_id=owner_id, strict=True)
            if float_compare(
                    quantity, available_quantity,
                    precision_digits=precision_digits) > 0:
                mess += _(
                    '[%s] %s - You plan to issue %.2f %s '
                    'but you only have not available!\n') % (
                        product_id.default_code, product_id.display_name,
                        quantity, product_id.product_tmpl_id.uom_id.name)
        if mess:
            raise UserError(mess)

    @api.onchange('location_id')
    def _onchange_internal_move_location(self):
        picking_type_id = self.env.ref(
            'besco_stock.picking_type_internal_move')
        if self.picking_type_id == picking_type_id:
            self.move_line_ids.update({'location_id': self.location_id.id})

    @api.onchange('location_dest_id')
    def _onchange_internal_move_location_dest(self):
        picking_type_id = self.env.ref(
            'besco_stock.picking_type_internal_move')
        if self.picking_type_id == picking_type_id:
            self.move_line_ids.update({
                'location_dest_id': self.location_dest_id.id})

    def _check_backorder(self):
        """ This method will loop over all the move lines of self and
        check if creating a backorder is necessary. This method is
        called during button_validate if the user has already processed
        some quantities and in the immediate transfer wizard that is
        displayed if the user has not processed any quantities.

        :return: True if a backorder is necessary else False
        """
        quantity_todo = {}
        quantity_done = {}
        rounding = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for move in self.mapped('move_lines'):
            quantity_todo.setdefault(move.product_id.id, 0)
            quantity_done.setdefault(move.product_id.id, 0)
            quantity_todo[move.product_id.id] += move.product_uom_qty
            quantity_done[move.product_id.id] += move.quantity_done

        for ops in self.mapped('move_line_ids').filtered(lambda x: x.package_id and not x.product_id and not x.move_id):
            for quant in ops.package_id.quant_ids:
                quantity_done.setdefault(quant.product_id.id, 0)
                quantity_done[quant.product_id.id] += quant.qty
        for pack in self.mapped('move_line_ids').filtered(lambda x: x.product_id and not x.move_id):
            quantity_done.setdefault(pack.product_id.id, 0)
            quantity_done[pack.product_id.id] += pack.product_uom_id._compute_quantity(
                pack.qty_done, pack.product_id.uom_id)
        return any(float_compare(quantity_done[x], quantity_todo.get(x, 0), precision_digits=rounding) < 0 for x in quantity_done)

    def button_validate(self):
        for pick in self:
            picking_type_ids = self.env['stock.picking.type']
            picking_type_ids |= self.env.ref(
                'besco_stock.picking_type_good_receipt')
            picking_type_ids |= self.env.ref(
                'besco_stock.picking_type_return_supplier')
            if pick.picking_type_id in picking_type_ids and \
                    not pick.vendor_document:
                raise UserError(_('Please input vendor document.'))
        self.ensure_one()
        # THANH 30072020 - check qty done should not > initial qty for transit in operation
        self._check_received_qty()

        if not self.move_lines and not self.move_line_ids:
            raise UserError(_('Please add some items to move.'))

        # Clean-up the context key at validation to avoid forcing the creation of immediate
        # transfers.
        ctx = dict(self.env.context)
        ctx.pop('default_immediate_transfer', None)
        self = self.with_context(ctx)

        # add user as a follower
        self.message_subscribe([self.env.user.partner_id.id])

        # If no lots when needed, raise error
        picking_type = self.picking_type_id
        precision_digits = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        no_quantities_done = all(
            float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in
            self.move_line_ids.filtered(lambda m: m.state not in ('done', 'cancel')))
        no_reserved_quantities = all(
            float_is_zero(move_line.product_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line
            in self.move_line_ids)
        if no_reserved_quantities and no_quantities_done:
            raise UserError(_(
                'You cannot validate a transfer if no quantites are reserved nor done. To force the transfer, switch in edit more and encode the done quantities.'))
        self._check_inventory_date(no_quantities_done=no_quantities_done)

        if picking_type.use_create_lots or picking_type.use_existing_lots:
            lines_to_check = self.move_line_ids
            if not no_quantities_done:
                lines_to_check = lines_to_check.filtered(
                    lambda line: float_compare(line.qty_done, 0,
                                               precision_rounding=line.product_uom_id.rounding)
                )

            # THANH 07082020 - raise error if missing lot and life_date of product fefo
            # THANH 07082020 - raise error if missing lot and lot_name of product fifo/lifo
            message_warning = ""
            count_lot = 0
            message_lot = ""
            count_fefo = 0
            message_fefo = ""
            for line in lines_to_check:
                product = line.product_id
                if product and product.tracking != 'none':
                    if product.removal_method != 'fefo' and not line.lot_name and not line.lot_id:
                        count_lot += 1
                        message_lot += (_('\n - %s') % (product.display_name))
                    if product.removal_method == 'fefo' and not line.life_date and not line.lot_id:
                        count_fefo += 1
                        message_fefo += (_('\n - %s') % (product.display_name))
            if count_lot:
                message_warning += (_('''You need to supply a Lot/Serial number for %s product(s): %s\n''') % (
                    count_lot, message_lot))
            if count_fefo:
                message_warning += (_('''You need to supply a Lot/Serial number and End of Life Date for %s product(s): %s''') % (
                    count_fefo, message_fefo))
            if count_lot or count_fefo:
                raise ValidationError(message_warning)

        # Minh ràng buộc không cho done phiếu Internal Transfer khi không đủ số lượng tồn kho
        if self.picking_type_id.operation in ['move', 'other_out']:
            if self.move_line_ids.filtered(lambda x: not x.qty_done):
                raise UserError(_(
                    'You cannot validate a transfer if no quantites are reserved nor done. To force the transfer, switch in edit more and encode the done quantities.'))
            self._check_available_qty()

        if no_quantities_done:
            return self.action_generate_immediate_wizard()
        if self.location_id.usage == 'internal':
            moves_overprocessed = self.with_context(
                overprocessed_stock_moves=True)._get_overprocessed_stock_moves()
        else:
            moves_overprocessed = self._get_overprocessed_stock_moves()
        if moves_overprocessed and not self._context.get('skip_overprocessed_check'):
            if self.location_id.usage == 'internal':
                products = ''
                for pro in moves_overprocessed.mapped('product_id'):
                    products += (_('\n - %s') % (pro.display_name))
                raise ValidationError(
                    _('You have processed more than what was initially planned for the product(s): %s.') % (
                        products))
            return self.action_generate_overprocessed_wizard()

        if self._check_backorder():
            if self.picking_type_id.code == 'internal':
                # THANH 30072020 - context internal_invisible helps to hide button Create Backorder
                # and button No Backorder from pop up Create Backorder
                return self.with_context(internal_invisible=True).action_generate_backorder_wizard()
            return self.action_generate_backorder_wizard()

        return self.with_context(log_users=True).action_generate_immediate_wizard()

    def action_generate_overprocessed_wizard(self):
        action = super(
            StockPicking, self).action_generate_overprocessed_wizard()
        action['name'] = _('Processed different from initial demand!')
        return action

    def _get_overprocessed_stock_moves(self):
        self.ensure_one()
        if self._context.get('overprocessed_stock_moves', False):
            return super(StockPicking, self)._get_overprocessed_stock_moves()
        return self.move_lines.filtered(
            lambda move: move.reserved_availability != 0 and float_compare(move.quantity_done, move.reserved_availability, precision_rounding=move.product_uom.rounding) != 0)
