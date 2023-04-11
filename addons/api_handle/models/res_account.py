from odoo import fields, models, api
from odoo.addons.phuclong_restful_api.common import invalid_response, valid_response
from odoo.addons.phuclong_restful_api.models.access_token import create_token, check_token
import json


class handleAccountResponse(models.Model):
    _inherit = 'res.partner'

    authorized = fields.Boolean(string="Register use App", default=False)
