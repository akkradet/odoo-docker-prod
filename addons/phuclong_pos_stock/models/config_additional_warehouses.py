# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError, AccessError, ValidationError

class ConfigAdditionalWarehouses(models.Model):
    _name = 'config.additional.warehouses'
    _description = 'Config Additional Warehouses'
    
    name = fields.Char(string='Description', required=True)
    from_date = fields.Date(required=True)
    to_date = fields.Date(required=True)
    line_ids = fields.One2many('config.additional.warehouses.line', 'config_id', string='Lines', copy=True)
    check_applied = fields.Boolean(string="Has Applied", default=False, copy=False)
    check_expired = fields.Boolean(string="Has Expired", default=False, copy=False)
    
    @api.constrains('from_date', 'to_date')
    def _check_date(self):
        if self.to_date < self.from_date:
            raise ValidationError(_('Date From must be before Date To'))
    
    def button_apply(self):
        for line in self.line_ids:
            wh_vals = []
            for wh in line.support_warehouse_ids:
                if wh not in line.user_id.warehouse_ids:
                    wh_vals.append((4, wh.id))
            if wh_vals:
                line.user_id.write({'warehouse_ids': wh_vals})
                line.user_id.update_profile()
        self.check_applied = True
                
    @api.model 
    def auto_config_user_warehouses(self):
        today = fields.Datetime.now().date()
        config_to_add_wh = self.search([('check_applied','=',False),('from_date', '<=', today),('to_date', '>=', today)])
        config_to_remove_wh = self.search([('check_applied','=',True),('check_expired','=',False),('to_date', '<', today)])
        for config in config_to_add_wh:
            config.button_apply()
        for config in config_to_remove_wh:
            for line in config.line_ids:
                wh_vals = []
                for wh in line.support_warehouse_ids:
                    if wh in line.user_id.warehouse_ids:
                        wh_vals.append((3, wh.id))
                if wh_vals:
                    line.user_id.write({'warehouse_ids': wh_vals})
                    line.user_id.update_profile()
            config.check_expired = True
    
class ConfigAdditionalWarehousesLine(models.Model):
    _name = 'config.additional.warehouses.line'
    _description = 'Config Additional Warehouses Line'
    
    config_id = fields.Many2one('config.additional.warehouses', 'Config', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', required=True, domain=[('id','not in', [1, 2])])
    warehouse_ids = fields.Many2many('stock.warehouse', 'warehouse_config_addition_rel', 'warehouse_id', 'config_id',
                                      string="Current Working Warehouse", readonly=True)
    support_warehouse_ids = fields.Many2many('stock.warehouse', 'support_warehouse_config_addition_rel', 'warehouse_id', 'config_id',
                                      string="Support Warehouse", required=True)
    
    @api.onchange('user_id')
    def onchange_user_id(self):
        self.warehouse_ids = self.user_id.warehouse_ids
        
