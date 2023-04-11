# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class wizardPosCashierScanner(models.TransientModel):
    _name = "wizard.pos.cashier.scanner"
    _inherit = 'barcodes.barcode_events_mixin'

    session_id = fields.Many2one('pos.session', 'Session')
    cashier_barcode = fields.Char('Cashier Code')

    @api.model
    def do_barcode_scan(self, barcode, session_id):
        if not barcode:
            raise UserError('Invalid Barcode')
        if not session_id:
            raise UserError('Invalid Session')
        session = self.env['pos.session'].sudo().search([
            ('id', '=', session_id)
        ])
        # Search barcode:
        card = self.env['cardcode.info'].sudo().search([
            ('hidden_code', '=', barcode),
            ('card_type', '=', 'employee'),
            ('state', '=', 'using'),
            ('employee_id.use_for_employee_coupon', '!=', True)
        ], limit=1)
        if not card:
            raise UserError(_('The employee card code does not exist'))
        else:
            employee_id = card.employee_id.id
            session_with_cashier_opening = self.env['pos.session'].search([('id','!=', session.id),('state', '!=', 'closed'),('cashier_id', '=', employee_id)], limit=1)
            if session_with_cashier_opening:
                raise UserError(_('Cashier has an opening session: %s, please close it before change session')%(session_with_cashier_opening.name))
            session.sudo().write({
                'cashier_id': employee_id
            })
#             session.open_session()
        vals = {
            'message': 'Mở ca thành công',
            'cashier': 'Nhân viên: %s' % (card.employee_id.name)
        }
        return vals
