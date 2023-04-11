from odoo import fields, api, _, models

class ConfigQandA(models.Model):
    _name = 'config.qanda'

    name = fields.Char('Name')
    url = fields.Char('URL')
    hide = fields.Boolean('Hide', default=False)