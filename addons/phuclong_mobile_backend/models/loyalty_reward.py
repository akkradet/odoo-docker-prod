# -*- coding: utf-8 -*-

from odoo import api, fields, models


class LoyaltyReward(models.Model):
    _name = 'loyalty.reward'
    _inherit = ['loyalty.reward', 'image.mixin']

    def _prepair_url_image(self, base_url=False, field='image_1920'):
        self.ensure_one()
        if not base_url:
            base_url = self.env['ir.config_parameter'].sudo(
            ).get_param('web.base.url')
        return '%s/web/image/%s/%s/%s' % (base_url, self._name, self.id, field)

    content = fields.Html(string='Content', default='')
    contact = fields.Html(string='Contact', default='')
    
