from werkzeug.contrib.cache import SimpleCache, RedisCache
import hashlib
import json
"""Common methods"""
import ast
import logging

import werkzeug.wrappers

from odoo.http import request
from datetime import date, datetime, timezone, timedelta
from odoo.loglevels import ustr

_logger = logging.getLogger(__name__)
try:
    cache = RedisCache()
except Exception as e:
    cache = SimpleCache()
    _logger.info('Simple Caching')

def md5(value):
    return hashlib.md5(value.encode('utf-8')).hexdigest()


def get_key():
    return md5(request.httprequest.full_path)


def get_cache():
    key = get_key()
    if cache.has(key):
        try:
            return cache.get(key)
        except Exception as e:
            pass
    return False


def set_cache(data, timeout):
    try:
        key = get_key()
        cache.set(key, data, timeout)
    except Exception as e:
        pass


def convert_datetime_to_json(obj):
    if isinstance(obj, date):
        if isinstance(obj, datetime):
            return obj.astimezone(timezone.utc).isoformat()
        return obj.isoformat()
    return ustr(obj)


def valid_response(data, status=200, has_cache=True, timeout=60):
    """Valid Response
    This will be return when the http request was successfully processed."""
    data_response = {
        "count": len(data),
        "data": data,
        "status": status
    }
    if has_cache:
        set_cache(data, timeout)
    if request.env.user.use_for_website:
        request.env['api.history'].create({
            'name': request.httprequest.method + ' ' + request.httprequest.base_url,
            'time_call': datetime.now(),
            'request_params': str(request.env.user._context.get('payload', '')),
            'message_err': str(data_response)
        })
    return werkzeug.wrappers.Response(
        status=status,
        content_type="application/json; charset=utf-8",
        response=json.dumps(data_response, default=convert_datetime_to_json),
    )


def invalid_response(typ, message=None, status=401):
    """Invalid Response
    This will be the return value whenever the server runs into an error
    either from the client or the server."""
    if request.env.user.use_for_website:
        request.env['api.history'].create({
            'name': request.httprequest.method + ' ' + request.httprequest.base_url,
            'time_call': datetime.now(),
            'request_params': str(request.env.user._context.get('payload', '')),
            'message_err': str(message)
            if str(message)
            else "wrong arguments (missing validation)"
        })
    return werkzeug.wrappers.Response(
        status=200,
        content_type="application/json; charset=utf-8",
        response=json.dumps(
            {
                "data": {
                    "type": typ,
                    "message": str(message)
                    if str(message)
                    else "wrong arguments (missing validation)",
                },
                'status': status
            }
        ),
    )


def extract_arguments(payload={}, offset=0, limit=0, order=None):
    """."""
    request.env.user = request.env.user.with_context(payload=payload)
    fields, domain = ['id', 'display_name'], []
    if payload.get("domain"):
        try:
            domain = json.loads(payload.get("domain"))
        except Exception as e:
            domain = []
            _logger.info(e)
            pass
    if payload.get("fields"):
        try:
            fields = payload.get("fields").split(',')
        except Exception as e:
            fields = ['id', 'display_name']
            _logger.info(e)
            pass
    if payload.get("offset"):
        offset = int(payload["offset"])
    if payload.get("limit"):
        limit = int(payload.get("limit"))
    if payload.get("order"):
        order = payload.get("order")
    return [domain, fields, offset, limit, order]
