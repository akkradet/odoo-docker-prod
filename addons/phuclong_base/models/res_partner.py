# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class Partner(models.Model):
    _inherit = "res.partner"

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        args = args or []
        context = self._context or {}
        if context.get('hide_main_user'):
            users_main = self.env['res.users']._get_main_user(user_admin=True)
            if users_main:
                args += [('id', 'not in', users_main.mapped('partner_id').ids)]
        return super(Partner, self).search(args, offset, limit, order, count=count)
    
    def toggle_active(self):
        for partner in self:
            if partner.active and any(partner.user_ids.filtered(lambda u: u.active)):
                raise UserError(_('You cannot archive this partner since his related user is still active.'))
            partner.active = not partner.active
        return True
