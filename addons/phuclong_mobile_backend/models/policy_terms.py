from odoo import models, fields, api, _

class PolicyTerms(models.Model):
    _name = 'policy.terms'

    _description = 'Policy and Terms'

    name = fields.Char(string="Policy name")
    url = fields.Char(string="URL")
    priority = fields.Char(string="Priority")
    hide = fields.Boolean(string="Hide")