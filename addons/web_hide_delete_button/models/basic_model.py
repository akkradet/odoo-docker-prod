# -*- coding: utf-8 -*-
from odoo import http, models, fields, api, _


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def check_unlink(self):
        user = self.env.user
        if user.has_group('base.group_system'):
            return True
        model_id = self.env['ir.model'].sudo().search(
            [('model', '=', self._name)], limit=1)
        if model_id:
            if model_id.sudo().user_unlink_ids and user.id in model_id.sudo().user_unlink_ids.ids:
                return True
            if model_id.sudo().group_unlink_ids:
                group_ids = user.groups_id.ids
                if any(gid in group_ids for gid in model_id.sudo().group_unlink_ids.ids):
                    return True
        return False
