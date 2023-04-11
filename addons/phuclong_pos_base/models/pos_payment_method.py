# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang
import time
    
class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"
    
    use_for = fields.Selection([('cash', 'Cash'), ('bank', 'Bank'), ('on_account_emp', 'On Account Employee'), ('on_account_customer', 'On Account Customer'),
                                ('momo', 'Momo'), ('visa', 'Visa')], string="Use For", default=False, copy=False) 
    is_cash_count = fields.Boolean(string='Cash', compute='_compute_is_cash_count', store=True, readonly=True)
    logo = fields.Image('Logo', copy=False, attachment=True, max_width=1024, max_height=1024)
    sequence = fields.Integer(default=0)
    visa_ids = fields.One2many('pos.payment.method.visa', 'payment_method_id')
    
    @api.depends('use_for')
    def _compute_is_cash_count(self):
        for method in self:
            if method.use_for == 'cash':
                method.is_cash_count = True
            else:
                method.is_cash_count = False
                
class PosPaymentMethodVisa(models.Model):
    _name = "pos.payment.method.visa"
    _description = "PosPaymentMethodVisa"
    
    code = fields.Char(required=True)
    payment_method_id = fields.Many2one('pos.payment.method', ondelete="cascade")
    
class PosPayment(models.Model):
    _inherit = "pos.payment"
    
    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    on_account_partner_id = fields.Many2one('res.partner', string="Partner On Account", readonly=True)
    on_account_info = fields.Char(string="On Account Info", readonly=True)
