# -*- coding: utf-8 -*-
from odoo import models, api, SUPERUSER_ID
from odoo.http import request
from datetime import datetime, timedelta

class ResUsers(models.Model):
    _inherit = 'res.users'
    
    def check_to_clear_session(self):
        check_clear = self.access_multi_sessions()
#         check_login = request.session.context.get('login', False)
        check_login = self.context_login
        if check_clear and not self.context_login:
#             self.context_get.clear_cache(self)
            self.with_user(SUPERUSER_ID).write({'context_login':True})
#             self.context_get()
        return (check_clear and check_login) and True or False

    def access_multi_sessions(self):
        return self.pos_config and True or False

#     def clear_session(self):
#         """
#             Function for clearing the session details for user
#         """
#         self.with_user(SUPERUSER_ID).write({'sid': False, 'exp_date': False, 'logged_in': False, 'context_login': False,
#                     'last_update': datetime.now()})
#         request.session.logout()
