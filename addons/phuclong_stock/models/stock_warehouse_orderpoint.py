# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_round


class StockWarehouseOrderpoint(models.Model):
#     _inherit = 'stock.warehouse.orderpoint'

    _name = 'stock.warehouse.orderpoint'
    _inherit = ['stock.warehouse.orderpoint', 'mail.thread', 'mail.activity.mixin']

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    week_month_toggle = fields.Selection([('weekday', 'Weekday'),
                                          ('day_of_month', 'Day of the Month')],
                                          'Reordering point option', default='weekday',
                                          help="Select reordering point option: Weekday or Day of the Month")
    weekday_ids = fields.Many2many('res.calendar.weekday', 'stock_warehouse_orderpoint_weekday_rel',
                               'orderpoint_id', 'weekday_id', string='Weekday', help="Weekday")
    day_of_month_ids = fields.Many2many('res.calendar.daymonth', 'stock_warehouse_orderpoint_daymonth_rel',
                                    'orderpoint_id', 'daymonth_id', string='Day of the Month')
    safety_cycle_days = fields.Float(
        string="Days in Safety Cycle",
        required=True,
        help="The number of days in the Safety Cycle is required to calculate the amount of replenished stock.")
    qty_available = fields.Float(
        string='Quantity On Hand',
        readonly=True,
        digits=(16, 3))
    # free_qty = fields.Float('Free To Use Quantity ',)
    incoming_qty = fields.Float(
        string='Incoming',
        readonly=True,
        digits=(16, 3))
    outgoing_qty = fields.Float(
        string='Outgoing',
        readonly=True,
        digits=(16, 3))
    virtual_available = fields.Float(
        string='Forecast Quantity',
        readonly=True,
        digits=(16, 3))
    product_weekly_outgoing_qty = fields.Float(
        string="Last 7 days Outgoing Quantity",
        readonly=True,
        digits=(16, 3))
    product_weekly_average_uom_sales_qty = fields.Float(
        string="Last 7 days Average Sales Quantity",
        readonly=True,
        help="Average Sales Quantity for the last 7 days",
        digits=(16, 3))
    date_update = fields.Datetime(string='Update date')
    lead_days = fields.Integer(
        'Lead Time', default=0,
        help=_("Number of days after the orderpoint is triggered to receive "
               "the products or to order to the vendor")
    )
    lead_type = fields.Selection(
        [('net', 'Days to get the products'),
         ('supplier', 'Days to purchase')],
        'Lead Type',
        required=True, default='net')
    
    _sql_constraints = [('product_warehouse_orderpoint_uniq', 'check(1=1)', 'No error'),]

    @api.constrains('product_id', 'warehouse_id')
    def _check_product_warehouse(self):
        for rcs in self:
            if rcs.product_id and rcs.warehouse_id:
                orderpoint_id = self.env['stock.warehouse.orderpoint'].search([('id', '!=', rcs.id),
                                                                               ('product_id', '=', rcs.product_id.id),
                                                                               ('warehouse_id', '=', rcs.warehouse_id.id)])
                if orderpoint_id:
                    raise UserError(_("Reordering rule for %s - %s at warehouse %s already exists: rule number %s" \
                                       % (rcs.product_id.default_code, rcs.product_id.name, rcs.warehouse_id.name,
                                          orderpoint_id.name)))

    @api.constrains('safety_cycle_days')
    def _check_safety_cycle_days(self):
        for rcs in self:
            if rcs.safety_cycle_days < 0:
                raise UserError(_("The number of days in safety cycle must be greater or equal to 0."))

    @api.constrains('product_min_qty', 'product_max_qty')
    def _check_range_product_qty(self):
        for rcs in self:
            if rcs.product_min_qty > rcs.product_max_qty:
                raise UserError(_("The Minimum Quantity must be less than or equal to the Maximum Quantity."))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super(StockWarehouseOrderpoint, self)._onchange_product_id()
        for rcs in self:
            if rcs.product_id:
                qty_multiple = rcs.product_id.uom_po_id.factor_inv / rcs.product_id.uom_id.factor_inv
                rcs.qty_multiple = float_round(qty_multiple, precision_rounding=rcs.product_uom.rounding)
        return res

    def action_view_po_line(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'views': [(self.env.ref('purchase.purchase_order_line_tree').id, 'tree')],
            'view_mode': 'tree',
            'name': _('Purchase Order Lines'),
            'res_model': 'purchase.order.line',
        }
        context = {
        }
        # Define domains and context
        domain = [
            ('orderpoint_id', '=', self.id),
        ]
        action['context'] = context
        action['domain'] = domain
        return action

    def action_open_quants(self):
        self.ensure_one()
        action = self.product_id.action_open_quants()
        action['context'].update({
            'search_default_warehousegroup': 1
        })
        action['domain'].append(('warehouse_id', '=', self.warehouse_id.id))
        return action

    def action_view_move(self):
        self.ensure_one()
        action = self.env.ref('stock.stock_move_action').read()[0]
        ctx = dict({})
        ctx.update({
            'search_default_groupby_picking_type': 1,
            'search_default_status': 1
            })
        action['context'] = ctx
        action['domain'] = [
            ('warehouse_id', '=', self.warehouse_id.id),
            ('product_id', '=', self.product_id.id)]
        return action

    def button_run_manually(self):
        self.ensure_one()
        action = self.env.ref('stock.action_procurement_compute').read()[0]
        return action

    @api.model
    def create(self, vals):
        if 'warehouse_id' in vals and 'location_id' not in vals:
            warehouse_id = self.env['stock.warehouse'].browse(
                vals['warehouse_id'])
            vals['location_id'] = warehouse_id.lot_stock_id.id
        return super(StockWarehouseOrderpoint, self).create(vals)
