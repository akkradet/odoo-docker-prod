# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta
import urllib.request
import json

from odoo import SUPERUSER_ID
from odoo import fields, api
from odoo import models
from odoo.exceptions import AccessDenied
from odoo.http import request
from ..controllers.main import clear_session_history

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    sid = fields.Char('Session ID')
    exp_date = fields.Datetime('Expiry Date')
    logged_in = fields.Boolean('Logged In')
    last_update = fields.Datetime(string="Last Connection Updated")
    context_login = fields.Boolean(string='Context Logged In', readonly=True)
    
    def access_multi_sessions(self):
        return False
    
    def check_valid_ip_login(self, mac_address):
        return True

    @classmethod
    def _login(cls, db, login, password):
        if not password:
            raise AccessDenied()
        ip = request.httprequest.environ['REMOTE_ADDR'] if request else 'n/a'
#         _logger.info('----request info: %s', request.httprequest.environ)
#         real_ip = request.httprequest.environ['HTTP_X_REAL_IP'] if request else 'n/a'
        public_ip = False
        mac_address = False
        if request.httprequest.environ.get('HTTP_X_FORWARDED_FOR') is None:
            public_ip = request.httprequest.environ['REMOTE_ADDR']
        else:
            public_ip = request.httprequest.environ['HTTP_X_FORWARDED_FOR']
        
        try:
            with cls.pool.cursor() as cr:
                self = api.Environment(cr, SUPERUSER_ID, {})[cls._name]
                with self._assert_can_auth():
                    user = self.search(self._get_login_domain(login))
                    if not user:
                        raise AccessDenied()
                    user = user.with_user(user)
                    user._check_credentials(password)
                    # check sid and exp date
                    if user.exp_date and user.sid and user.logged_in and user.access_multi_sessions():
                        _logger.warning("User %s is already logged in "
                                        "into the system!. Multiple "
                                        "sessions are not allowed for "
                                        "security reasons!" % user.name)
                        request.uid = user.id
                        raise AccessDenied("already_logged_in")
                    
                    login_param = request.params.copy()
                    if 'mac_address' in login_param and login_param['mac_address']:
                        mac_address = login_param['mac_address']
                    if not user.check_valid_ip_login(mac_address):
                        raise AccessDenied("invalid_ip_login")
                    # save user session detail if login success
                    user._save_session()
                    user._update_last_login()
        except AccessDenied:
            _logger.info("Login failed for db:%s login:%s from %s", db, login,
                         ip)
            raise
        _logger.info("Login successful for db:%s login:%s from %s", db, login,
                     ip)
        return user.id

    def _clear_session(self):
        """
            Function for clearing the session details for user
        """
        self.with_user(SUPERUSER_ID).write({'sid': False, 'exp_date': False, 'logged_in': False, 'context_login': False,
                    'last_update': datetime.now()})

    def _save_session(self):
        """
            Function for saving session details to corresponding user
        """
        exp_date = datetime.utcnow() + timedelta(days=365)
        sid = request.httprequest.session.sid
#         self.context_get.clear_cache(self)
        self.with_user(SUPERUSER_ID).write({'sid': sid, 'exp_date': exp_date,
                                            'logged_in': True,
                                            'last_update': datetime.now()})

    def validate_sessions(self):
        """
            Function for validating user sessions
        """
#         users = self.search([('exp_date', '!=', False)])
        for user in self:
#             if user.exp_date < datetime.utcnow():
                # clear session session file for the user
            session_cleared = clear_session_history(user.sid)
            user._clear_session()
            if session_cleared:
                # clear user session
#                 user._clear_session()
                _logger.info("Cron _validate_session: "
                             "cleared session user: %s" % (user.name))
            else:
                _logger.info("Cron _validate_session: failed to "
                             "clear session user: %s" % (user.name))
