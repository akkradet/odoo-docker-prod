from odoo.http import request
from odoo import http, SUPERUSER_ID
import requests
from odoo.addons.phuclong_restful_api.controllers.main import APIController, _routes
from odoo.addons.phuclong_restful_api.common import invalid_response, valid_response, md5, get_cache
from odoo.addons.phuclong_restful_api.models.access_token import check_token, create_token
from odoo.addons.web.controllers.main import Binary
from datetime import date, datetime, timedelta
import json
import math
import xmltodict
import hashlib
import logging
import base64
import random

_logger = logging.getLogger(__name__)


class PhucLongAPPController(http.Controller):

    @http.route('/api/v1/notification', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def notification(self, **payload):
        partner_id = int(payload.get('partner_id', 0))
        noti_id = int(payload.get('id', 0))
        action = payload.get('action', 'read')
        limit = int(payload.get('limit', 0))
        page = int(payload.get('page', 0))
        offset = 0
        if page > 0:
            if limit == 0:
                limit = 20
            offset = (page - 1) * limit
        else:
            offset = 0
            limit = None
        if partner_id:
            if action == 'read_all':
                return valid_response(request.env['mobile.notification'].sudo()._read_all_notification(partner_id))
            if not noti_id:
                return valid_response(request.env['mobile.notification'].sudo()._get_notifications_by_partner(partner_id, limit, offset))
            else:
                action = payload.get('action', 'read')
                if action == 'delete':
                    return valid_response(request.env['mobile.notification'].sudo().browse(noti_id)._delete_notification(partner_id))
                return valid_response(request.env['mobile.notification'].sudo().browse(noti_id)._read_notification(partner_id))
        return invalid_response('Error', 'Partner_id not exists')
