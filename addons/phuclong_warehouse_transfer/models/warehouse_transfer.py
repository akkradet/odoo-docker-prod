# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError


class WarehouseTransferLine(models.Model):
    _inherit = "warehouse.transfer.line"

    @api.onchange('product_id')
    def onchange_product_id(self):
        super(WarehouseTransferLine, self).onchange_product_id()
        if not self.product_id:
            return
        self.product_uom = self.product_id.product_tmpl_id.uom_id or self.product_uom

class WarehouseTransfer(models.Model):
    _inherit = "warehouse.transfer"

    def button_to_approve(self):
        for rec in self:
            if rec.state != 'draft':
                states = dict(
                    self._fields['state']._description_selection(self.env))
                return {
                    'type': 'ir.actions.act_window.message',
                    'title': _('Warning'),
                    'message': _("Warehouse Transfer %s is %s.") % (rec.display_name, states.get(rec.state, '')),
                    'close_button_title': False,
                    'buttons': [
                        {
                            'type': 'ir.actions.client',
                            'tag': 'reload',
                            'classes': 'btn-primary',
                            'name': _('Reload'),
                        }
                    ]
                }
        return super(WarehouseTransfer, self).button_to_approve()

    def button_approve(self):
        for rec in self:
            if not rec.origin:
                raise UserError(_("Source is not inputed yet"))
            if rec.state != 'to approve':
                states = dict(
                    self._fields['state']._description_selection(self.env))
                return {
                    'type': 'ir.actions.act_window.message',
                    'title': _('Warning'),
                    'message': _("Warehouse Transfer %s is %s.") % (rec.display_name, states.get(rec.state, '')),
                    'close_button_title': False,
                    'buttons': [
                        {
                            'type': 'ir.actions.client',
                            'tag': 'reload',
                            'classes': 'btn-primary',
                            'name': _('Reload'),
                        }
                    ]
                }
        return super(WarehouseTransfer, self).button_approve()

    def _get_invisible_approve(self):
        invisible_approve = False
        for transfer in self:
            admin_uid = self.env.ref('base.user_admin').id
            if self._uid not in (SUPERUSER_ID, admin_uid) and \
                    transfer.supplier_wh_id.id not in \
                    self.env.user._warehouses_domain():
                invisible_approve = True
        return invisible_approve

    @api.depends('supplier_wh_id')
    def compute_invisible_approve(self):
        for transfer in self:
            invisible_approve = transfer._get_invisible_approve()
            transfer.invisible_approve = invisible_approve

    def _get_invisible_reverse(self):
        invisible_reverse = False
        for transfer in self:
            admin_uid = self.env.ref('base.user_admin').id
            if self._uid not in (SUPERUSER_ID, admin_uid) and \
                    transfer.supplied_wh_id.id not in \
                    self.env.user._warehouses_domain():
                invisible_reverse = True
        return invisible_reverse

    @api.depends('supplied_wh_id')
    def compute_invisible_reverse(self):
        for transfer in self:
            invisible_reverse = transfer._get_invisible_reverse()
            transfer.invisible_reverse = invisible_reverse

    date_request = fields.Datetime(
        string="Request Date",
        readonly=True,
        default=fields.Datetime.now,
        copy=False,
        states={'draft': [('readonly', False)]})
    invisible_approve = fields.Boolean(
        compute="compute_invisible_approve",
        string="Invisible Approve")
    invisible_reverse = fields.Boolean(
        compute="compute_invisible_reverse",
        string="Invisible Reverse")

    def _get_reverse_transfer_line(self):
        return_lines = []
        for trans in self:
            pickings = trans.picking_ids.filtered(
                lambda x: x.picking_type_operation == 'transit_out'
                and x.warehouse_id == trans.sudo().supplier_wh_id
                and x.state == 'done')
            for move in pickings.mapped('move_lines').filtered(
                    lambda m: m.state == 'done'):
                moves_dest = move.move_dest_ids.filtered(
                    lambda m: m.state != 'cancel')
                qty_dest = moves_dest and sum(
                    moves_dest.mapped('product_qty')) or 0.0
                moves_returned = move.returned_move_ids.filtered(
                    lambda m: m.state != 'cancel')
                qty_returned = moves_returned and sum(
                    moves_returned.mapped('product_qty')) or 0
                quantity = move.product_qty - qty_dest - qty_returned
                if quantity <= 0:
                    continue
                vals = {
                    'product_id': move.product_id,
                    'transfer_line_id': move.transfer_line_id,
                    'move_id': move}
                uom_quantity = move.product_id.uom_id._compute_quantity(
                    quantity, move.product_uom,
                    rounding_method='HALF-UP',
                    product=move.product_id)
                uom_quantity_back_to_product_uom = \
                    move.product_uom._compute_quantity(
                        uom_quantity, move.product_id.uom_id,
                        rounding_method='UP',
                        product=move.product_id)
                rounding = self.env['decimal.precision'].precision_get(
                    'Product Unit of Measure')
                if float_compare(
                        quantity, uom_quantity_back_to_product_uom,
                        precision_digits=rounding) == 0:
                    vals.update({
                        'product_uom_qty': uom_quantity,
                        'product_uom': move.product_uom})
                else:
                    vals.update({
                        'product_uom_qty': quantity,
                        'product_uom': move.product_id.uom_id})
                return_lines.append(vals)
        return return_lines

    def _prepare_reverse_move_default_values(
            self, qty_returned, new_picking, return_line, move):
        vals = {
            'picking_id': new_picking.id,
            'origin_returned_move_id': move.id,
            'product_id': return_line['product_id'].id,
            'product_uom_qty': qty_returned,
            'product_uom': return_line['product_uom'].id,
            'location_id': new_picking.location_id.id,
            'location_dest_id': new_picking.location_dest_id.id,
            'picking_type_id': new_picking.picking_type_id.id,
            'warehouse_id': new_picking.warehouse_id.id,
            'transfer_line_id': return_line['transfer_line_id'].id,
            'procure_method': 'make_to_stock',
            'to_refund': True,
            'state': 'draft'}
        return vals

    def reverse_transfer(self):
        for trans in self:
            picking_type_id = trans.supplier_wh_id.transit_in_type_id
            internal_transit_location, external_transit_location = \
                trans.supplier_wh_id._get_transit_locations()
            location_id = \
                internal_transit_location \
                if trans.supplied_wh_id.company_id \
                == trans.supplier_wh_id.company_id \
                else external_transit_location
            location_dest_id = trans.supplier_wh_id.lot_stock_id
            if not location_id:
                raise UserError("Default Source Location do not exist!")
            if not location_dest_id:
                raise UserError("Default Destination Location do not exist!")
            return_lines = trans._get_reverse_transfer_line()
            if not return_lines:
                raise UserError(_(
                    'You must cancel the picking '
                    'before making the reverse transfer action'))
            PickingObj = self.env['stock.picking']
            new_picking_id = PickingObj.with_context(
                action_from_warehouse_transfer=True).create({
                    'date_done': fields.Datetime.now(),
                    'responsible': self.env.user.name,
                    'picking_type_id': picking_type_id.id,
                    'state': 'draft',
                    'origin': _("Return of %s") % trans.name,
                    'warehouse_id': trans.supplier_wh_id.id,
                    'location_id': location_id.id,
                    'location_dest_id': location_dest_id.id})
            new_picking_id.message_post_with_view(
                'mail.message_origin_link',
                values={'self': new_picking_id, 'origin': trans},
                subtype_id=self.env.ref('mail.mt_note').id)
            for return_line in return_lines:
                vals = self._prepare_reverse_move_default_values(
                    return_line['product_uom_qty'], new_picking_id,
                    return_line, return_line['move_id'])
                new_id = return_line['move_id'].copy(default=vals)
                move_orig_to_link = return_line[
                    'move_id'].move_dest_ids.mapped('returned_move_ids')
                move_dest_to_link = return_line[
                    'move_id'].move_orig_ids.mapped('returned_move_ids')
                vals['move_orig_ids'] = [
                    (4, m.id) for m in move_orig_to_link | return_line[
                        'move_id']]
                vals['move_dest_ids'] = [(4, m.id) for m in move_dest_to_link]
                new_id.write(vals)
            new_picking_id.action_confirm()
            new_picking_id.action_assign()
            new_picking_id.action_fullfill()
            new_picking_id.action_done()
            return new_picking_id

    invisible_refuse = fields.Boolean(compute='_compute_invisible_button')
    invisible_cancel = fields.Boolean(compute='_compute_invisible_button')

    def _compute_invisible_button(self):
        user = self.env.user
        warehouse_ids = self.env.user._warehouses_domain()
        is_admin = user._is_admin()
        for rec in self:
            invisible_refuse = True
            invisible_cancel = True
            if is_admin:
                invisible_refuse = False
                invisible_cancel = False
            else:
                if rec.supplied_wh_id and rec.supplied_wh_id.id not in warehouse_ids:
                    invisible_refuse = False
                if rec.supplier_wh_id and rec.supplier_wh_id.id not in warehouse_ids:
                    invisible_cancel = False
            rec.invisible_refuse = invisible_refuse
            rec.invisible_cancel = invisible_cancel
