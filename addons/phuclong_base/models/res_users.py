# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class Users(models.Model):
    _inherit = "res.users"

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        args = args or []
        context = self._context or {}
        if context.get('hide_main_user'):
            users_main = self.env['res.users']._get_main_user(user_admin=True)
            if users_main:
                args += [('id', 'not in', users_main.ids)]
        return super(Users, self).search(args, offset, limit, order, count=count)
