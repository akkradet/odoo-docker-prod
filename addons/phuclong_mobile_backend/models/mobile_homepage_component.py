# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class MobileHomepageComponent(models.Model):
    _name = 'mobile.homepage.component'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Content Component'
    _order = 'sequence desc'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(string="sequence")
    is_published = fields.Boolean('Is Published', copy=False, default=False)
    post_ids = fields.Many2many('blog.post', string='Posts')

    def action_published(self):
        if self.is_published:
            self.is_published = False
        else:
            self.is_published = True
