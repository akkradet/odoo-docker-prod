# -*- coding: utf-8 -*-
import logging
import odoo
from odoo import http, models, fields, api, _, SUPERUSER_ID
from odoo.http import request
from odoo.addons.portal.controllers.web import Home

logger = logging.getLogger(__name__)

class Web(Home):

    @http.route(website=True, auth="public", sitemap=False)
    def web_login(self, redirect=None, *args, **kw):
        response = super(Web, self).web_login(redirect=redirect, *args, **kw)
        if not redirect and request.params['login_success']:
            if request.env['res.users'].browse(request.session.uid).required_emp_card:
                action = request.env.ref('phuclong_pos_theme.action_wizard_login_scanner_wizard')
                if action:
                    request.session.required_barcode_scan = True
                    redirect_string = '/web?#action=%s'%(action.id)
                    redirect = bytes(redirect_string, 'utf-8') + request.httprequest.query_string
            if not redirect:
                redirect = b'/web' + request.httprequest.query_string
            return http.redirect_with_hash(redirect)
        return response


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def load_views(self, views, options=None):
        user_id = request.env['res.users'].browse(request.session.uid)
        if user_id.required_emp_card:
            if request.session.required_barcode_scan:
                request.session.required_barcode_scan = False
                user_id.with_user(SUPERUSER_ID).logged_in = False
            else:
#                 if not request.session.check_user_scanned:
                if not user_id.logged_in:
                    request.session.logout(keep_db=True)
#                     return
        return super(BaseModel, self).load_views(views, options)
