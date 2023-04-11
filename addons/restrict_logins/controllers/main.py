# -*- coding: utf-8 -*-
import os

import werkzeug
import werkzeug.contrib.sessions
import werkzeug.datastructures
import werkzeug.exceptions
import werkzeug.local
import werkzeug.routing
import werkzeug.wrappers
import werkzeug.wsgi
from odoo.addons.web.controllers import main

import odoo
import odoo.modules.registry
from odoo import SUPERUSER_ID
from odoo import http
from odoo.exceptions import AccessError
from odoo.http import Response
from odoo.http import request
from odoo.service import security
from odoo.tools.translate import _


def clear_session_history(u_sid, f_uid=False):
    """ Clear all the user session histories for a particular user """
    path = odoo.tools.config.session_dir
    store = werkzeug.contrib.sessions.FilesystemSessionStore(
        path, session_class=odoo.http.OpenERPSession, renew_missing=True)
    session_fname = store.get_session_filename(u_sid)
    try:
        os.remove(session_fname)
        return True
    except OSError:
        pass
    return False


def super_clear_all():
    """ Clear all the user session histories """
    path = odoo.tools.config.session_dir
    store = werkzeug.contrib.sessions.FilesystemSessionStore(
        path, session_class=odoo.http.OpenERPSession, renew_missing=True)
    for fname in os.listdir(store.path):
        path = os.path.join(store.path, fname)
        try:
            os.unlink(path)
        except OSError:
            pass
    return True


class Session(main.Session):
    
    @http.route('/web/session/logout', type='http', auth="none")
    def logout(self, redirect='/web'):
        user = request.env['res.users'].with_user(1).search(
            [('id', '=', request.session.uid)])
        # clear user session
#         clear_session_history(user.sid, user.id)
        user._clear_session()
        request.session.logout(keep_db=True)
        return werkzeug.utils.redirect(redirect, 303)

    @http.route('/clear_all_sessions', type='http', auth="none")
    def logout_all(self, redirect='/web', f_uid=False):
        """ Log out from all the sessions of the current user """
        if f_uid:
            user = request.env['res.users'].with_user(1).browse(int(f_uid))
            if user:
                # clear session session file for the user
                session_cleared = clear_session_history(user.sid, f_uid)
                user._clear_session()
#                 if session_cleared:
                    # clear user session
#                     user._clear_session()
        request.session.logout(keep_db=True)
        return werkzeug.utils.redirect(redirect, 303)

    @http.route('/super/logout_all', type='http', auth="none")
    def super_logout_all(self, redirect='/web'):
        """ Log out from all the sessions of all the users """
        users = request.env['res.users'].with_user(1).search([])
        for user in users:
            # clear session session file for the user
            session_cleared = super_clear_all()
            if session_cleared:
                # clear user session
                user._clear_session()
        request.session.logout(keep_db=True)
        return werkzeug.utils.redirect(redirect, 303)


class Home(main.Home):

    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        main.ensure_db()
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return http.redirect_with_hash(redirect)

        if not request.uid:
            request.uid = odoo.SUPERUSER_ID

        values = request.params.copy()
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            old_uid = request.uid
            try:
                uid = request.session.authenticate(request.session.db,
                                                   request.params['login'],
                                                   request.params['password'])
                request.params['login_success'] = True
                return http.redirect_with_hash(
                    self._login_redirect(uid, redirect=redirect))
            except odoo.exceptions.AccessDenied as e:
                failed_uid = request.uid
                request.uid = old_uid
                if e.args == odoo.exceptions.AccessDenied().args:
                    values['error'] = _("Wrong login/password")
                elif e.args[0] == "already_logged_in":
                    values['error'] = "Tài khoản đã được đăng nhập. Vui lòng đăng xuất khỏi các thiết bị khác và thử lại."
                    values['logout_all'] = True
                    values[
                        'failed_uid'] = failed_uid if failed_uid != SUPERUSER_ID else False
                elif e.args[0] == "invalid_ip_login":
                    values['error'] = "Tài khoản đang đăng nhập sai máy hoặc sai cửa hàng"
                    values['logout_all'] = True
                    values[
                        'failed_uid'] = failed_uid if failed_uid != SUPERUSER_ID else False
                else:
                    values['error'] = e.args[0]
        else:
            if 'error' in request.params and request.params.get(
                    'error') == 'access':
                values['error'] = _('Only employee can access this database. '
                                    'Please contact the administrator.')

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        if not odoo.tools.config['list_db']:
            values['disable_database_manager'] = True

        response = request.render('web.login', values)
        response.headers['X-Frame-Options'] = 'DENY'
        return response


# class RootExt(odoo.http.Root):
#
    # def get_response(self, httprequest, result, explicit_session):
        # if isinstance(result, Response) and result.is_qweb:
            # try:
                # result.flatten()
            # except Exception as e:
                # if request.db:
                    # result = request.registry['ir.http']._handle_exception(e)
                # else:
                    # raise
                    #
        # if isinstance(result, (bytes, str)):
            # response = Response(result, mimetype='text/html')
        # else:
            # response = result
            #
        # save_session = (not request.endpoint) or request.endpoint.routing.get(
            # 'save_session', True)
        # if not save_session:
            # return response
            #
        # if httprequest.session.should_save:
            # if httprequest.session.rotate:
                # self.session_store.delete(httprequest.session)
                # httprequest.session.sid = self.session_store.generate_key()
                # if httprequest.session.uid:
                    # httprequest.session.session_token = security.compute_session_token(
                        # httprequest.session, request.env)
                # httprequest.session.modified = True
            # self.session_store.save(httprequest.session)
        # # We must not set the cookie if the session id was specified using a http header or a GET parameter.
        # # There are two reasons to this:
        # # - When using one of those two means we consider that we are overriding the cookie, which means creating a new
        # #   session on top of an already existing session and we don't want to create a mess with the 'normal' session
        # #   (the one using the cookie). That is a special feature of the Session Javascript class.
        # # - It could allow session fixation attacks.
        # if not explicit_session and hasattr(response, 'set_cookie'):
            # response.set_cookie('session_id', httprequest.session.sid,
                                # max_age=90 * 24 * 60 * 60, httponly=True)
                                #
        # return response
        #
        #
# root = RootExt()
# odoo.http.Root.get_response = root.get_response
