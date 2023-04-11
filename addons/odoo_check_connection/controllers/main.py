# -*- coding: utf-8 -*-
from odoo.http import Controller, request, route

class CheckConnection(Controller):

    @route(['/ping'], type='http', auth='public', website=False)
    def check_connection(self, **post):
        return request.make_response('PONG')