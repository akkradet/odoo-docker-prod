# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta

import werkzeug
import werkzeug.exceptions
import werkzeug.routing
import werkzeug.urls
import werkzeug.utils

from odoo import models, http, SUPERUSER_ID
from odoo.exceptions import AccessDenied
from odoo.http import request

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

#     @classmethod
#     def _authenticate(cls, auth_method='user'):
#         try:
#             if request.session.uid:
#                 uid = request.session.uid
#                 user_pool = request.env['res.users'].with_user(
#                     SUPERUSER_ID).browse(uid)
#                     
#                 if user_pool.access_multi_sessions():
#                     def _update_user(u_sid, u_now, u_exp_date, u_uid):
#                         """ Function for updating session details for the
#                             corresponding user
#                         """
#                         if u_uid and u_exp_date and u_sid and u_now:
# #                             user_pool.context_get.clear_cache(user_pool)
#                             query = """update res_users set sid = '%s',
#                                            last_update = '%s',exp_date = '%s',
#                                            logged_in = 'TRUE'
#                                            where id = (
#                                                 SELECT id FROM res_users
#                                                 WHERE id = %s
#                                                 FOR UPDATE SKIP LOCKED
#                                             );
#                                            """ % (u_sid, u_now, u_exp_date, u_uid)
#                             request.env.cr.execute(query)
# #                             user_pool.context_get()
#     
#                     sid = request.session.sid
#                     last_update = user_pool.last_update
#                     now = datetime.now()
#                     exp_date = datetime.now() + timedelta(days=365)
#                     # check that the authentication contains bus_inactivity
#                     request_params = request.params.copy()
#                     if 'options' in request_params and 'bus_inactivity' in \
#                             request_params['options']:
#                         # update session if there is sid mismatch
#                         if uid and user_pool.sid and sid != user_pool.sid:
#                             _update_user(sid, now, exp_date, uid)
#                     else:
#                         # update if there is no session data and user is active
#                         if not user_pool.last_update and not user_pool.sid and \
#                                 not user_pool.logged_in:
#                             _update_user(sid, now, exp_date, uid)
#                         # update sid and date if last update is above 0.5 min
#                         if last_update:
#                             update_diff = (datetime.now() -
#                                            last_update).total_seconds() / 60.0
#                             if uid and user_pool.sid and (update_diff > 0.5 or sid != user_pool.sid):
#                                 _update_user(sid, now, exp_date, uid)
#         except Exception as e:
#             _logger.info("Exception during updating user session...%s", e)
#             pass
#         try:
#             if request.session.uid:
#                 try:
#                     request.session.check_security()
#                     # what if error in security.check()
#                     #   -> res_users.check()
#                     #   -> res_users._check_credentials()
#                 except (AccessDenied, http.SessionExpiredException):
#                     # All other exceptions mean undetermined status (e.g. connection pool full),
#                     # let them bubble up
#                     user_pool = request.env['res.users'].with_user(
#                         SUPERUSER_ID).browse(request.session.uid)
#                     user_pool._clear_session()
#                     request.session.logout(keep_db=True)
#             if request.uid is None:
#                 getattr(cls, "_auth_method_%s" % auth_method)()
#         except (AccessDenied, http.SessionExpiredException,
#                 werkzeug.exceptions.HTTPException):
#             raise
#         except Exception:
#             _logger.info("Exception during request Authentication.",
#                          exc_info=True)
#             raise AccessDenied()
#         return auth_method
