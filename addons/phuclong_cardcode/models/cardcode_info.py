# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import Warning, ValidationError, UserError


class CardcodeInfo(models.Model):
    _name = 'cardcode.info'
    _description = 'Cardcode Info'
    _rec_name = 'appear_code'
    _order = 'id desc'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    publish_id = fields.Many2one('cardcode.publish', string='Publish Cardcode', readonly=True, required=True,
                                 ondelete='cascade')
    hidden_code = fields.Char(string="Hidden Code", required=True)
    appear_code = fields.Char(string="Appear Code", required=True)
    size_appear_code = fields.Integer(
        compute='_compute_size_appear_code', store=True)

    @api.depends('appear_code')
    def _compute_size_appear_code(self):
        for rec in self:
            rec.size_appear_code = rec.appear_code and len(
                rec.appear_code) or 0

    card_type = fields.Selection(
        related='publish_id.card_type', string="Card Type", store=True, readonly=True)
    publish_date = fields.Date(
        related='publish_id.publish_date', string="Date Publish", store=True, readonly=True)
    state = fields.Selection([('create', 'Create'),
                              ('using', 'Using'),
                              ('close', 'Close'),
                              ('cancel', 'Cancel')
                              ], string='State', default='create')
    employee_id = fields.Many2one('hr.employee', string='Employee',)
    partner_id = fields.Many2one('res.partner', string='Customer',)
    date_expired = fields.Date(string="Expired Date",)
    date_created = fields.Date(string="Date",)
    order_reference = fields.Char()

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    def unlink(self):
        # Add code here
        if any(c.state not in ['create', 'close'] or c.employee_id or c.partner_id for c in self):
            raise UserError(_("You are not allowed to delete this record"))
        return super(CardcodeInfo, self).unlink()

    @api.constrains('date_created', 'date_expired')
    def _check_date_created_date_expired(self):
        for rec in self:
            if rec.date_created and rec.date_expired and rec.date_created > rec.date_expired:
                raise ValidationError(
                    _("Expire date must be greater than or equal to effective date"))

    def name_get(self):
        res = []
        for cardcode in self:
            name = cardcode.sudo().appear_code or cardcode.sudo().hidden_code or ''
            res.append((cardcode.id, name))
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            if not self._context.get('search_appear_code', False):
                domain = ['|', '|', ('hidden_code', operator, name), ('appear_code', operator, name),
                          ('publish_id', operator, name)]
            else:
                domain = [('appear_code', operator, name)]
        return self.search(domain + args, limit=limit).name_get()

    def update_state(self):
        for cardcode in self:
            if cardcode.state == 'using':
                raise Warning(
                    _("You cannot cancel this card code publish because the card code is using"))
            sql = '''
                UPDATE cardcode_info SET state = 'cancel' WHERE id = %s
            ''' % (cardcode.id)
            self._cr.execute(sql)
        return True

    def _check_cardcode(self):
        for cardcode in self:
            domain = ['|', ('hidden_code', '=', cardcode.hidden_code),
                      ('appear_code', '=', cardcode.appear_code)
                      ]
            count = self.search_count(domain)
            if count > 1:
                return False
        return True

    _constraints = [
        (_check_cardcode, _("You cannot create two Cardcode with same Appear/Hidden!"),
         ['appear_code', 'hidden_code']),
    ]
