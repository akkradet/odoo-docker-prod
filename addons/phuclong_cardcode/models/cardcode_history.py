# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import Warning


class CardcodeHistory(models.Model):
    _name = 'cardcode.history'
    _description = 'Cardcode History'
    _order = 'id desc'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    old_cardcode = fields.Char(string='Old Card Code')
    new_cardcode = fields.Char(string='New Card Code')
    date = fields.Datetime('Created Date')
    user_id = fields.Many2one('res.users', string='Responsible')
    partner_id = fields.Many2one('res.partner', string='Customer')
    mobile = fields.Char(related='partner_id.mobile', string='Mobile', store=True, readonly=True)
    note = fields.Text('Note')
    reason = fields.Selection([('lost', 'Lost card'),
                               ('destroy', 'Card is broken'),
                               ('wrong_code', 'Wrong code'),
                               ('exchange_by_fee', 'Exchange card by a fee'),
                               ('new_member', 'New Member')
                               ], string="Reason",)
    payment_status = fields.Selection([('paid', 'Paid'),
                                       ('not_paid_yet', 'Not paid yet'),
                                       ], string="Payment Status", )

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------
    def name_get(self):
        res = []
        for cardcode in self:
            name = cardcode.sudo().partner_id.name or cardcode.sudo().new_cardcode or ''
            res.append((cardcode.id, name))
        return res
