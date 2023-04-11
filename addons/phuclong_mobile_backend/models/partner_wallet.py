from odoo import models, fields, api, _

class PartnerWallet(models.Model):
    _name = 'partner.wallet'

    _description = 'Partner Wallet'

    name = fields.Char("Name")
    image_front = fields.Image('Front photo of identity card')
    image_back = fields.Image('Back photo of identity card')
    id_number = fields.Char('ID number')
    amount_total = fields.Float('Amount Total')
    order_ids = fields.Many2many(comodel_name='pos.order')
    pos_payment_ids = fields.Many2many(comodel_name='pos.payment')
    state = fields.Selection([('new', 'New'), ('done', 'Done'), ('cancel', 'Cancel')], string="State", default='new')
    partner_ids = fields.One2many('res.partner', 'wallet_id')

    def confirm(self):
        self.partner_ids.write({'identification_id': self.id_number})
        self.write({'state': 'done'})

    def cancel(self):
        self.write({'state': 'cancel'})

    def set_draft(self):
        self.write({'state': 'new'})