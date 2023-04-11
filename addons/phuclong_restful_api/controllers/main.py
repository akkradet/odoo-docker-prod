"""Part of odoo. See LICENSE file for full copyright and licensing details."""

import functools
import logging
import json
from odoo import http
from odoo.addons.phuclong_restful_api.common import (
    extract_arguments,
    invalid_response,
    valid_response,
)
from odoo.http import request
from odoo.models import check_method_name
from odoo.api import _call_kw_model
from ..models.access_token import check_token
from odoo.exceptions import AccessError
from datetime import datetime, date

_logger = logging.getLogger(__name__)


def validate_token(func):
    """."""

    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        """."""
        access_token = request.httprequest.headers.get("access_token")
        if not access_token:
            return invalid_response(
                "access_token_not_found", "missing access token in request header", 401
            )
        token_checked_value, token_value = check_token(access_token)

        if token_checked_value:
            request.session.uid = token_value
            request.uid = token_value
            return func(self, *args, **kwargs)
        else:
            if token_value:
                return invalid_response(
                    "access_token", token_value, 201
                )
            else:
                return invalid_response(
                    "access_token", token_value, 202
                )

    return wrap


_routes = ["/api/v1/<model>", "/api/v1/<model>/<id>",
           "/api/v1/<model>/<id>/<action>"]


class APIController(http.Controller):
    """."""

    def __init__(self):
        self._model = "ir.model"

    @validate_token
    @http.route("/api/v1/call_kw_model/<model>/<action>", type="http", auth="none", methods=["GET", "POST"], csrf=False,
                cors="*", multilang=False)
    def _call_kw_model(self, model=None, action=None, **payload):
        """."""
        try:
            check_method_name(action)
            Model = request.env[model]
            method = getattr(type(Model), action)
            if method:
                args = [payload] if payload else {}
                return _call_kw_model(method, Model, args, {})
            else:
                return invalid_response(
                    "missing_method",
                    "%s object has no method %s"
                    % (model, action),
                    404,
                )
        except Exception as e:
            return invalid_response("Exception", e, 503)
        else:
            return valid_response({})

    @validate_token
    @http.route(_routes, type="http", auth="none", methods=["GET"], csrf=False, cors="*", multilang=False)
    def get(self, model=None, id=None, **payload):
        ioc_name = model
        model = request.env[self._model].sudo().search(
            [("model", "=", model)], limit=1)
        if model:
            domain, fields, offset, limit, order = extract_arguments(payload)
            if id:
                domain = [("id", "=", int(id))]
            try:
                data = (
                    request.env[model.model].with_context(api=True).search_read(
                        domain=domain,
                        fields=fields,
                        offset=offset,
                        limit=limit,
                        order=order,
                    )
                )
            except Exception as e:
                return invalid_response("Exception", e, 503)
            if data:
                return valid_response(data)
            else:
                return valid_response(data)
        return invalid_response(
            "invalid object model",
            "The model %s is not available in the registry." % ioc_name,
        )

    @validate_token
    @http.route(_routes, type="http", auth="none", methods=["POST"], csrf=False, cors="*", multilang=False)
    def post(self, model=None, id=None, **payload):
        """Create a new record.
        Basic sage:
        import requests

        headers = {
            'content-type': 'application/x-www-form-urlencoded',
            'charset': 'utf-8',
            'access-token': 'access_token'
        }
        data = {
            'name': 'Babatope Ajepe',
            'country_id': 105,
            'child_ids': [
                {
                    'name': 'Contact',
                    'type': 'contact'
                },
                {
                    'name': 'Invoice',
                   'type': 'invoice'
                }
            ],
            'category_id': [{'id': 9}, {'id': 10}]
        }
        req = requests.post('%s/api/res.partner/' %
                            base_url, headers=headers, data=data)

        """
        ioc_name = model
        model = request.env[self._model].sudo().search(
            [("model", "=", model)], limit=1)
        if model:
            try:
                fields = ['id', 'display_name']
                if payload.get("_fields"):
                    try:
                        fields = json.loads(payload.get("_fields"))
                    except Exception as e:
                        del payload['_fields']
                        _logger.info(e)
                        pass

                model_create = request.env['ir.model'].sudo().search([('model', '=', model.model)])
                if model_create:
                    field_list = model_create.field_id.filtered(
                        lambda x: x.ttype in ['many2many', 'one2many']).mapped('name')
                    for key in payload.keys():
                        if key in field_list:
                            payload[key] = [(0, 0, x) for x in json.loads(payload[key])]

                    field_list_m2o = model_create.field_id.filtered(
                        lambda x: x.ttype in ['many2one']).mapped('name')
                    for key in payload.keys():
                        if key in field_list_m2o:
                            payload[key] = int(payload[key])

                    fields_boolean = model_create.field_id.filtered(
                        lambda x: x.ttype in ['boolean']).mapped('name')
                    for key in payload.keys():
                        if key in fields_boolean:
                            if payload[key].lower() in ['true', '1']:
                                payload[key] = True
                            else:
                                payload[key] = False

                    # field_list_required = model_create.field_id.filtered(
                    #     lambda x: x.required == True).mapped('name')
                    #
                    # mess = []
                    # for key in field_list_required:
                    #     if key not in payload.keys():
                    #         mess.append(key)
                    #
                    # if len(mess) > 0:
                    #     return invalid_response("Exception", '%s is required' % ', '.join(mess))
                resource = request.env[model.model].sudo().with_context(api=True).create(payload)
            except Exception as e:
                return invalid_response("Exception", e)
            else:
                if resource:
                    domain = [("id", "=", int(resource.id))]
                    try:
                        data = (
                            request.env[ioc_name].search_read(
                                domain=domain,
                                fields=fields,
                                offset=0,
                                limit=0,
                                order=None,
                            )
                        )
                    except Exception as e:
                        return invalid_response("Exception", e)
                    else:
                        return valid_response(data)
                else:
                    return valid_response({"id": resource.id})
        return invalid_response(
            "invalid object model",
            "The model %s is not available in the registry." % ioc_name,
        )

    @validate_token
    @http.route(_routes, type="http", auth="none", methods=["PUT"], csrf=False, cors="*", multilang=False)
    def put(self, model=None, id=None, **payload):
        """."""
        try:
            _id = int(id)
        except Exception as e:
            return invalid_response(
                "invalid object id", "invalid literal %s for id with base " % id
            )
        _model = (
            request.env[self._model].sudo().search(
                [("model", "=", model)], limit=1)
        )
        if not _model:
            return invalid_response(
                "invalid object model",
                "The model %s is not available in the registry." % model,
                404,
            )
        try:
            request.env[_model.model].browse(_id).with_context(api=True).write(payload)
        except ValueError as e:
            return invalid_response("Value error", e, 400)
        except Exception as e:
            return invalid_response("Exception", e.name)
        else:
            status_mess = 'update %s record with id %s successfully!' % (_model.model, _id)
            return valid_response(payload)

    @validate_token
    @http.route(_routes, type="http", auth="none", methods=["DELETE"], csrf=False, cors="*", multilang=False)
    def delete(self, model=None, id=None, **payload):
        """."""
        try:
            _id = int(id)
        except Exception as e:
            return invalid_response(
                "invalid object id", "invalid literal %s for id with base " % id
            )
        try:
            record = request.env[model].with_context(api=True).search([("id", "=", _id)])
            if record:
                record.with_context(api=True).unlink()
            else:
                return invalid_response(
                    "missing_record",
                    "record object with id %s could not be found" % _id,
                    404,
                )
        except Exception as e:
            return invalid_response("Exception", e.name, 503)
        else:
            return valid_response("record %s has been successfully deleted" % record.id)

    @validate_token
    @http.route(_routes, type="http", auth="none", methods=["PATCH"], csrf=False, cors="*", multilang=False)
    def patch(self, model=None, id=None, action=None, **payload):
        """."""
        try:
            _id = int(id)
        except Exception as e:
            return invalid_response(
                "invalid object id", "invalid literal %s for id with base " % id
            )
        try:
            check_method_name(action)
            record = request.env[model].sudo().with_context(api=True).search([("id", "=", _id)])
            _callable = action in [
                method for method in dir(record) if callable(getattr(record, method))
            ]
            if record and _callable:
                # action is a dynamic variable.
                args = payload if payload else {}
                getattr(record, action)(args)
            else:
                return invalid_response(
                    "missing_record",
                    "record object with id %s could not be found or %s object has no method %s"
                    % (_id, model, action),
                    404,
                )
        except Exception as e:
            return invalid_response("Exception", e, 503)
        else:
            return valid_response("record %s has been successfully patched" % record.id)
