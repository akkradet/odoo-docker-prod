# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Model(models.Model):
    _inherit = 'ir.model'

    group_unlink_ids = fields.Many2many(
        'res.groups', 'ir_model_group_unlink_rel', 'mid', 'guid', string='Group Unlink')
    user_unlink_ids = fields.Many2many(
        'res.users', 'ir_model_user_unlink_rel', 'mid', 'uid', string='User Unlink')
