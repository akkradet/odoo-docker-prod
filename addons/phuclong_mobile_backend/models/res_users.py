from odoo import models, fields, api, _

class ResUser(models.Model):
    _inherit = 'res.users'

    use_for_website = fields.Boolean('User for Website', default=False)