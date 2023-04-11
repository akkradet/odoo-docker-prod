# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class productLock(models.Model):
    _name = 'pos.product.lock'
    _inherit = ['mail.thread']

    name = fields.Char(
        'Name', 
        compute='_compute_complete_name', 
        track_visibility='onchange')
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string="Stock Warehouse",
        track_visibility='onchange')
    product_ids = fields.Many2many(
        'product.template',
        'product_lock_template_rel',
        'lock_id', 'product_id',
        string='Product Name',
        domain=[('available_in_pos', '=', True)],
        track_visibility='onchange')

    @api.depends('warehouse_id')
    def _compute_complete_name(self):
        for lock in self:
            if lock.warehouse_id:
                lock.name = 'Lock board: %s' % (lock.warehouse_id.name)
            else:
                lock.name = False

    @api.onchange('warehouse_id')
    def set_domain_depend_on_warehouse_id(self):
        domain = []
        locks = self.search([])
        if locks:
            lock_ids = locks.mapped('warehouse_id').ids
            domain = [('id', 'not in', lock_ids)]
        return {'domain': {'warehouse_id': domain}}
    
    @api.model
    def check_condition_show_dialog(self, record_id, data_changed):
        warehouse_id = data_changed['warehouse_id']
        session_opening = self.env['pos.session'].search([('state', '=', 'opened'),
                                                          ('config_id.warehouse_id', '=', warehouse_id)], limit=1) or False
        if session_opening:
            return True
        else:
            return False

