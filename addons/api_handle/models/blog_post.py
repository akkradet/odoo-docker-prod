from odoo import fields, models, api
from odoo.addons.phuclong_restful_api.common import invalid_response, valid_response
from odoo.addons.phuclong_restful_api.models.access_token import create_token, check_token
import json

class blogPostInherit(models.Model):
    _inherit = 'blog.post'

    url = fields.Char(compute='_depends_website_url')

    @api.depends('website_url')
    def _depends_website_url(self):
        self.url = self.env['ir.config_parameter'].get_param('web.base.url') + self.website_url