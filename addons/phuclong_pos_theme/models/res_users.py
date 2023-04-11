# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ResUsers(models.Model):
    _inherit = 'res.users'
    
    required_emp_card = fields.Boolean('Required Employee Card', default=False)
    
    @api.onchange('required_emp_card')
    def _onchange_required_emp_card(self):
        res = {}
        for user in self:
            if user.required_emp_card:
                employee_related = self.env['hr.employee'].search([('user_id', '=', user._origin.id)], limit=1) or False
                if not employee_related:
                    user.required_emp_card = False
                    res['warning'] = {'title': _('Warning'), 'message': _('Please create Employee related with this User')}
                else:
                    emp_card_id = self.env['cardcode.info'].search([('card_type', '=', 'employee'),('state', '=', 'using'),
                                                                    ('employee_id', '=', employee_related.id)], limit=1) or False
                    if not emp_card_id:
                        user.required_emp_card = False
                        res['warning'] = {'title': _('Warning'), 'message': _('The employee card code does not exist, please set card first')}
        return res