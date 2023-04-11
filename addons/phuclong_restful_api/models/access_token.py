import hashlib
import logging
import os
import time
import math
import jwt

from datetime import datetime, timedelta
from odoo.http import request
from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

expires_in = "phuclong_restful_api.access_token_expires_in"
secret_key = "secret"

def create_token(uid):
    now = math.floor(time.mktime(datetime.now().timetuple()))
    header = {'cty': 'phuc_long'}
    exp = now + int(request.env.ref(expires_in).sudo().value)
    payload = {
        'jti': str(uid)+'-'+str(now),
        'iss': uid,
        'exp': exp,
        'rest_api': 1
    }
    token = jwt.encode(payload, secret_key, 'HS256', header)
    return token

def check_token(access_token):
    try:
        payload = jwt.decode(access_token, secret_key, algorithms=['HS256'])
        if  payload and payload.get('iss', False):
            return True, payload['iss']
        else:
            return False, "token seems to invalid"
    except Exception as e:
        return False , e