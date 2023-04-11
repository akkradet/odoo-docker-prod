# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    is_pos_manager = fields.Boolean('Is POS Manager', default=False, copy=False)
    warehouses_dom = fields.Char(related='user_id.warehouses_dom', string="Warehouse Domain", readonly=True)
    
class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    is_pos_manager = fields.Boolean('Is POS Manager', default=False, copy=False)
    
