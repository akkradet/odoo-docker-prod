# -*- coding: utf-8 -*-

from odoo import api, fields, models, _ , SUPERUSER_ID

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    on_acount_amount = fields.Float('On Account Amount')
    payment_pos_order_ref = fields.Char('Lasted Payment Ref', readonly=True)
    
    @api.model
    def get_on_acount_amount(self, employee_id):
        employee = self.browse(employee_id)
        department = employee and employee.department_id.name
        return employee and employee.on_acount_amount or 0, department
    
    @api.model
    def update_employee_on_account_amount(self, employee_list, order_name):
        updated_employee = self.search([('payment_pos_order_ref','=',order_name)],limit=1) or False 
        if updated_employee:
            return True
        
        update_list = []
        #Check first 
        for employee in employee_list:
            employee_id = self.browse(employee[0])
            amount_update = employee[1]
            if employee_id:
                amount_available = employee_id.on_acount_amount
                if amount_update > amount_available:
                    return employee_id.on_acount_amount
            update_list.append([employee_id, amount_available-amount_update])
        
        #Update later    
        for list in update_list:
            employee_update = list[0]
            employee_update.with_user(SUPERUSER_ID).write({'on_acount_amount': list[1], 'payment_pos_order_ref':order_name})
                
        return True
    
class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'
    
    on_acount_amount = fields.Float('On Account Amount')
    payment_pos_order_ref = fields.Char('Lasted Payment Ref', readonly=True)