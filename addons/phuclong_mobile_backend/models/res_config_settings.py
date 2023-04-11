from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    maximum_km = fields.Char('Maximum KM delivery', default=3, required=True)
    prefix_birthday = fields.Char(
        'Prefix Birthday', default='', required=False)
    prefix_reward = fields.Char('Prefix Reward', default='', required=False)
    code_size = fields.Char('Code Size', default="6", required=True)
    alphabet = fields.Char('Alphabet', default="0", required=True)
    stand = fields.Char('Stand', default="0", required=True)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        res.update(maximum_km=ICPSudo.get_param(
            'phuclong_mobile_backend.maximum_km', default="3"))
        res.update(prefix_birthday=ICPSudo.get_param(
            'phuclong_mobile_backend.prefix_birthday', default=''))
        res.update(prefix_reward=ICPSudo.get_param(
            'phuclong_mobile_backend.prefix_reward', default=''))
        res.update(code_size=ICPSudo.get_param(
            'phuclong_mobile_backend.code_size', default="6"))
        res.update(alphabet=ICPSudo.get_param(
            'phuclong_mobile_backend.alphabet', default="0"))
        res.update(stand=ICPSudo.get_param(
            'phuclong_mobile_backend.stand', default="0"))
        return res

    @api.model
    def set_values(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        ICPSudo.set_param(
            "phuclong_mobile_backend.maximum_km", self.maximum_km)
        ICPSudo.set_param(
            "phuclong_mobile_backend.prefix_birthday", self.prefix_birthday or '')
        ICPSudo.set_param(
            "phuclong_mobile_backend.prefix_reward", self.prefix_reward or '')
        ICPSudo.set_param("phuclong_mobile_backend.code_size",
                          self.code_size or '6')
        ICPSudo.set_param("phuclong_mobile_backend.alphabet",
                          self.alphabet or '0')
        ICPSudo.set_param("phuclong_mobile_backend.stand", self.stand or '0')
        super(ResConfigSettings, self).set_values()
