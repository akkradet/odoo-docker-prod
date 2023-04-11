# -*- coding: utf-8 -*-
from odoo.addons.web.controllers import main
import odoo
from odoo import SUPERUSER_ID
from odoo import http
from odoo.http import Response
from odoo.http import request

class Session(main.Session):
    
    @http.route('/web/session/destroy', type='json', auth="user")
    def destroy(self):
        user = request.env['res.users'].with_user(1).search(
            [('id', '=', request.session.uid)])
        # clear user session
        user._clear_session()
        request.session.logout()
        
    




