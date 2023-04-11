# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError, Warning


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    product_max_qty = fields.Float(string='Maximum Forecast Quantity', related='orderpoint_id.product_max_qty',
                                   readonly=True)
    is_product_max_qty_exceeded = fields.Boolean(
        string='Max Quantity Exceeded',)
    provided_by = fields.Char(
        related="product_id.provided_by", readony=True, store=False)

    qty_request = fields.Float(string='Request Qty', digits=(16, 2))
    product_qty = fields.Float(
        string='Quantity', digits=(16, 2), required=True)

    qty_received = fields.Float(
        string="Received", digits=(16, 2), copy=False, compute=False)
    qty_returned = fields.Float(
        string="Returned", digits=(16, 2), copy=False, compute=False)
    qty_to_returned = fields.Float(
        string="Waiting Return", digits=(16, 2), copy=False)

    qty_to_invoice = fields.Float(compute='_compute_to_invoice_qty',
                                  string='To Invoice', store=True, readonly=True, digits=(16, 2))
    qty_invoiced = fields.Float(compute='_compute_qty_invoiced',
                                string='Invoiced', store=True, readonly=True, digits=(16, 2))

    picking_state = fields.Char(related=False, compute='_compute_picking_state',
                                string="Picking State", store=True, readonly=True)

    @api.depends(
        'order_id',
        'order_id.picking_ids',
        'order_id.picking_ids.state'
    )
    def _compute_picking_state(self):
        states = dict(
            self.env['stock.picking']._fields['state']._description_selection(self.env))
        for rec in self:
            state = False
            if rec.order_id and rec.order_id.picking_ids:
                for picking_id in rec.order_id.picking_ids:
                    state = states.get(picking_id.state, '')
            rec.picking_state = state

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    # _onchange_partner_id, _onchange_product_id
    @api.onchange('product_id')
    def onchange_product_id(self):
        for rcs in self:
            if rcs.orderpoint_id and rcs.product_id != rcs.orderpoint_id.product_id:
                raise Warning(
                    _("You can't change product because the order line have a Reordering Rules %s." % rcs.orderpoint_id.name))
        res = super(PurchaseOrderLine, self).onchange_product_id()
        product_lang = self.product_id.with_context(
            lang=self.partner_id.lang,
            partner_id=self.partner_id.id)
        self.name = product_lang.display_name
        if product_lang.description_purchase:
            self.name = product_lang.description_purchase
        if self.order_id and self.order_id.state == 'draft' and self.qty_request != self.product_qty:
            self.qty_request = self.product_qty
        return res

    @api.onchange('qty_request')
    def onchange_qty_request(self):
        self.product_qty = self.qty_request
        self._onchange_quantity()

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        super(PurchaseOrderLine, self)._onchange_quantity()
        res = dict()
        for rcs in self:
            is_product_max_qty_exceeded = False
            if not rcs.orderpoint_id:
                orderpoint_id = self.env['stock.warehouse.orderpoint'].search([
                    ('product_id', '=', rcs.product_id.id),
                    ('warehouse_id', '=', rcs.warehouse_id.id)])
            else:
                orderpoint_id = rcs.orderpoint_id
            if not orderpoint_id:
                continue
            if orderpoint_id and rcs.warehouse_id == orderpoint_id.warehouse_id:
                if orderpoint_id.product_max_qty != 0 and rcs.product_qty > orderpoint_id.product_max_qty and \
                        rcs.product_id == orderpoint_id.product_id:
                    product_available = rcs.product_id.with_context(
                        warehouse=rcs.warehouse_id.id)._product_available()
                    qty_available = product_available[rcs.product_id.id][
                        'qty_available'] or 0.0
                    # quant_ids = self.env['stock.quant'].sudo().search([
                    #     ('product_id', '=', rcs.product_id.id),
                    #     ('warehouse_id', '=', rcs.warehouse_id.id)])
                    # qty_available = quant_ids and sum(quant_ids.mapped('inventory_quantity')) or 0.0
                    message = _("The ordered quantity must be less than %(qty_available)s. "
                                "It is because the maximum quantity for product %(product_id)s "
                                "at warehouse %(warehouse_name)s is %(product_max_qty)s (%(orderpoint_id)s)."
                                ) % {'qty_available': orderpoint_id.product_max_qty,
                                     'product_id': rcs.product_id.name,
                                     'warehouse_name': orderpoint_id.warehouse_id.name,
                                     'product_qty_available': qty_available,
                                     'orderpoint_id': orderpoint_id.name,
                                     'product_max_qty': int(rcs.orderpoint_id.product_max_qty),
                                     }
                    is_product_max_qty_exceeded = True
                    if self.env['res.users'].has_group('purchase.group_purchase_manager'):
                        res.update({'warning': {'title': _("Warning"),
                                                'message': message, },
                                    })
                    else:
                        raise Warning(message)
        res.update({
            'is_product_max_qty_exceeded': is_product_max_qty_exceeded
        })
        return res

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------
    def write(self, vals):
        order_line = {}
        for rcs in self:
            order_line.update({rcs.id: {'product_old': rcs.product_id,
                                        'product_qty_old': rcs.product_qty}})
        res = super(PurchaseOrderLine, self).write(vals)
        for rcs in self:
            if vals.get('product_id', False) or vals.get('product_qty', False):
                message = ''
                if vals.get('product_id', False):
                    message += _("Product: %s -> %s") % (order_line[rcs.id]['product_old'].name,
                                                         rcs.product_id.name)
                else:
                    message += _("Product: %s") % (
                        order_line[rcs.id]['product_old'].name,)
                if vals.get('product_qty', False):
                    message += _("<br>Quantity: %s -> %s") % (order_line[rcs.id]['product_qty_old'],
                                                              vals.get('product_qty', False))
                rcs.order_id.message_post(body=message)
        return res

    @api.model
    def create(self, vals):
        res = super(PurchaseOrderLine, self).create(vals)
        return res

    def _suggest_quantity(self):
        '''
        Suggest a minimal quantity based on the seller
        '''
        if not self.product_id:
            return
        seller_min_qty = self.product_id.seller_ids\
            .filtered(lambda r: r.name == self.order_id.partner_id)\
            .sorted(key=lambda r: r.min_qty)
        if seller_min_qty:
            if self.order_id and self.order_id.type == 'return':
                self.product_qty = 0.0
            else:
                self.product_qty = seller_min_qty[0].min_qty or self.product_qty or 1.0
            self.product_uom = seller_min_qty[0].product_uom or self.product_uom
        else:
            if self.order_id and self.order_id.type == 'return':
                self.product_qty = 0.0
            else:
                self.product_qty = 1.0
        return True

    def get_orderpoint(self):
        min_qty, max_qty = 0, 0
        orderpoint_id = self.env['stock.warehouse.orderpoint'].search([
            ('product_id', '=', self.product_id.id),
            ('warehouse_id', '=', self.order_id.warehouse_id.id)], limit=1)
        if orderpoint_id:
            min_qty = orderpoint_id.product_min_qty
            max_qty = orderpoint_id.product_max_qty
        return min_qty, max_qty
