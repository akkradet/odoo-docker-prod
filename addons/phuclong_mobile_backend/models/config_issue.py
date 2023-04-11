from odoo import models, fields, api, _


class ConfigIssue(models.Model):
    _name = 'config.issue'

    name = fields.Char('Name')
    description = fields.Text('Description')
