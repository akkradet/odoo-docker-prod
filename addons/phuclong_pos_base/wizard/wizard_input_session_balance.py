# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class WizardInputSessionBalance(models.TransientModel):
    _name = "wizard.input.session.balance"

    currency_id = fields.Many2one('res.currency', string="Currency")
    balance_start = fields.Monetary(string="Starting Balance")
    
    @api.model
    def default_get(self, fields):
        active_ids = self._context.get('active_ids')
        pos_session = self.env['pos.session'].browse(active_ids)
        res = super(WizardInputSessionBalance, self).default_get(fields)
        if pos_session:
            res.update({'currency_id': pos_session.currency_id.id})
        return res

    def set_balance_start(self):
        active_ids = self._context.get('active_ids')
        pos_session = self.env['pos.session'].browse(active_ids)
        if len(str(int(self.balance_start))) > 15:
            raise UserError(_('Please input smaller number.'))
        if pos_session:
            pos_session.cash_register_balance_start = self.balance_start
            pos_session.open_session()
