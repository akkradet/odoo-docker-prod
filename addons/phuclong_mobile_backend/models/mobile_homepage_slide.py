# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class MobileHomepageSlide(models.Model):
    _name = 'mobile.homepage.slide'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Slide Banner'
    _order = 'sequence desc'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(string="sequence")
    is_published = fields.Boolean('Is Published', copy=False, default=False)
    image = fields.Binary("Image", required=True)
    deeplink = fields.Char(string="Deep Link")
    active = fields.Boolean(string="Active", default=True)
    new_id = fields.Many2one('show.case', 'New')

    def action_published(self):
        if self.is_published:
            self.is_published = False
        else:
            self.is_published = True

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self._context.get('api', False):
            args += [('is_published', '=', True)]
        return super(MobileHomepageSlide, self).search(args, offset, limit, order, count=count)