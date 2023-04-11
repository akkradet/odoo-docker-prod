# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WizardCardcodeHistoryInfo(models.TransientModel):
    _name = "wizard.cardcode.history.info"

    cardcode_id = fields.Many2one('cardcode.info', string='Card Code')
    reason = fields.Selection([('lost', 'Lost card'),
                               ('destroy', 'Card is broken'),
                               ('wrong_code', 'Wrong code'),
                               ('exchange_by_fee', 'Exchange card by a fee'),
                               ('new_member', 'New Member')
                               ], string="Reason", required=False)
    payment_status = fields.Selection([('paid', 'Paid'),
                                       ('not_paid_yet', 'Not paid yet'),
                                       ], string="Payment Status", )
    partner_id = fields.Many2one('res.partner', string='Partner')
    cardcode_old_id = fields.Many2one('cardcode.info', string='Old Card Code')
    note = fields.Text('Note')

    @api.onchange('cardcode_old_id')
    def onchange_cardcode_old_id(self):
        for rcs in self:
            res = {}
            if rcs.cardcode_old_id:
                #                 res.update({'domain': {'cardcode_id': [('state', '=', 'create'), '|', '&', ('id', 'in', rcs.cardcode_old_id.ids),
                #                                                        ('state', '=', 'create'),
                #                                                        ('card_type', '=', 'partner')]
                #                                                        }})
                res.update({'domain': {'cardcode_id': ['|', '&', ('id', 'in', rcs.cardcode_old_id.ids),
                                                       ('state', '=', 'using'),
                                                       # '&',
                                                       ('state', '=', 'create'),
                                                       ('card_type', '=', 'partner'), ]
                                       }})
        return res

    def action_create_cardcode_history(self):
        for rcs in self:
            #             if rcs.cardcode_id == rcs.cardcode_old_id:
            #                 return
            if rcs.cardcode_id:
                vals = {'date': fields.Datetime.now(),
                        'note': rcs.note or '',
                        'old_cardcode': rcs.cardcode_old_id and rcs.cardcode_old_id.appear_code or '',
                        'new_cardcode': rcs.cardcode_id and rcs.cardcode_id.appear_code or '',
                        'partner_id': rcs.partner_id and rcs.partner_id.id or '',
                        'reason': rcs.reason or False,
                        'payment_status': rcs.reason != 'exchange_by_fee' and False or rcs.payment_status or False,
                        'user_id': self._uid
                        }
                rcs.partner_id.appear_code_id = rcs.cardcode_id
                rcs.cardcode_id.write({'partner_id': rcs.partner_id.id,
                                       'state': 'using'})
                if rcs.cardcode_old_id != rcs.cardcode_id:
                    rcs.cardcode_old_id.write({'partner_id': False,
                                               'state': 'close'})
                history_id = self.env['cardcode.history'].search([
                    ('reason', '=', rcs.reason),
                    ('reason', '=', 'exchange_by_fee'),
                    ('new_cardcode', '=', rcs.cardcode_id.appear_code)],
                    limit=1, order='date desc')
                if history_id:
                    history_id.write(vals)
                else:
                    self.env['cardcode.history'].create(vals)
        return
