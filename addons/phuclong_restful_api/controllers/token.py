# Part of odoo. See LICENSE file for full copyright and licensing details.
import json
import logging

import werkzeug.wrappers

from odoo import http
from odoo.addons.phuclong_restful_api.common import invalid_response, valid_response
from odoo.http import request
from ..models.access_token import create_token

_logger = logging.getLogger(__name__)

expires_in = "phuclong_restful_api.access_token_expires_in"

class AccessToken(http.Controller):
    """."""

    def __init__(self):
        self._expires_in = request.env.ref(expires_in).sudo().value

    @http.route(
        "/api/v1/auth/token", methods=["GET"], type="http", auth="none", csrf=False, multilang=False
    )
    def token(self, **post):
        """The token URL to be used for getting the access_token:

        Args:
            **post must contain login and password.
        Returns:

            returns https response code 404 if failed error message in the body in json format
            and status code 202 if successful with the access_token.
        Example:
           import requests

           headers = {'content-type': 'text/plain', 'charset':'utf-8'}

           data = {
               'login': 'admin',
               'password': 'admin',
               'db': 'galago.ng'
            }
           base_url = 'http://odoo.ng'
           eq = requests.post(
               '{}/api/auth/token'.format(base_url), data=data, headers=headers)
           content = json.loads(req.content.decode('utf-8'))
           headers.update(access-token=content.get('access_token'))
        """
        db, username, password = (
            request.db,
            post.get("login"),
            post.get("password"),
        )
        _credentials_includes_in_body = all([db, username, password])
        if not _credentials_includes_in_body:
            # The request post body is empty the credetials maybe passed via the headers.
            headers = request.httprequest.headers
            db = headers.get("db")
            username = headers.get("login")
            password = headers.get("password")
            _credentials_includes_in_headers = all([db, username, password])
            if not _credentials_includes_in_headers:
                # Empty 'db' or 'username' or 'password:
                return invalid_response(
                    "missing error",
                    "either of the following are missing [db, username,password]",
                    403,
                )
        # Login in odoo database:
        try:
            request.session.authenticate(db, username, password)
        except Exception as e:
            # Invalid database:
            print(e)
            # info = "The database name is not valid {}".format((e))
            error = "invalid_login"
            # _logger.error(info)
            return invalid_response(error,"Wrong database/username/password!")

        uid = request.session.uid
        # odoo login failed:
        if not uid:
            info = "authentication failed"
            error = "authentication failed"
            _logger.error(info)
            return invalid_response(401, error, info)

        # Generate tokens
        access_token = create_token(uid)

        # Successful response:
        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
            response=json.dumps(
                {
                    "id": uid,
                    "user_context": request.session.get_context() if uid else {},
                    "company_id": request.env.user.company_id.id if uid else None,
                    "access_token": access_token.decode('utf-8'),
                    "expires_in": self._expires_in,
                }
            ),
        )

    @http.route(
        "/api/v1/auth/token", methods=["DELETE"], type="http", auth="none", csrf=False, multilang=False
    )
    def delete(self, **post):
        """."""
        access_token = request.httprequest.headers.get("access_token")
        if not access_token:
            info = "No access token was provided in request!"
            error = "no_access_token"
            _logger.error(info)
            return invalid_response(400, error, info)
        for token in access_token:
            token.unlink()
        # Successful response:
        return valid_response(
            200, {"desc": "token successfully deleted", "delete": True}
        )
