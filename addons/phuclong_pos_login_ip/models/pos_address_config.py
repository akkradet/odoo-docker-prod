# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class PosAddressConfig(models.Model):
    _name = 'pos.address.config'
    _description = 'PosAddressConfig'

    name = fields.Char('Name', compute='_compute_complete_name', readonly=True, store=True)
    config_id = fields.Many2one('pos.config', string="POS Config", required=False, copy=False)
    ipaddress_ids = fields.One2many(
        'pos.ip.address',
        'config_id',
        string='IP Addresses', copy=False)

    @api.depends('config_id')
    def _compute_complete_name(self):
        for config in self:
            if config.config_id:
                config.name = 'Địa chỉ đăng nhập POS: %s' % (config.config_id.name)
            else:
                config.name = False

    @api.onchange('config_id')
    def set_domain_depend_on_config_id(self):
        domain = []
        configs = self.search([])
        if configs:
            config_ids = configs.mapped('config_id').ids
            domain = [('id', 'not in', config_ids)]
        return {'domain': {'config_id': domain}}
    
class PosIPAddress(models.Model):
    _name = 'pos.ip.address'
    _description = 'PosIPAddress'

    name = fields.Char('MAC Address', required=True)
    public_ip = fields.Char('Public IP', required=False)
    config_id = fields.Many2one('pos.address.config', readonly=True, ondelete="cascade")
    
class ResUsers(models.Model):
    _inherit = 'res.users'
    
    def check_valid_ip_login(self, mac_address):
        if self.pos_config:
            config_available = self.env['pos.ip.address'].search([('config_id.config_id', '=', self.pos_config.id)])
            if len(config_available):
                if mac_address:
                    mac_address = mac_address.replace('-','')
                    config_mapped = config_available.filtered(lambda l: l.name.replace('-','') == mac_address)
                    if not len(config_mapped):
                        return False
                else:
                    return False
        return True
