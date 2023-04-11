from odoo import models, fields, api, _
from odoo.exceptions import UserError


class RequestUpdateCard(models.Model):
    _name = 'request.update.card'

    _description = 'Request Update Card'

    name = fields.Char(string="Ref")
    partner_id = fields.Many2one('res.partner', string="Customer")
    appear_code = fields.Char(string="Appear Code")
    mobile_old = fields.Char(string="Mobile Old")
    mobile = fields.Char(string="", related='partner_id.mobile')
    state = fields.Selection([
        ('new', 'New'),
        ('confirm', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancel')
    ], default='new')
    issue_id = fields.Many2one('config.issue', 'Issue')
    description = fields.Text()

    @api.model
    def create(self, vals):
        partner_id = self.env['res.partner'].sudo().search(
            [('id', '=', int(vals.get('partner_id', False)))], limit=1)
        if 'name' not in vals:
            if partner_id:
                vals['name'] = partner_id.name
        if not partner_id:
            raise UserError(_('Partner not exist!'))
        return super(RequestUpdateCard, self).create(vals)

    def action_done(self):
        self.write({'state': 'done'})

    def action_confirm(self):
        self.write({'state': 'confirm'})

    def action_cancel(self):
        self.write({'state': 'cancel'})
