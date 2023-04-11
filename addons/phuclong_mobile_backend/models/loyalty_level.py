# -*- coding: utf-8 -*-

from odoo import api, fields, models


class LoyaltyLevel(models.Model):
    _name = 'loyalty.level'
    _inherit = ['loyalty.level', 'image.mixin']

    def _prepair_url_image(self, base_url=False, field='image_1920'):
        self.ensure_one()
        if not base_url:
            base_url = self.env['ir.config_parameter'].sudo(
            ).get_param('web.base.url')
        return '%s/web/image/%s/%s/%s' % (base_url, self._name, self.id, field)

    content_birthday = fields.Html(string='Content', default='')
    contact_birthday = fields.Html(string='Contact', default='')
