# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError
from lxml import etree
import base64, xlrd

class WizardClearUserSession(models.TransientModel):
    _name = "wizard.clear.user.session"
    _description = 'WizardClearUserSession'

    user_id = fields.Many2one('res.users', string="User", required=True)
    
    def clear_user_session(self):
        self.sudo().user_id.validate_sessions()
        self.env['clear.user.session.history'].create({'user_id': self.user_id.id})
        
    def fields_view_get(
            self, view_id=None, view_type=False,
            toolbar=False, submenu=False):
        res = super(WizardClearUserSession, self).fields_view_get(
            view_id=view_id, view_type=view_type,
            toolbar=toolbar, submenu=submenu)
        if view_type in 'form':
            user_with_config = self.with_user(SUPERUSER_ID).env['res.users'].search([('pos_config', '!=', False)])
            if len(user_with_config):
                warehouses = self.env.user._warehouses_domain()
                if warehouses:
                    user_to_clear_session = user_with_config.filtered(lambda l: l.pos_config.warehouse_id.id in warehouses)
                else:
                    user_to_clear_session = user_with_config
            
            if user_to_clear_session:
                doc = etree.XML(res['arch'])
                for node in doc.xpath("//field[@name='user_id']"):
                    node.set('domain', "[('id','in',%s)]"%(user_to_clear_session.ids))
                    res['arch'] = etree.tostring(doc)
        return res

class ClearUserSessionHistory(models.Model):
    _name = "clear.user.session.history"
    _description = 'ClearUserSessionHistory'
    
    user_id = fields.Many2one('res.users', string="User", readonly=True)
