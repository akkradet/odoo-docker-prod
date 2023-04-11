from odoo import models, fields, api, _

class ConfigurationLogin(models.Model):
    _name = 'configuration.login'

    _description = 'Configuration Login'

    name = fields.Char(string="Name")
    active = fields.Boolean(default=True)
    code = fields.Char('Code')

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if not self._context.get('api', False):
            args += [('code', '!=', 'SMS')]
        return super(ConfigurationLogin, self).search(args, offset, limit, order, count)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if not self._context.get('api', False):
            domain += [('code', '!=', 'SMS')]
        return super(ConfigurationLogin, self).search_read(domain, fields, offset, limit, order)