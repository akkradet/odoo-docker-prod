# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
import werkzeug
import werkzeug.utils
from odoo.http import request

class LoginScannerWizard(models.TransientModel):
    _name = "login.scanner.wizard"
    _inherit = 'barcodes.barcode_events_mixin'

    scanner_code = fields.Char('Scanner Code')

    @api.model
    def do_barcode_scan(self, barcode, record):
        if not barcode:
            raise UserError('Invalid Barcode')
        # Search barcode:
        card = self.env['cardcode.info'].sudo().search([
            ('hidden_code', '=', barcode),
            ('card_type', '=', 'employee'),
            ('state', '=', 'using')
        ], limit=1)
        if not card or card.employee_id.user_id != self.env.user:
            return False
        vals = {
            'message': _('Login Successful'),
            'cashier': _('Employee: ') + card.employee_id.name
        }
#         request.session.check_user_scanned = True
        self.env.user.with_user(SUPERUSER_ID).logged_in = True
        return vals
    
    def confirm_cancel(self):
        request.session.logout(keep_db=True)
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/web/login'
        }
