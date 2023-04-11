# -*- coding: utf-8 -*-
from odoo import models, api, SUPERUSER_ID

class ResUsers(models.Model):
    _inherit = 'res.users'
    
#     def access_multi_sessions(self):
#         return self.pos_config and True or False
        #Vuong disable for golive
#         return False

#     @api.model
#     def name_search(self, name, args=None, operator='ilike', limit=100):
#         args = args or []
#         context = self._context or {}
#         user_to_clear_session = []
#         if context.get('pos_user_store',False):
#             user_with_config = self.with_user(SUPERUSER_ID).env['res.users'].search([('pos_config', '!=', False)])
#             if len(user_with_config):
#                 warehouses = self.env.user._warehouses_domain()
#                 if warehouses:
#                     user_to_clear_session = user_with_config.filtered(lambda l: l.pos_config.warehouse_id.id in warehouses)
#                 else:
#                     user_to_clear_session = user_with_config
#                 if user_to_clear_session:
#                     args += [('id','in',user_to_clear_session.ids)]
#         return super(ResUsers, self).name_search(name, args, operator, limit)
#     
#     def search(self, args, offset=0, limit=None, order=None, count=False):
#         args = args or []
#         context = self._context or {}
#         user_to_clear_session = []
#         if context.get('pos_user_store',False):
#             self._cr.execute(''' select id from res_users where pos_config is not null and active = True''')
#             result = self._cr.fetchall()
#             user_with_config = self.with_user(SUPERUSER_ID).env['res.users'].browse(result)
#             if len(user_with_config):
#                 warehouses = self.env.user._warehouses_domain()
#                 if warehouses:
#                     user_to_clear_session = user_with_config.filtered(lambda l: l.pos_config.warehouse_id.id in warehouses)
#                 else:
#                     user_to_clear_session = user_with_config
#                 if user_to_clear_session:
#                     args += [('id','in',user_to_clear_session.ids)]
#         return super(ResUsers, self).search(args, offset, limit, order, count=count)
