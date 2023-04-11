# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, Warning


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    emp_card_id = fields.Many2one(
        'cardcode.info', string='Appear Code', track_visibility='onchange')
    use_for_employee_coupon = fields.Boolean(string='Use For Employee Coupon')

    # -------------------------------------------------------------------------
    # CONSTRAINS METHODS
    # -------------------------------------------------------------------------
    @api.constrains('emp_card_id')
    def _constrains_check_emp_card(self):
        for rcs in self:
            if rcs.emp_card_id and rcs.emp_card_id.employee_id and rcs.emp_card_id.employee_id != rcs:
                raise UserError(
                    _('You cannot use this Appear Code because the Appear Code is using'))

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    @api.onchange('emp_card_id')
    def _onchange_cardcode_info(self):
        res = {}
        for rcs in self:
            if rcs.emp_card_id:
                if self.env['cardcode.info'].search_count([
                    ('employee_id', 'in', rcs.ids),
                    ('id', '!=', rcs.emp_card_id.id)
                ]) > 0:
                    res['warning'] = {
                        'title': _('Warning'),
                        'message': _('The status of the old card will be returned to draft. Continues ?')
                    }
        return res

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    def check_emp_card(self, vals, create=True):
        if 'emp_card_id' in vals:
            emp_card_id = self.env['cardcode.info'].search(
                [('id', '=', int(vals.get('emp_card_id', 0)))], limit=1)
            if emp_card_id:
                if emp_card_id.card_type != 'employee' or emp_card_id.employee_id or emp_card_id.state != 'create' or not emp_card_id.publish_id or (emp_card_id.publish_id and emp_card_id.publish_id.state != 'confirmed'):
                    raise UserError(
                        _('Appear card code is invalid, please check again.'))

    def using_emp_card(self, vals, create=True):
        if 'emp_card_id' in vals:
            for rec in self:
                if rec.emp_card_id:
                    rec.emp_card_id.write(
                        {'employee_id': rec.id, 'state': 'using'})

    def unused_emp_card(self, vals):
        if 'emp_card_id' in vals:
            for rec in self:
                if rec.emp_card_id:
                    rec.emp_card_id.write(
                        {'employee_id': False, 'state': 'create'})

    @api.model
    def create(self, vals):
        self.check_emp_card(vals, True)
        res = super(HrEmployee, self).create(vals)
        res.using_emp_card(vals, True)
        return res

    def write(self, vals):
        self.check_emp_card(vals, False)
        self.unused_emp_card(vals)
        result = super(HrEmployee, self).write(vals)
        self.using_emp_card(vals, False)
        return result


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    emp_card_id = fields.Many2one(
        'cardcode.info', string='Appear Code')
    use_for_employee_coupon = fields.Boolean(string='Use For Employee Coupon')
