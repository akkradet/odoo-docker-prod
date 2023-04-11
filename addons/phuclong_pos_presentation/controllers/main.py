# -*- coding: utf-8 -*-
import logging
import odoo
from odoo import http, models, fields, api, _
from odoo.http import request
from odoo.addons.portal.controllers.web import Home
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class Web(Home):

    @http.route(
        '/web/presentation/receiver',
        type='http', auth="public", sitemap=False)
    def presentation(self, **kwargs):
        now = datetime.now()
        config_id = kwargs and kwargs.get('config', False)
        warehouse = config_id and request.env['pos.config'].sudo().search(
            [('id', '=', int(config_id))]).warehouse_id
        banner = []
        if warehouse:
            banner = request.env['pos.banner.config'].sudo().search([
                ('warehouse_ids', 'in', [warehouse.id]),
                ('active', '=', True),
                ('start_date', '<=', now),
                ('end_date', '>=', now),
            ], order='start_date')
        return request.render('phuclong_pos_presentation.presentation_receiver', {
            'banners': banner,
            'banners_len': len(banner)
        })
