from odoo import models, api, fields, _

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    use_for = fields.Selection(selection_add=[('payoo', 'Payoo'), ('voucher', 'Voucher')])