from odoo.http import request
from odoo import fields, http, SUPERUSER_ID, _
import requests
from odoo.addons.phuclong_restful_api.common import invalid_response, valid_response, get_cache
from odoo.addons.phuclong_restful_api.models.access_token import check_token, create_token
from odoo.addons.phuclong_restful_api.controllers.main import validate_token
from datetime import date, datetime, timedelta, time
from dateutil import relativedelta
import json
import math
import hashlib
import logging
import base64
import random

_logger = logging.getLogger(__name__)

list_weekday = {
    '1': 'monday',
    '2': 'tuesday',
    '3': 'wednesday',
    '4': 'thursday',
    '5': 'friday',
    '6': 'saturday',
    '7': 'sunday'
}


class PhucLongAPPController(http.Controller):

    def create_partner_and_user(self, name, mobile, password, method_login):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        partner_obj = request.env['res.partner']
        user_obj = request.env['res.users']
        partner_id = partner_obj.sudo().search([('mobile', '=', mobile)])
        if partner_id:
            partner_id.write({
                'name': name,
                'authorized': True,
                'customer': True,
            })
            partner_id.method_login_ids.filtered(lambda x: x.login_id.id == method_login.id).write(
                {'name': password})
            login_method_partner = partner_id.method_login_ids.filtered(
                lambda x: x.login_id.id == method_login.id)
            if login_method_partner:
                login_method_partner.update({'name': password})
            else:
                partner_id.write({'method_login_ids': [
                    (0, 0, {'name': password, 'login_id': method_login.id})]})
            if partner_id.user_ids:
                partner_id.user_ids[0].write({'password': password})
                user_id = partner_id.user_ids[0]
            else:
                user_id = user_obj.sudo()._create_user_from_template({
                    'name': name,
                    'login': mobile,
                    'password': password,
                    'partner_id': partner_id.id,
                })
                try:
                    request.env.ref('base.group_portal').write(
                        {'users': [(4, user_id.id)]})
                except Exception as e:
                    pass
        else:
            partner_id = partner_obj.sudo().create({
                'name': name,
                'mobile': mobile,
                'authorized': True,
                'customer': True,
                'can_loyalty_level': False,
                'method_login_ids': [(0, 0, {'name': password, 'login_id': method_login.id})]
            })
            user_id = user_obj.sudo()._create_user_from_template({
                'name': name,
                'login': mobile,
                'password': password,
                'partner_id': partner_id.id,
            })
            try:
                request.env.ref('base.group_portal').write(
                    {'users': [(4, user_id.id)]})
            except Exception as e:
                pass
            partner_id.sudo().write({
                'email': False,
                'street': False,
                'parent_id': False,
                'street2': False,
                'city': False,
                'state_id': False,
                'district_id': False,
                'ward_id': False,
                'zip': False,
                'country_id': False,
                'vat': False
            })
        return partner_id, user_id

    def _prepair_url_image(self, model, field, id):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        base_url = request.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        return base_url + '/web/image/%s/%s/%s' % (model, id, field)

    @http.route('/api/v1/check_token', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def check_token(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        token = payload.get('access_token', False)
        if token:
            is_expire, data = check_token(token)
            if is_expire:
                user_id = request.env['res.users'].sudo().browse(data)
                return valid_response(self._prepair_response_login(user_id.partner_id, user_id))
            else:
                return invalid_response('Something went wrong', data)
        else:
            return invalid_response('Missing field', 'Missing access_token field')

    @http.route('/api/v1/get_accept_login', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def get_accept_login(self):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        data = get_cache()
        if data:
            return valid_response(data, has_cache=False)
        login_obj = request.env['configuration.login'].sudo()
        list_login = login_obj.with_context(api=True).search_read(
            [('active', '=', True)], fields=['name', 'code'])
        return valid_response(list_login)

    @validate_token
    @http.route('/api/v1/update_password', type="http", auth="none", methods=["POST"], csrf=False, cors="*")
    def update_password(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        partner_obj = request.env['res.partner'].sudo()
        login_method_id = request.env.ref(
            'phuclong_mobile_backend.login_method_mobile')
        if payload.get('partner_id', False) and payload.get('password', False):
            partner_id = partner_obj.browse(
                int(payload.get('partner_id', False)))
            if partner_id:
                try:
                    login = partner_id.method_login_ids.filtered(
                        lambda x: x.login_id.id == login_method_id.id)
                    if login:
                        login.sudo().write({'name': payload.get('password')})
                        return valid_response({'status': True})
                    else:
                        partner_id.sudo().write({'method_login_ids': [
                            (0, 0, {'name': payload.get('password', False), 'login_id': login_method_id.id})]})
                except Exception as e:
                    _logger.info("Change password fail" + str(e.name or e))
                    return invalid_response('Error', 'Something went wrong!')
            else:
                return invalid_response('Error', 'Partner_id not exists')
        else:
            return invalid_response('Error', 'Missing require value!')

    @http.route('/api/v1/send_otp', type="http", auth="none", methods=["POST"], csrf=False, cors="*")
    def send_otp(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        mobile = payload.get('mobile', False)
        if mobile:
            if payload.get('register', False) == 'False':
                try:
                    otp = '123456'
                    request.env['mobile.otp'].sudo().create({
                        'name': mobile,
                        'otp': otp,
                        'expires_in': fields.Datetime.now() + timedelta(seconds=600)
                    })
                    return valid_response({'status': True})
                except Exception as e:
                    return valid_response({'status': False})
            partner_id = request.env['res.partner'].sudo().search(
                [('mobile', '=', mobile)], limit=1)
            if partner_id:
                if partner_id.authorized:
                    if partner_id.method_login_ids.filtered(lambda x: x.login_id.code == 'SMS'):
                        return valid_response({'name': partner_id.name or None, 'mobile_status': 1})
                    if partner_id.method_login_ids:
                        try:
                            otp = '123456'
                            request.env['mobile.otp'].sudo().create({
                                'name': mobile,
                                'otp': otp,
                                'expires_in': fields.Datetime.now() + timedelta(seconds=600)
                            })
                            return valid_response({'name': partner_id.name or None, 'mobile_status': 0})
                        except Exception as e:
                            return valid_response({'name': partner_id.name or None, 'mobile_status': -1})
                    else:
                        return valid_response({'name': partner_id.name or None, 'mobile_status': 1})
                else:
                    return valid_response({'name': partner_id.name or None, 'mobile_status': 2})
            else:
                try:
                    otp = '123456'
                    request.env['mobile.otp'].sudo().create({
                        'name': mobile,
                        'otp': otp,
                        'expires_in': fields.Datetime.now() + timedelta(seconds=600)
                    })
                    return valid_response({'name': partner_id.name or None, 'mobile_status': 0})
                except Exception as e:
                    return valid_response({'name': partner_id.name or None, 'mobile_status': -1})
        else:
            return invalid_response('Mobile was wrong', 'The phone number is not in the correct format')

    @http.route('/api/v1/check_otp', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def check_otp(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        mobile = payload.get('mobile', False)
        otp = payload.get('otp', False)
        if mobile and otp:
            check_otp = request.env['mobile.otp'].sudo().search([('name', '=', mobile), ('otp', '=', otp)],
                                                                order='create_date DESC', limit=1)
            if check_otp and check_otp.expires_in > fields.Datetime.now():
                return valid_response({'status': True})
            return valid_response({'status': False})
        else:
            return invalid_response('Missing fields required', 'Missing fields required')

    def check_account_mobile(self, mobile):
        if mobile:
            partner_obj = request.env['res.partner'].sudo()
            mobile_partner = partner_obj.search([('mobile', '=', mobile)])
            if mobile_partner:
                mobile_authorized = mobile_partner.authorized
                if mobile_authorized:
                    return 1
                else:
                    return 2
            else:
                return 0
        else:
            return -1

    @http.route('/api/v1/accept_login_method', type="http", auth="none", methods=["POST"], csrf=False, cors="*")
    def accept_login_method(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        method_login = payload.get('method_login', False)
        password = payload.get('password', False)
        method_login_id = request.env['configuration.login'].sudo().with_context(api=True).search(
            [('code', '=', method_login)])
        if method_login_id:
            partner_id = request.env['res.partner'].sudo().browse(
                int(payload.get('partner_id', False)))
            if partner_id:
                partner_id.sudo().write({'method_login_ids': [
                    (0, 0, {'name': password, 'login_id': method_login_id.id})]})
            else:
                return invalid_response('Not found', 'Account not found', 404)
        else:
            return invalid_response('Not found', 'Login not found', 404)

    @http.route('/api/v1/login_with_third_party', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def login_with_third_party(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        method_login = payload.get('method_login', False)
        password = payload.get('password', False)
        method_login_id = request.env['configuration.login'].sudo().with_context(api=True).search(
            [('code', '=', method_login)])
        if method_login_id:
            login = request.env['login.method'].sudo().search(
                [('name', '=', password), ('login_id', '=', method_login_id.id)], limit=1)
            if login:
                user_id = login.partner_id.user_ids and login.partner_id.user_ids[0] or False
                return valid_response({'status': True, 'data': self._prepair_response_login(login.partner_id, user_id)})
            else:
                return valid_response({'status': False, 'data': {}})
        else:
            return invalid_response('Missing required', 'Method login not exists', 404)

    @http.route('/api/v1/register', type="http", auth="none", methods=["POST"], csrf=False, cors="*")
    def register(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        name = payload.get('name', False)
        mobile = payload.get('mobile', False)
        password = payload.get('password', False)
        otp = payload.get('otp', False)
        method_login = payload.get('method_login', False)
        method_login_id = request.env['configuration.login'].sudo().with_context(
            api=True).search([('code', '=', method_login)])
        if method_login_id:
            if method_login_id.code == 'SMS':
                partner_id = request.env['res.partner'].sudo().search(
                    [('mobile', '=', mobile), ('authorized', '=', True)])
                if partner_id and partner_id.method_login_ids:
                    partner_id.sudo().write({'method_login_ids': [
                        (0, 0, {'name': password, 'login_id': method_login_id.id})]})
                    user_id = partner_id.user_ids and partner_id.user_ids[0] or False
                    return valid_response(self._prepair_response_login(partner_id, user_id))
                if otp:
                    check_otp = request.env['mobile.otp'].sudo().search([('name', '=', mobile), ('otp', '=', otp)],
                                                                        order='create_date DESC', limit=1)
                    if check_otp and check_otp.expires_in > fields.Datetime.now():
                        if name and mobile and password:
                            partner_id = request.env['res.partner'].sudo().search(
                                [('mobile', '=', mobile), ('authorized', '=', True)])
                            if not partner_id:
                                try:
                                    partner_id, user_id = self.create_partner_and_user(
                                        name, mobile, password, method_login_id)
                                    return valid_response(
                                        self._prepair_response_login(partner_id, user_id))
                                except Exception as e:
                                    return invalid_response('Something went wrong', e, 405)
                            else:
                                return invalid_response('Error', 'Mobile is exists', 404)
                        else:
                            return invalid_response('Missing required', 'Missing name, mobile, password', 405)
                    else:
                        return invalid_response('Something went wrong', 'OTP is expires', 405)
                else:
                    return invalid_response('Missing required', 'OTP not exists', 404)
            else:
                if name and mobile and password:
                    partner_id = request.env['res.partner'].sudo().search(
                        [('mobile', '=', mobile), ('authorized', '=', True)])
                    if not partner_id:
                        try:
                            partner_id, user_id = self.create_partner_and_user(
                                name, mobile, password, method_login_id)
                            return valid_response(
                                self._prepair_response_login(partner_id, user_id))
                        except Exception as e:
                            return invalid_response('Something went wrong', e, 405)
                    else:
                        partner_id.sudo().write({'method_login_ids': [
                            (0, 0, {'name': password, 'login_id': method_login_id.id})]})
                        user_id = partner_id.user_ids and partner_id.user_ids[0] or False
                        return valid_response(self._prepair_response_login(partner_id, user_id))
        else:
            return invalid_response('Missing required', 'Method login not exists', 404)

    def _prepair_response_login(self, partner_id, user_id):
        list_login = []
        method_login = ['FB', 'SMS', 'GG', 'SMS']
        method_login_partner = partner_id.method_login_ids.mapped(
            'login_id').mapped('code')
        for method in method_login:
            if method not in method_login_partner:
                list_login.append({'code': method, 'status': False})
            else:
                list_login.append({'code': method, 'status': True})
        return {
            'access_token': create_token(user_id.id),
            'name': partner_id.name or None,
            'partner_id': partner_id.id or None,
            'phone': partner_id.mobile or None,
            'gender': partner_id.gender or None,
            'email': partner_id.email or None,
            'birthday': partner_id.birthday or None,
            'street': partner_id.contact_address or None,
            'identification': partner_id.identification_id or None,
            'appear_code': partner_id.appear_code_id.appear_code or None,
            'wallet_on_account': partner_id.wallet_on_account or None,
            'wallet_id': partner_id.wallet_id.id or None,
            'loyalty_level_name': partner_id.loyalty_level_id.level_name or 'Mới',
            'loyalty_level_id': partner_id.loyalty_level_id.id or None,
            'loyalty_discount_percent': partner_id.loyalty_level_id.discount_percent or None,
            'current_point_act': partner_id.current_point_act or None,
            'total_point_act': partner_id.total_point_act or None,
            'year_discount_birth': partner_id.year_discount_birth or None,
            'date_get_loyalty_card': partner_id.date_get_loyalty_card or None,
            'expired_date_loyalty_card': partner_id.expired_date or None,
            'change_date_level': partner_id.change_date_level or None,
            'image': partner_id.image_1920 or None,
            'accept_login_method': list_login
        }

    @http.route('/api/v1/login', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def login(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        password = payload.get('password', False)
        mobile = payload.get('mobile', False)
        method_login = payload.get('method_login', False)
        method_login_id = request.env['configuration.login'].sudo().with_context(
            api=True).search([('code', '=', method_login)])
        if method_login_id:
            if method_login_id.code == 'SMS':
                partner_id = request.env['res.partner'].sudo().search(
                    [('mobile', '=', mobile)], limit=1)
                if partner_id and partner_id.method_login_ids.filtered(lambda x: x.login_id.code == 'SMS' and x.name == password):
                    user_id = partner_id.user_ids and partner_id.user_ids[0] or False
                    return valid_response(self._prepair_response_login(partner_id, user_id))
                else:
                    return invalid_response('Not found', 'Account not found', 404)
            if method_login_id and password:
                login = request.env['login.method'].sudo().search(
                    [('name', '=', password), ('login_id', '=', method_login_id.id)], limit=1)
                if login:
                    user_id = login.partner_id.user_ids and login.partner_id.user_ids[0] or False
                    return valid_response(self._prepair_response_login(login.partner_id, user_id))
                else:
                    return invalid_response('Not found', 'Account not found', 404)
            else:
                return invalid_response('Missing required fields', 'Missing fields required', 404)
        else:
            return invalid_response('Missing required', 'Method login not exists', 404)

    def float_time_convert(self, float_val):
        hours = 0
        mins = 0
        if float_val:
            hours = math.floor(abs(float_val))
            mins = abs(float_val) - hours
            mins = round(mins * 60)
            if mins >= 60.0:
                hours = hours + 1
                mins = 0.0
        float_time = '%02d:%02d' % (hours, mins)
        return float_time

    def convert_float_to_time(self, float_time):
        return ' {0:02.0f}:{1:02.0f}'.format(*divmod(float_time * 60, 60))

    @http.route('/api/v1/get_store', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def get_store(self):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        store_obj = request.env['res.store']
        store_ids = store_obj.sudo().search([])
        res = []
        for store in store_ids:
            duration = []
            for time in store.durations_ids:
                duration.append({
                    'name': time.name.name or None,
                    'opening_time': self.convert_float_to_time(time.opening_time) or False,
                    'closing_time': self.convert_float_to_time(time.closing_time) or False,
                })
            res.append({
                'id': store.id,
                'name': store.name or None,
                'address': store.address or None,
                # 'description_time': store.description_time or None,
                'delivery_hotline': store.delivery_hotline or None,
                'customer_hotline': store.customer_hotline or None,
                'warehouse_id': store.warehouse_id.id or None,
                'latitude': store.latitude or None,
                'longitude': store.longitude or None,
                'duration': duration,
                'image': self._prepair_url_image('res.store', 'image_1920', store.id) or None,
                'city': store.state_id.name or None
            })
        return valid_response(res)

    def _prepare_product_vals(self, product):
        if product.parent_code:
            return {
                'parent_code': product.parent_code or None,
                'sizes': [
                    {
                        'product_id': product.id,
                        'price': product.list_price or 0.0,
                        'size': product.size_id.name or None
                    }
                ],
                'name': product.name_mobile if product.name_mobile else product.name,
                'categ_id': product.mobile_category_id.id or None,
                'price': product.list_price or 0.0,
                'eng_name': product.eng_name.split('(')[0].strip() if product.eng_name else None,
                'is_topping': False,
                'description': product.app_description or None,
                'image': self._prepair_url_image('product.template', 'image_1920', str(product.id)),
                'toppings': [
                    {
                        'topping_id': x.id,
                        'topping_name': x.name or None,
                        'price': x.list_price or 0.0
                    } for x in product.suitable_topping_ids
                ],
                'materials': [
                    {
                        'material_id': x.id,
                        'material_name': x.name_mobile if x.name_mobile else x.name,
                        'size': [item for item in [{'code': 'over', 'name': 'Nhiều'}, {'code': 'normal', 'name': 'Bình thường'},
                                                   {'code': 'below', 'name': 'Ít'}, {'code': 'none', 'name': 'Không'}] if item['code'] not in x.option_unavailable_ids.mapped('type')]
                    } for x in product.custom_material_ids if x.available_in_mobile
                ]
            }
        else:
            return {
                'product_id': product.id,
                'parent_code': product.parent_code or None,
                'size': product.size_id.name or None,
                'name': product.name_mobile if product.name_mobile else product.name,
                'categ_id': product.mobile_category_id.id or None,
                'price': product.list_price or 0.0,
                'eng_name': product.eng_name or None,
                'description': product.app_description or None,
                'is_topping': False,
                'image': self._prepair_url_image('product.template', 'image_1920', str(product.id)),
                'toppings': [
                    {
                        'topping_id': x.id,
                        'topping_name': x.name or None,
                        'price': x.list_price or 0.0
                    } for x in product.suitable_topping_ids
                ],
                'materials': [
                    {
                        'material_id': x.id,
                        'material_name': x.name_mobile if x.name_mobile else x.name,
                        'size': [item for item in [{'code': 'over', 'name': 'Nhiều'}, {'code': 'normal', 'name': 'Bình thường'},
                                                   {'code': 'below', 'name': 'Ít'}, {'code': 'none', 'name': 'Không'}] if item['code'] not in x.option_unavailable_ids.mapped('type')]
                    } for x in product.custom_material_ids if x.available_in_mobile
                ]
            }

    @http.route('/api/v1/get_product', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def get_product(self):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        product_obj = request.env['product.template']
        res = []
        for product in product_obj.sudo().search([('available_in_mobile', '=', True), ('active', '=', True)]):
            data_flag = list(
                filter(lambda x: res[x]['parent_code'] == product.parent_code and product.parent_code,
                       range(len(res))))
            if len(data_flag) > 0:
                res[data_flag[0]]['sizes'].append({
                    'product_id': product.id,
                    'price': product.list_price or 0.0,
                    'size': product.size_id.name or None
                })
                res[data_flag[0]]['price'] = product.list_price if res[data_flag[0]]['price'] > product.list_price else \
                    res[data_flag[0]]['price']
                res[data_flag[0]]['sizes'] = sorted(
                    res[data_flag[0]]['sizes'], key=lambda k: k['price'])
            else:
                res.append(self._prepare_product_vals(product))
        return valid_response(res)

    @http.route('/api/v1/check_update', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def check_update(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        date_from = payload.get('date_from', False)
        date_to = payload.get('date_to', False)
        if date_to and date_from:
            products = []
            product_obj = request.env['product.template']
            for product in product_obj.sudo().search([('write_date', '>=', date_from), ('write_date', '<=', date_to)]):
                data_flag = list(
                    filter(lambda x: products[x]['parent_code'] == product.parent_code and product.parent_code,
                           range(len(products))))
                if len(data_flag) > 0:
                    products[data_flag[0]]['sizes'].append({
                        'product_id': product.id,
                        'price': product.list_price or 0.0,
                        'size': product.size_id.name or None
                    })
                    products[data_flag[0]]['price'] = product.list_price if products[data_flag[0]][
                        'price'] > product.list_price else \
                        products[data_flag[0]]['price']
                    products[data_flag[0]]['sizes'] = sorted(
                        products[data_flag[0]]['sizes'], key=lambda k: k['price'])
                else:
                    products.append(self._prepare_product_vals(product))
            return valid_response(products)
        else:
            return invalid_response('Missing Data', 'Missing date_from, date_to', 403)

    @http.route('/api/v1/get_new_product', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def get_new_product(self):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        product_obj = request.env['product.template']
        res = []
        for product in product_obj.sudo().search([('is_new_product', '=', True)]):
            data_flag = list(
                filter(lambda x: res[x]['parent_code'] == product.parent_code and product.parent_code,
                       range(len(res))))
            if len(data_flag) > 0:
                res[data_flag[0]]['sizes'].append({
                    'product_id': product.id,
                    'price': product.list_price or 0.0,
                    'size': product.size_id.name or None
                })
                res[data_flag[0]]['price'] = product.list_price if res[data_flag[0]]['price'] > product.list_price else \
                    res[data_flag[0]]['price']
                res[data_flag[0]]['sizes'] = sorted(
                    res[data_flag[0]]['sizes'], key=lambda k: k['price'])
            else:
                res.append(self._prepare_product_vals(product))
        return valid_response(res)

    @http.route('/api/v1/get_combo', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def get_combo(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        combo_obj = request.env['sale.promo.combo'].sudo()
        warehouse_id = request.env['stock.warehouse'].browse(
            int(payload.get('warehouse_id', 0)))
        res = []
        date = fields.Datetime.now()
        sale_type_id = False
        if payload.get('sale_type_id', False):
            sale_type_id = request.env['pos.sale.type'].sudo().search(
                [('type_for_app', '=', str(payload['sale_type_id']))], limit=1).id
        if warehouse_id:
            combo_ids = combo_obj.search([('start_date', '<=', str(date)[0:11]), ('end_date', '>=', str(date)[0:11]),
                                          ('state', '=', 'approved'),
                                          ('sale_type_ids', '=',
                                           sale_type_id), '&', '|',
                                          ('warehouse_ids', '=',
                                           warehouse_id.id), ('warehouse_ids', '=', False),
                                          '|', ('day_of_week.value', '=', list_weekday[str(
                                              (fields.Datetime.now() + timedelta(hours=7)).isoweekday())]),
                                          ('day_of_week', '=', False)])
            for combo_id in combo_ids:
                combo_lines = []
                for line_id in combo_id.combo_line_ids:
                    products = []
                    if line_id.use_pricelist:
                        if line_id.apply_on == 'categ':
                            product_ids = request.env['product.template'].sudo().search(
                                [('categ_id', 'in', line_id.categ_ids.ids), ('available_in_mobile', '=', True)])
                            for product in product_ids:
                                products.append({
                                    'product_id': product.id,
                                    'product_name': product.name or None,
                                    'price': product.list_price or None
                                })
                        else:
                            for line in line_id.combo_line_detail_ids:
                                products.append({
                                    'product_id': line.product_id.product_tmpl_id.id,
                                    'product_name': line.product_id.name or None,
                                    'price': line.product_id.list_price or None
                                })
                    else:
                        if line_id.apply_on == 'categ':
                            product_ids = request.env['product.template'].sudo().search(
                                [('categ_id', 'in', line_id.categ_ids.ids), ('available_in_mobile', '=', True)])
                            for product in product_ids:
                                products.append({
                                    'product_id': product.id,
                                    'product_name': product.name or None,
                                    'price': product.list_price or None
                                })
                        else:
                            for line in line_id.combo_line_detail_ids:
                                products.append({
                                    'product_id': line.product_id.product_tmpl_id.id,
                                    'product_name': line.product_id.name or None,
                                    'price': line.unit_price_combo or None
                                })
                    combo_lines.append({
                        'line_id': line_id.id,
                        'qty': line_id.qty_combo or None,
                        'products': products or None
                    })
                res.append({
                    'combo_id': combo_id.id,
                    'use_for_coupon': combo_id.use_for_coupon,
                    'image': self._prepair_url_image('sale.promo.combo', 'image_mobile', str(combo_id.id)),
                    'combo_name': combo_id.name or None,
                    'combo_lines': combo_lines or None
                })
            return valid_response(res)
        else:
            return invalid_response("Invalid data", "warehouse_id not in params", 400)

    @http.route('/api/v1/get_banner', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def get_banner(self):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        banner_obj = request.env['mobile.homepage.slide'].sudo()
        res = []
        for item in banner_obj.sudo().search([], order='create_date DESC'):
            res.append({
                'name': item.name or '',
                'image': self._prepair_url_image('mobile.homepage.slide', 'image', str(item.id)),
                'new_id': item.new_id.id or None
            })
        return valid_response(res)

    @http.route('/api/v1/get_cate', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def get_cate(self):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        return valid_response(request.env['product.category.mobile'].sudo().search_read([],
                                                                                        fields=[
                                                                                            'id', 'name'],
                                                                                        order='sequence_of_category ASC'))

    @http.route('/api/v1/get_question_answer', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def get_question_answer(self):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        return valid_response(
            request.env['config.qanda'].sudo().search_read([('hide', '=', False)], fields=['id', 'name', 'url']))

    @http.route('/api/v1/get_news', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def get_news(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        new_id = payload.get('new_id', False)
        if new_id:
            new = request.env['show.case'].sudo().search([('id', '=', new_id)])
            if new:
                res = {
                    'id': new.id,
                    'title': new.name or None,
                    'highlight': new.short_des or None,
                    'content': new.body_html or None,
                }
                if new.view_type == '2':
                    if new.use_for == 'product':
                        res.update({
                            'use_for': 'product',
                            'product': new.product_id.id or None,
                            'combo': None
                        })
                    else:
                        res.update({
                            'use_for': 'combo',
                            'combo': new.combo_id.id or None,
                            'product': None
                        })
                else:
                    res.update({
                        'use_for': None,
                        'product': None,
                        'combo': None
                    })
                return valid_response([res])
            return invalid_response('Not Found', 'New id not found', 404)
        else:
            new_ids = request.env['show.case'].sudo().search(
                [('is_published', '=', True)])
            res = []
            for item in new_ids:
                res.append({
                    'id': item.id,
                    'title': item.name or None,
                    'highlight': item.short_des or None,
                    'view_type': item.view_type or None,
                    'image': self._prepair_url_image('show.case', 'image', item.id)
                })
            return valid_response(res)

    @http.route('/api/v1/get_shipping_fee', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def get_shipping_fee(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        return valid_response(request.env['shipping.fee'].sudo().search_read([], fields=['id', 'name', 'active',
                                                                                         'distance_to', 'distance_from',
                                                                                         'quantity_product_min',
                                                                                         'quantity_product_max'
                                                                                         'delivery_cost']))

    def _prepair_material_line(self, list_material, product):
        res = []
        for item in list_material:
            res.append([0, 0, {
                'option_id': item['material_id'],
                'option_type': item['size']
            }])
        for item in product.custom_material_ids:
            if not item.available_in_mobile:
                res.append([0, 0, {
                    'option_id': item.id,
                    'option_type': 'normal'
                }])
        return res

    def _compute_unitprice(self, product_id, sale_type_id, warehouse_id):
        pricelist_ids = request.env['product.pricelist'].sudo().search(['|', ('apply_type', '=', 'all_warehouse'), '&',
                                                                        ('warehouse_ids', '=',
                                                                         warehouse_id.id),
                                                                        ('sale_type_ids', '=', sale_type_id.id)])
        pricelist_priority = pricelist_ids.filtered(
            lambda x: x.price_type == 'price_event')
        if not pricelist_priority:
            pricelist_id = pricelist_ids[0] if len(
                pricelist_ids) > 0 else False
        else:
            pricelist_id = pricelist_priority[0]
        if not pricelist_id:
            return product_id.list_price
        else:
            if len(pricelist_id.item_ids) == 0:
                return product_id.list_price
            else:
                if pricelist_id.item_ids.filtered(
                        lambda x: x.applied_on == '1_product' and x.product_tmpl_id == product_id.id):
                    item = pricelist_id.item_ids.filtered(
                        lambda x: x.applied_on == '1_product' and x.product_tmpl_id == product_id.id)
                    if item.compute_price == 'fixed':
                        return item.fixed_price
                    else:
                        return product_id.list_price * item.percent_price / 100
                elif pricelist_id.item_ids.filtered(
                        lambda x: x.applied_on == '2_product_category'):
                    for item in pricelist_id.item_ids.filtered(
                            lambda x: x.applied_on == '2_product_category'):
                        product_ids = request.env['product.template'].sudo().search(
                            json.loads(item.category_dom))
                        if product_id in product_ids:
                            if item.compute_price == 'fixed':
                                return item.fixed_price
                            else:
                                return product_id.list_price * item.percent_price / 100
                elif pricelist_id.item_ids.filtered(
                        lambda x: x.applied_on == '3_global'):
                    item = pricelist_id.item_ids.filtered(
                        lambda x: x.applied_on == '3_global')
                    if item.compute_price == 'fixed':
                        return item.fixed_price
                    else:
                        return product_id.list_price * item.percent_price / 100

    def _prepair_order_lines(self, product_id, sale_type_id, warehouse_id, qty, materials, order_id,
                             order_line_id=None, price_unit=None, combo_id=None,
                             is_topping=False, loyalty_discount_percent=None, description='', no_compute_price=False, coupon_app_id=False):
        if not no_compute_price:
            price = price_unit if price_unit else self._compute_unitprice(
                product_id, sale_type_id, warehouse_id)
        else:
            price = price_unit
        cup_id = product_id.cup_ids.filtered(
            lambda x: x.sale_type_id.id == sale_type_id.id)
        discount = 0
        discount_amount = 0
        is_loyalty_line = False
        is_birthday_promotion = False
        if is_topping or combo_id:
            coupon_app_id = False
        if coupon_app_id:
            if coupon_app_id.type == 'birthday':
                is_birthday_promotion = True
            is_loyalty_line = True
            if coupon_app_id.gift_type == 'product':
                price = 0
                loyalty_discount_percent = 0
            if coupon_app_id.gift_type == 'discount':
                if coupon_app_id.type == 'point':
                    discount_amount = coupon_app_id.discount
                elif coupon_app_id.type == 'birthday':
                    discount = coupon_app_id.discount
        if loyalty_discount_percent:
            is_loyalty_line = True
        price_incl = price
        if discount > 0:
            price_incl = price_incl - (price_incl * discount / 100)
        if discount_amount > 0:
            price_incl = price_incl - discount_amount
        if loyalty_discount_percent > 0:
            price_incl = price_incl - \
                (price_incl * loyalty_discount_percent / 100)
        price_subtotal_incl = price_incl * qty
        return {
            'product_id': product_id.sudo().id,
            'qty': qty,
            'name': product_id.name,
            'uom_id': product_id.uom_id.id,
            'option_ids': self._prepair_material_line(materials, product_id),
            'price_unit': price,
            'discount': discount,
            'discount_amount': discount_amount,
            'loyalty_discount_percent': loyalty_discount_percent,
            'is_loyalty_line': is_loyalty_line,
            'is_birthday_promotion': is_birthday_promotion,
            'order_id': order_id.id,
            'related_line_id': order_line_id.id if order_line_id else False,
            'combo_id': combo_id.id if combo_id else False,
            'is_topping_line': is_topping,
            'note': description,
            'is_done_combo': True if combo_id else False,
            'price_subtotal': price,
            'cup_type': False if not cup_id or not cup_id.cup_line_ids else cup_id.cup_line_ids[0].cup_type,
            'price_subtotal_incl': price_subtotal_incl,
        }

    def _create_order_lines(self, sale_type_id, warehouse_id, order_id, shipping_fee, combos=None, products=None):
        order_line_obj = request.env['pos.order.line'].sudo()
        product_obj = request.env['product.product'].sudo()
        combo_obj = request.env['sale.promo.combo'].sudo()
        coupon_app_obj = request.env['coupon.app'].sudo()
        for product in products:
            product_id = product_obj.search(
                [('product_tmpl_id', '=', int(product['product_id']))])
            coupon_app_id = False
            voucher_lock_id = False
            if 'reward_id' in product and product['reward_id']:
                coupon_app_id = coupon_app_obj.search(
                    [('id', '=', product['reward_id'])], limit=1)
                if coupon_app_id:
                    voucher_lock_id = order_id.voucher_lock_ids.filtered(
                        lambda v: v.is_coupon_app and v.voucher_code == coupon_app_id.name)
            order_line_id = order_line_obj.create(self._prepair_order_lines(product_id, sale_type_id, warehouse_id,
                                                                            product['qty'], product['materials'],
                                                                            order_id,
                                                                            coupon_app_id=coupon_app_id,
                                                                            loyalty_discount_percent=product.get(
                                                                                'loyalty_discount_percent', False),
                                                                            description=product.get('description')))
            if voucher_lock_id:
                voucher_lock_id.write({'order_line_id': order_line_id.id})
            order_line_id.update({'fe_uid': order_line_id.id})
            for topping in product['toppings']:
                product_id = product_obj.search(
                    [('product_tmpl_id', '=', topping['topping_id'])])
                topping_id = order_line_obj.create(
                    self._prepair_order_lines(product_id, sale_type_id, warehouse_id,
                                              topping['qty'], [
                                              ], order_id, order_line_id, is_topping=True,
                                              coupon_app_id=coupon_app_id,
                                              loyalty_discount_percent=topping.get(
                                                  'loyalty_discount_percent', False),
                                              description=topping.get('description')))
                topping_id.update({'fe_uid': topping_id.id})
        for index, combo in enumerate(combos):
            combo_id = combo_obj.browse(combo['combo_id'])
            for line in combo['combo_lines']:
                line_id = combo_id.combo_line_ids.filtered(
                    lambda x: x.id == line['line_id'])
                if line_id:
                    if line_id.use_pricelist:
                        for product in line['products']:
                            product_id = product_obj.search(
                                [('product_tmpl_id', '=', product['product_id'])])
                            order_line_id = order_line_obj.create(
                                self._prepair_order_lines(product_id, sale_type_id, warehouse_id,
                                                          product['qty'], product['materials'], order_id,
                                                          combo_id=combo_id,
                                                          loyalty_discount_percent=False,
                                                          description=product.get('description')))
                            order_line_id.update({'fe_uid': order_line_id.id})
                            for topping in product['toppings']:
                                product_id = product_obj.search(
                                    [('product_tmpl_id', '=', topping['topping_id'])])
                                topping_id = order_line_obj.create(
                                    self._prepair_order_lines(product_id, sale_type_id, warehouse_id,
                                                              topping['qty'], [
                                                              ], order_id, order_line_id,
                                                              combo_id=combo_id, is_topping=True,
                                                              loyalty_discount_percent=False,
                                                              description=topping.get('description')))
                                topping_id.update({'fe_uid': topping_id.id})
                    else:
                        for product in line['products']:
                            product_id = product_obj.search(
                                [('product_tmpl_id', '=', product['product_id'])])
                            order_line_id = order_line_obj.create(
                                self._prepair_order_lines(product_id, sale_type_id, warehouse_id,
                                                          product['qty'], product['materials'], order_id,
                                                          price_unit=product['price'], combo_id=combo_id,
                                                          loyalty_discount_percent=False,
                                                          description=product.get(
                                                              'description'),
                                                          no_compute_price=True))
                            order_line_id.update({'fe_uid': order_line_id.id})
                            for topping in product['toppings']:
                                product_id = product_obj.search(
                                    [('product_tmpl_id', '=', topping['topping_id'])])
                                topping_id = order_line_obj.create(
                                    self._prepair_order_lines(product_id, sale_type_id, warehouse_id,
                                                              topping['qty'], [
                                                              ], order_id, order_line_id,
                                                              combo_id=combo_id, is_topping=True,
                                                              loyalty_discount_percent=False,
                                                              description=topping.get(
                                                                  'description'),
                                                              no_compute_price=True))
                                topping_id.update({'fe_uid': topping_id.id})
            line_ids = order_id.lines.filtered(
                lambda x: x.combo_id.id == combo_id.id)
            if line_ids:
                line_ids.write({'combo_seq': combo.get(
                    'combo_seq', False), 'combo_qty': combo.get('combo_qty', False)})
        if shipping_fee > 0 and sale_type_id.type_for_app == '2':
            order_line_fee_id = order_line_obj.create({
                'product_id': request.env.ref(
                    'phuclong_mobile_backend.product_shipping_fee').sudo().product_variant_id.id,
                'qty': 1,
                'uom_id': request.env.ref(
                    'phuclong_mobile_backend.product_shipping_fee').sudo().product_variant_id.uom_id.id,
                'price_unit': shipping_fee,
                'price_subtotal': shipping_fee,
                'price_subtotal_incl': shipping_fee,
                'order_id': order_id.id,
                'name': request.env.ref(
                    'phuclong_mobile_backend.product_shipping_fee').sudo().product_variant_id.name,
            })
            order_line_fee_id.update({'fe_uid': order_line_fee_id.id})

    def get_start_end_today(self, format_datetime=False):
        to_datetime = fields.Datetime.to_datetime
        today = to_datetime(fields.Date.context_today(request))
        convert_date_datetime_to_utc = request.env['res.users']._convert_date_datetime_to_utc
        start_today, end_today = convert_date_datetime_to_utc(fields.Datetime.to_string(
            today), True), convert_date_datetime_to_utc(fields.Datetime.to_string(today + timedelta(days=1, seconds=-1)), True)
        if format_datetime:
            return to_datetime(start_today), to_datetime(end_today)
        return start_today, end_today

    @validate_token
    @http.route('/api/v1/create_order', type="json", auth="none", methods=["POST"], csrf=False, cors="*")
    def create_order(self, *params, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        order_obj = request.env['pos.order'].sudo()
        datas = json.loads(request.httprequest.data)
        _logger.info(str(datas))
        partner_id = request.env['res.partner'].sudo().browse(
            int(datas.get('partner_id')))
        order_id = False
        start_today, end_today = self.get_start_end_today()
        if datas.get('order_id', False):
            check_order_id = request.env['pos.order'].sudo().browse(
                int(datas.get('order_id')))
            if check_order_id.order_in_app and check_order_id.state == 'draft' and fields.Datetime.from_string(start_today) <= check_order_id.date_order <= fields.Datetime.from_string(end_today):
                order_id = check_order_id
        if not order_id:
            order_id = order_obj.search([('order_in_app', '=', True), ('partner_id', '=', partner_id.id), ('state', '=',  'draft'), (
                'date_order', '>=', start_today), ('date_order', '<=', end_today)], order='date_order DESC', limit=1)
        warehouse_id = request.env['stock.warehouse'].browse(
            int(datas.get('warehouse_id', 0)))
        session_obj = request.env['pos.session'].sudo()
        pos_obj = request.env['pos.config'].sudo()
        payment_method_id = request.env['pos.payment.method'].sudo().search(
            [('use_for', '=', 'payoo')], limit=1)
        stock_location_id = request.env['stock.location'].sudo().search(
            [('warehouse_id', '=', warehouse_id.id or 0)])
        pos_id = pos_obj.search(
            [('stock_location_id', 'in', stock_location_id.ids or []), ('use_for_mobile', '=', True), ('payment_method_ids', '=', payment_method_id.id)], limit=1)
        session_id = session_obj.search([
            ('config_id', 'in', pos_id.ids or []), ('state', '=', 'opened'),
            ('start_at', '>=', start_today),
            ('start_at', '<=', end_today)
        ], limit=1)
        sale_type_id = request.env['pos.sale.type'].sudo().search([
            ('type_for_app', '=', int(datas.get('sale_type_id')))
        ], limit=1)
        request.env.user = partner_id.user_ids or request.env['res.users'].sudo(
        ).browse(1)
        if not session_id:
            _logger.info('1')
            return json.dumps({'status_code': 404,
                               'err': _('Hệ thống không tạo được đơn hàng!\nXin quý khách chọn cửa hàng khác và đặt hàng lại.')})
        if not pos_id:
            _logger.info('2')
            return json.dumps({'status_code': 404,
                               'err': _('Hệ thống không tạo được đơn hàng!\nXin quý khách chọn cửa hàng khác và đặt hàng lại.')})
        if not stock_location_id:
            _logger.info('3')
            return json.dumps({'status_code': 404,
                               'err': _('Hệ thống không tạo được đơn hàng!\nXin quý khách chọn cửa hàng khác và đặt hàng lại.')})
        if sale_type_id.id not in session_id.config_id.sale_type_ids.ids or not sale_type_id:
            _logger.info('4')
            return json.dumps({'status_code': 404,
                               'err': _('Hệ thống không tạo được đơn hàng!\nXin quý khách chọn cửa hàng khác và đặt hàng lại.')})
        if not session_id.config_id.payment_method_ids.filtered(lambda x: x.use_for == 'payoo'):
            _logger.info('5')
            return json.dumps({'status_code': 404,
                               'err': _('Hệ thống không tạo được đơn hàng!\nXin quý khách chọn cửa hàng khác và đặt hàng lại.')})
        voucher_lock_ids = []
        if not order_id:
            pos_reference = '%s-%s-%s-%s' % (
                session_id.config_id.name, session_id.id, 999, '{:04d}'.format((order_obj.search_count([
                    ('order_in_app', '=', True),
                    ('create_date', '>=', start_today),
                    ('create_date', '<=', end_today),
                    ('session_id', '=', session_id.id)
                ]) + 1)))
        else:
            if order_id.voucher_lock_ids:
                order_id.voucher_lock_ids.unlink()
            pos_reference = order_id.pos_reference
        rewards = []
        coupons = []
        coupon_combos = []
        coupon_code = ''
        exist_rewards = []
        exist_vouchers = []
        for combo in datas.get('combos', []):
            coupon = combo.get('coupon_code', False)
            if coupon:
                coupon_combos.append(coupon)
        for product in datas.get('products', []):
            reward_id = product.get('reward_id', 0)
            if reward_id:
                if int(reward_id) not in exist_rewards:
                    exist_rewards.append(int(reward_id))
                else:
                    _logger.info('11')
                    return json.dumps({'status_code': 404,
                                       'err': _('Hệ thống không tạo được đơn hàng!\nXin quý khách chọn cửa hàng khác và đặt hàng lại.')})
                rewards.append(int(reward_id))
            coupon = product.get('coupon_code', False)
            if coupon:
                coupons.append(coupon)
        if rewards:
            coupon_app_obj = request.env['coupon.app'].sudo()
            reward_ids = coupon_app_obj.search([('id', 'in', rewards)])
            if rewards != reward_ids.ids:
                _logger.info('9')
                return json.dumps({'status_code': 404,
                                   'err': _('Hệ thống không tạo được đơn hàng!\nXin quý khách chọn cửa hàng khác và đặt hàng lại.')})
            coupon_code += ','.join(reward_ids.mapped('name'))
            for reward_id in reward_ids:
                coupon_code_id, error = self.check_active_coupon_app(
                    reward_id, partner_id)
                if not coupon_code_id and error:
                    _logger.info(error)
                    return json.dumps({'status_code': 404,
                                       'err': _('Hệ thống không tạo được đơn hàng!\nXin quý khách chọn cửa hàng khác và đặt hàng lại.')})
                elif coupon_code_id and not error:
                    voucher_lock_ids += [(0, 0, {
                        'is_coupon_app': True,
                        'voucher_code': coupon_code_id.name,
                    })]
        if coupon_combos:
            for coupon in coupon_combos:
                coupon_data, error = self.check_active_coupon(
                    coupon, warehouse_id and warehouse_id.id or False)
                if not coupon_data and error:
                    _logger.info('11')
                    return json.dumps({'status_code': 404,
                                       'err': _('Hệ thống không tạo được đơn hàng!\nXin quý khách chọn cửa hàng khác và đặt hàng lại.')})
                elif coupon_data and not error:
                    if coupon_code != '':
                        coupon_code += ','
                    coupon_code += coupon
                    voucher_lock_ids += [(0, 0, {
                        'is_coupon': True,
                        'is_combo': True,
                        'voucher_code': coupon,
                    })]
        if coupons:
            for coupon in coupons:
                coupon_data, error = self.check_active_coupon(
                    coupon, warehouse_id and warehouse_id.id or False)
                if not coupon_data and error:
                    _logger.info('11')
                    return json.dumps({'status_code': 404,
                                       'err': _('Hệ thống không tạo được đơn hàng!\nXin quý khách chọn cửa hàng khác và đặt hàng lại.')})
                elif coupon_data and not error:
                    if coupon_code != '':
                        coupon_code += ','
                    coupon_code += coupon
                    voucher_lock_ids += [(0, 0, {
                        'is_coupon': True,
                        'voucher_code': coupon,
                    })]
        vouchers = datas.get('vouchers', [])
        if vouchers:
            payment_method_voucher_id = request.env['pos.payment.method'].sudo().search(
                [('use_for', '=', 'voucher')], limit=1)
            if not payment_method_voucher_id:
                _logger.info('7')
                return json.dumps({'status_code': 404,
                                   'err': _('Hệ thống không tạo được đơn hàng!\nXin quý khách chọn cửa hàng khác và đặt hàng lại.')})
            for voucher in vouchers:
                voucher_code = voucher.get('voucher', False)
                voucher_data, error = self.check_active_voucher(
                    voucher_code, warehouse_id and warehouse_id.id or False)
                if not voucher_data and error:
                    _logger.info(error)
                    return json.dumps({'status_code': 404,
                                       'err': _('Hệ thống không tạo được đơn hàng!\nXin quý khách chọn cửa hàng khác và đặt hàng lại.')})
                elif voucher_data and not error:
                    if voucher_code not in exist_vouchers:
                        exist_vouchers.append(voucher_code)
                        voucher_lock_ids += [(0, 0, {
                            'is_voucher': True,
                            'voucher_code': voucher_code,
                            'discount_amount': voucher.get('amount', 0)
                        })]
                    else:
                        _logger.info('8')
                        return json.dumps({'status_code': 404,
                                           'err': _('Hệ thống không tạo được đơn hàng!\nXin quý khách chọn cửa hàng khác và đặt hàng lại.')})

        if not order_id:
            order_id = order_obj.with_context(mail_create_nosubscribe=True).create({
                'pos_reference': pos_reference,
                'date_order': fields.Datetime.to_string(fields.Datetime.now()),
                'cashier_id': session_id.cashier_id and session_id.cashier_id.id or False,
                'partner_id': partner_id.id,
                'session_id': session_id.id,
                'sale_type_id': sale_type_id.id,
                'address_id': datas.get('address_id', False),
                'amount_total': datas.get('amount_total', 0),
                'amount_voucher': datas.get('amount_voucher', 0),
                'order_in_app': True,
                'description_for_app': datas.get('note', ''),
                'delivery_address_note': datas.get('delivery_address_note', ''),
                'amount_tax': datas.get('amount_total', 0) * 10 / 100,
                'amount_paid': 0,
                'amount_return': 0,
                'company_id': 1,
                'state': 'draft',
                'order_status_app': 'new',
                'delivery_address': datas.get('delivery_address', ''),
                'name_receiver': datas.get('name_receiver', ''),
                'phone_number_receiver': datas.get('phone_number_receiver', ''),
                'coupon_code': coupon_code,
                'voucher_lock_ids': voucher_lock_ids
            })
            order_id.note_label = order_id.id or False
        else:
            order_id.write({
                'date_order': fields.Datetime.to_string(fields.Datetime.now()),
                'cashier_id': session_id.cashier_id and session_id.cashier_id.id or False,
                'session_id': session_id.id,
                'sale_type_id': sale_type_id.id,
                'address_id': datas.get('address_id', False),
                'amount_total': datas.get('amount_total', 0),
                'amount_voucher': datas.get('amount_voucher', 0),
                'description_for_app': datas.get('note', ''),
                'delivery_address_note': datas.get('delivery_address_note', ''),
                'amount_tax': datas.get('amount_total', 0) * 10 / 100,
                'delivery_address': datas.get('delivery_address', ''),
                'name_receiver': datas.get('name_receiver', ''),
                'phone_number_receiver': datas.get('phone_number_receiver', ''),
                'coupon_code': coupon_code,
                'voucher_lock_ids': voucher_lock_ids
            })
        if order_id.lines:
            order_id.lines.unlink()
        self._create_order_lines(sale_type_id, warehouse_id, order_id, datas.get('shipping_fee', 0),
                                 datas.get('combos', []),
                                 datas.get('products', []))
        if order_id.amount_total == 0 and order_id.lines and datas.get('payment_confirmed', False):
            self._payment_confirmed(order_id)
        data_payoo, checksum_value = self._repair_data_payoo(
            order_id, partner_id)
        data_response = {
            'status_code': 200,
            'order_id': order_id.id,
            'order_name': order_id.name,
            'order_date': fields.Datetime.to_string(fields.Datetime.context_timestamp(request, order_id.date_order)),
            'checksum_value': checksum_value,
            'order_info_xml': data_payoo,
        }
        return data_response

    @validate_token
    @http.route('/api/v1/reorder', type="http", auth="none", methods=["POST"], csrf=False, cors="*")
    def reorder(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        pos_obj = request.env['pos.config'].sudo()
        order_obj = request.env['pos.order'].sudo()
        session_obj = request.env['pos.session'].sudo()
        order_id = request.env['pos.order'].sudo().browse(
            int(payload.get('order_id', 0)))
        if order_id.session_id.state == 'opened' and order_id.session_id.config_id.use_for_mobile:
            order_id.sudo().write({
                'date_order': fields.Datetime.to_string(fields.Datetime.now())
            })
            data_payoo, checksum_value = self._repair_data_payoo(
                order_id, order_id.partner_id)
            return valid_response({
                'order_id': order_id.id,
                'order_name': order_id.name,
                'order_date': fields.Datetime.to_string(fields.Datetime.context_timestamp(request, order_id.date_order)),
                'checksum_value': checksum_value,
                'order_info_xml': data_payoo
            })
        else:
            if order_id.session_id.config_id.use_for_mobile:
                start_today, end_today = self.get_start_end_today()
                session_id = session_obj.search(
                    [('config_id', '=', order_id.session_id.config_id.id), ('state', '=', 'opened'),
                     ('start_at', '>=', start_today),
                     ('start_at', '<=', end_today)], limit=1)
                if session_id:
                    order_id.sudo().write({
                        'pos_reference': '%s-%s-%s-%s' % (
                            session_id.config_id.name, session_id.id, 999, '{:04d}'.format((order_obj.search_count(
                                [('order_in_app', '=', True),
                                 ('create_date', '>=', start_today),
                                 ('create_date', '<=', end_today),
                                 ('session_id', '=', session_id.id)]) + 1))),
                        'date_order': datetime.strptime(fields.Datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
                                                        '%d-%m-%Y %H:%M:%S'),
                        'session_id': session_id.id
                    })
                    data_payoo, checksum_value = self._repair_data_payoo(
                        order_id, order_id.partner_id)
                    return valid_response({
                        'order_id': order_id.id,
                        'order_name': order_id.name,
                        'order_date': fields.Datetime.to_string(fields.Datetime.context_timestamp(request, order_id.date_order)),
                        'checksum_value': checksum_value,
                        'order_info_xml': data_payoo
                    })
                else:
                    pos_id = pos_obj.search(
                        [('stock_location_id', '=', order_id.session_id.config_id.stock_location_id.id),
                         ('use_for_mobile', '=', True)])
                    if pos_id:
                        session_id = session_obj.search(
                            [('config_id', 'in', pos_id.ids), ('state', '=', 'opened'),
                             ('start_at', '>=', start_today),
                             ('start_at', '<=', end_today)], limit=1)
                        if session_id:
                            order_id.sudo().write({
                                'pos_reference': '%s-%s-%s-%s' % (
                                    session_id.config_id.name, session_id.id, 999,
                                    '{:04d}'.format((order_obj.search_count(
                                        [('order_in_app', '=', True),
                                         ('create_date', '>=', start_today),
                                         ('create_date', '<=', end_today),
                                         ('session_id', '=', session_id.id)]) + 1))),
                                'date_order': datetime.strptime(fields.Datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
                                                                '%d-%m-%Y %H:%M:%S'),
                                'session_id': session_id.id,
                            })
                            data_payoo, checksum_value = self._repair_data_payoo(
                                order_id, order_id.partner_id)
                            return valid_response({
                                'order_id': order_id.id,
                                'order_name': order_id.name,
                                'order_date': fields.Datetime.to_string(fields.Datetime.context_timestamp(request, order_id.date_order)),
                                'checksum_value': checksum_value,
                                'order_info_xml': data_payoo
                            })
                        else:
                            return invalid_response('err',
                                                    _('Hệ thống không tạo được đơn hàng!\nXin quý khách chọn cửa hàng khác và đặt hàng lại.'))
                    else:
                        return invalid_response('err',
                                                _('Hệ thống không tạo được đơn hàng!\nXin quý khách chọn cửa hàng khác và đặt hàng lại.'))
            else:
                return invalid_response('err',
                                        _('Hệ thống không tạo được đơn hàng!\nXin quý khách chọn cửa hàng khác và đặt hàng lại.'))

    def _repair_data_payoo(self, order_id, partner_id):
        base_url = request.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        payoo_merchant_id = request.env['ir.config_parameter'].sudo(
        ).get_param('payoo_merchant_id')
        payoo_merchant_secret_key = request.env['ir.config_parameter'].sudo(
        ).get_param('payoo_merchant_secret_key')
        payoo_request_ip = request.env['ir.config_parameter'].sudo(
        ).get_param('payoo_request_ip')
        data_payoo = '''<shops><shop><session></session><username>mobile_sdk_demo_external</username><shop_id>%s</shop_id><shop_title>'Phúc Long'</shop_title><shop_domain>http://localhost</shop_domain><shop_back_url>%s</shop_back_url><order_no>%s</order_no><order_cash_amount>%s</order_cash_amount><order_ship_date>%s</order_ship_date><order_ship_days>1</order_ship_days><order_description>%s</order_description><notify_url>%s</notify_url><validity_time>%s</validity_time><customer><name>%s</name><phone>%s</phone><email>%s</email></customer><card><customerid></customerid><token></token><card_token></card_token></card><JsonResponse>%s</JsonResponse></shop></shops>''' % (
            payoo_merchant_id,
            'payoosdk1457://postbacksdkurl', order_id.name,
            int(order_id.amount_total - order_id.amount_voucher),
            (order_id.date_order + timedelta(hours=7)
             ).strftime('%d/%m/%Y'), order_id.description_for_app,
            '%s/payment_confirmed/%s' % (base_url, order_id.id),
            (fields.Datetime.now() + timedelta(days=1)
             ).strftime('%Y%m%d%H%M%S'), partner_id.name or '',
            partner_id.mobile or '', partner_id.email or '', 'true')
        checksum_value = hashlib.sha512(
            ('%s%s' % (payoo_merchant_secret_key, data_payoo)).encode('utf-8')).hexdigest()
        order_id.sudo().write({
            'payoo_request': data_payoo,
            'payoo_request_ip': payoo_request_ip,
            'payoo_checksum': checksum_value
        })
        return data_payoo, checksum_value

    @validate_token
    @http.route('/api/v1/get_loyalty', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def get_shipping_fee(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        partner_obj = request.env['res.partner'].sudo()
        res = {}
        partner_id = partner_obj.browse(int(payload.get('partner_id', False)))
        program_obj = request.env['loyalty.program'].sudo()
        start_today, end_today = self.get_start_end_today()
        program_event_id = program_obj.sudo().search(
            [('program_type', '=', 'event_program'),
             ('from_date', '<=', start_today),
             ('to_date', '>=', end_today)])
        program_base_id = program_obj.sudo().search(
            [('program_type', '=', 'base_program'), ('from_date', '<=', start_today),
             ('to_date', '>=', end_today)])
        if program_event_id:
            res.update({
                'compute_point': {
                    'apply': True,
                    'pp_currency': program_event_id.pp_currency or None,
                    'pp_order': program_event_id.pp_order or None,
                    'pp_product': program_event_id.pp_product or None,
                    'rounding_method': program_event_id.rounding_method or None,
                    'multiple_point': program_event_id.multiply_point_loyalty or 1,
                    'minimum_point': program_event_id.minimum_point or 0
                }
            })
        elif program_base_id:
            res.update({
                'compute_point': {
                    'apply': True,
                    'pp_currency': program_base_id.pp_currency or None,
                    'pp_order': program_base_id.pp_order or None,
                    'pp_product': program_base_id.pp_product or None,
                    'rounding_method': program_base_id.rounding_method or None,
                    'multiple_point': program_base_id.multiply_point_loyalty or 1,
                    'minimum_point': program_base_id.minimum_point or 0
                }
            })
        else:
            res.update({
                'compute_point': {
                    'apply': False,
                    'pp_currency': None,
                    'pp_order': None,
                    'pp_product': None,
                    'rounding_method': None,
                    'multiple_point': None,
                    'minimum_point': None
                }
            })
        if partner_id and partner_id.loyalty_level_id:
            rule_detail = []
            for rule in partner_id.loyalty_level_id.rule_ids.filtered(
                    lambda x: x.from_date <= date.today() and x.to_date >= date.today()):
                if rule.discount_type == 'category':
                    product_ids = request.env['product.template'].sudo().search([('categ_id', 'in',
                                                                                  json.loads(
                                                                                      rule.categories_dom))]).ids
                    rule_detail.append({
                        'discount_percent': rule.discount_percent,
                        'products': product_ids
                    })
                else:
                    rule_detail.append({
                        'discount_percent': rule.discount_percent,
                        'products': rule.product_ids.ids
                    })
            res.update({
                'discount_rule': {
                    'apply_all': partner_id.loyalty_level_id.discount_percent,
                    'rule_detail': rule_detail
                }
            })
        else:
            res.update({
                'discount_rule': {
                    'apply_all': 0.0,
                    'rule_detail': []
                }
            })
        return valid_response(res)

    @http.route('/api/v1/get_policy_terms', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def get_policy_terms(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        return valid_response(
            request.env['policy.terms'].sudo().search_read([], fields=['name', 'url', 'priority', 'hide']))

    def _payment_confirmed(self, order_id, response_data=False):
        if order_id:
            payment_ids = []
            payment_method_voucher_id = request.env['pos.payment.method'].sudo().search(
                [('use_for', '=', 'voucher')], limit=1)
            for voucher_lock_id in order_id.voucher_lock_ids:
                if voucher_lock_id.is_coupon_app and voucher_lock_id.order_line_id and voucher_lock_id.res_id:
                    voucher_lock_id.order_line_id.write(
                        {'coupon_app_id': voucher_lock_id.res_id})
                if voucher_lock_id.is_voucher or voucher_lock_id.is_coupon:
                    request.env['sale.promo.header'].sudo().update_set_done_coupon(
                        [(voucher_lock_id.voucher_code, 1)], order_id.pos_reference, order_id.partner_id and order_id.partner_id.id or False, order_id.warehouse_id and order_id.warehouse_id.id or False)
                    if voucher_lock_id.is_voucher:
                        payment_ids += [(0, 0, {
                            'payment_date': str(fields.Datetime.now()),
                            'payment_method_id': payment_method_voucher_id.id or False,
                            'currency_name': 'VND',
                            'voucher_code': voucher_lock_id.voucher_code,
                            'amount': voucher_lock_id.discount_amount,
                        })]
            if response_data:
                payoo_payment_method = str(
                    response_data['PaymentMethod']) if 'PaymentMethod' in response_data else False
                payoo_card_issuance_type = str(
                    response_data['CardIssuanceType']) if 'CardIssuanceType' in response_data else False
                payoo_card_issuance_type = str(
                    response_data['CardIssuanceType']) if 'CardIssuanceType' in response_data else False
                payoo_bank_name = str(
                    response_data['BankName']) if 'BankName' in response_data else False
                payoo_card_number = str(
                    response_data['CardNumber']) if 'CardNumber' in response_data else False
                payoo_billing_code = str(
                    response_data['BillingCode']) if 'BillingCode' in response_data else False
                payment_method_id = request.env['pos.payment.method'].sudo().search(
                    [('use_for', '=', 'payoo')], limit=1)
                payment_ids += [(0, 0, {
                    'payment_date': str(fields.Datetime.now()),
                    'payment_method_id': payment_method_id.id or False,
                    'currency_name': 'VND',
                    'amount': order_id.amount_total - order_id.amount_voucher,
                    'payoo_payment_method': payoo_payment_method,
                    'payoo_card_issuance_type': payoo_card_issuance_type,
                    'payoo_bank_name': payoo_bank_name,
                    'payoo_card_number': payoo_card_number,
                    'payoo_billing_code': payoo_billing_code,
                })]
            if order_id.partner_id.loyalty_level_id:
                total_amount_point = order_id.amount_total - sum(
                    order_id.lines.filtered(lambda x: x.combo_id or x.product_id.id == request.env.ref(
                        'phuclong_mobile_backend.product_shipping_fee').sudo().product_variant_id.id).mapped('price_subtotal_incl'))
                program_obj = request.env['loyalty.program'].sudo()
                program_event_id = program_obj.sudo().search(
                    [('program_type', '=', 'event_program'),
                        ('from_date', '<=', str(datetime.today().date())),
                        ('to_date', '>=', str(datetime.today().date()))])
                if program_event_id:
                    if program_event_id.pp_currency > 0:
                        pp_currency = round((total_amount_point / program_event_id.pp_currency) + 0.5) if program_event_id.rounding_method == 'up' else int(
                            total_amount_point / program_event_id.pp_currency)
                    else:
                        pp_currency = 0
                    pp_order = program_event_id.pp_order
                    product_qty = order_id.lines.filtered(
                        lambda x: x.is_topping_line == False and x.product_id.id != request.env.ref(
                            'phuclong_mobile_backend.product_shipping_fee').sudo().product_variant_id.id or not x.combo_id)
                    pp_product = program_event_id.pp_product * \
                        (len(product_qty) + 1)
                    total_point = int(
                        pp_currency + pp_order + pp_product)
                else:
                    program_id = program_obj.sudo().search(
                        [('program_type', '=', 'base_program'),
                            ('from_date', '<=', str(datetime.today().date())),
                            ('to_date', '>=', str(datetime.today().date()))])
                    if program_id.pp_currency > 0:
                        pp_currency = round((total_amount_point / program_id.pp_currency) + 0.5) if program_id.rounding_method == 'up' else int(
                            total_amount_point / program_id.pp_currency)
                    else:
                        pp_currency = 0
                    pp_order = program_id.pp_order
                    product_qty = order_id.lines.filtered(
                        lambda x: x.is_topping_line == False and x.product_id.id != request.env.ref(
                            'phuclong_mobile_backend.product_shipping_fee').sudo().product_variant_id.id and not x.combo_id)
                    pp_product = program_id.pp_product * \
                        (len(product_qty) + 1)
                    total_point = int(
                        pp_currency + pp_order + pp_product)
                order_id.write({
                    'state': 'paid',
                    'point_won': total_point,
                    'loyalty_points': total_point,
                    'partner_current_point': order_id.partner_id.current_point_act + total_point,
                    'partner_total_point': order_id.partner_id.total_point_act + total_point,
                    'partner_loyalty_level_id': order_id.partner_id.loyalty_level_id.id,
                    'payment_ids': payment_ids
                })
                partner = order_id.partner_id
                prior_point_act = partner.total_point_act or 0.0
                exchange_point = order_id.loyalty_points or 0.0
                point_won = order_id.point_won or 0.0
                year_discount_birth = partner.year_discount_birth or 0.0
                current_point_act_before = partner.current_point_act
                current_point_act = partner.current_point_act + point_won
                partner_total_point_act = partner.total_point_act + exchange_point
                count_discount_birth = partner.count_discount_birth
                partner.write({
                    'total_point_act': partner_total_point_act,
                    'current_point_act': current_point_act,
                    'year_discount_birth': year_discount_birth,
                    'count_discount_birth': count_discount_birth,
                })
                vals = {
                    'partner_id': partner.id,
                    'mobile': partner.mobile,
                    'bill_id': order_id.id,
                    'bill_amount': order_id.amount_total,
                    'bill_date': order_id.date_order,
                    'order_type': 'POS Order',
                    'exchange_point': exchange_point,
                    'point_up': point_won,
                    'point_down': exchange_point - point_won,
                    'prior_point_act': prior_point_act,
                    'current_point_act': partner_total_point_act,
                    'prior_total_point_act': current_point_act_before,
                    'current_total_point_act': current_point_act,
                }
                request.env['loyalty.point.history'].create(vals)
            else:
                total_amount_point = order_id.amount_total - sum(
                    order_id.lines.filtered(lambda x: x.combo_id or x.product_id.id == request.env.ref(
                        'phuclong_mobile_backend.product_shipping_fee').sudo().product_variant_id.id).mapped('price_subtotal_incl'))
                if order_id.amount_total >= 300000:
                    program_obj = request.env['loyalty.program'].sudo()
                    program_event_id = program_obj.sudo().search(
                        [('program_type', '=', 'event_program'),
                            ('from_date', '<=', str(datetime.today().date())),
                            ('to_date', '>=', str(datetime.today().date()))])
                    if program_event_id:
                        if program_event_id.pp_currency > 0:
                            pp_currency = round((total_amount_point / program_event_id.pp_currency) + 0.5) if program_event_id.rounding_method == 'up' else int(
                                total_amount_point / program_event_id.pp_currency)
                        else:
                            pp_currency = 0
                        pp_order = program_event_id.pp_order
                        product_qty = order_id.lines.filtered(
                            lambda x: x.is_topping_line == False and x.product_id.id != request.env.ref(
                                'phuclong_mobile_backend.product_shipping_fee').sudo().product_variant_id.id and not x.combo_id)
                        pp_product = program_event_id.pp_product * \
                            (len(product_qty) + 1)
                        total_point = int(
                            pp_currency + pp_order + pp_product)
                    else:
                        program_id = program_obj.sudo().search(
                            [('program_type', '=', 'base_program'),
                                ('from_date', '<=', str(
                                    datetime.today().date())),
                                ('to_date', '>=', str(datetime.today().date()))])
                        if program_id.pp_currency > 0:
                            pp_currency = round((total_amount_point / program_id.pp_currency) + 0.5) if program_id.rounding_method == 'up' else int(
                                total_amount_point / program_id.pp_currency)
                        else:
                            pp_currency = 0
                        pp_order = program_id.pp_order
                        product_qty = order_id.lines.filtered(
                            lambda x: x.is_topping_line == False and x.product_id.id != request.env.ref(
                                'phuclong_mobile_backend.product_shipping_fee').sudo().product_variant_id.id and not x.combo_id)
                        pp_product = program_id.pp_product * \
                            (len(product_qty) + 1)
                        total_point = int(
                            pp_currency + pp_order + pp_product)
                    level_id = request.env['loyalty.level'].sudo().search(
                        [('from_point_act', '<=', total_point), ('to_point_act', '>=', total_point)])
                    order_id.write({
                        'state': 'paid',
                        'point_won': total_point,
                        'loyalty_points': total_point,
                        'partner_current_point': order_id.partner_id.current_point_act + total_point,
                        'partner_total_point': order_id.partner_id.total_point_act + total_point,
                        'partner_loyalty_level_id': level_id.id,
                        'payment_ids': payment_ids
                    })
                    partner = order_id.partner_id
                    prior_point_act = partner.total_point_act or 0.0
                    exchange_point = order_id.loyalty_points or 0.0
                    point_won = order_id.point_won or 0.0
                    year_discount_birth = partner.year_discount_birth or 0.0
                    current_point_act_before = partner.current_point_act
                    current_point_act = partner.current_point_act + point_won
                    partner_total_point_act = partner.total_point_act + exchange_point
                    count_discount_birth = partner.count_discount_birth
                    partner.write({
                        'can_loyalty_level': True,
                        'total_point_act': partner_total_point_act,
                        'current_point_act': current_point_act,
                        'year_discount_birth': year_discount_birth,
                        'count_discount_birth': count_discount_birth,
                    })
                    vals = {
                        'partner_id': partner.id,
                        'mobile': partner.mobile,
                        'bill_id': order_id.id,
                        'bill_amount': order_id.amount_total,
                        'bill_date': order_id.date_order,
                        'order_type': 'POS Order',
                        'exchange_point': exchange_point,
                        'point_up': point_won,
                        'point_down': exchange_point - point_won,
                        'prior_point_act': prior_point_act,
                        'current_point_act': partner_total_point_act,
                        'prior_total_point_act': current_point_act_before,
                        'current_total_point_act': current_point_act,
                    }
                    request.env['loyalty.point.history'].create(vals)
                else:
                    order_id.write({
                        'state': 'paid',
                        'payment_ids': payment_ids
                    })

    @http.route('/payment_confirmed/<id>', type="http", auth="none", methods=["POST"], csrf=False, cors="*")
    def payment_confirmed(self, id=None, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        order_id = request.env['pos.order'].sudo().search(
            [('id', '=', id)], limit=1)
        if order_id and payload.get('NotifyData', False):
            res = base64.b64decode(payload.get('NotifyData')).decode('utf-8')
            data = json.loads(res)
            order_id.write({
                'payoo_response': json.dumps(data, indent=4),
            })
            if 'ResponseData' in data:
                response_data = json.loads(data['ResponseData'])
                if 'PaymentStatus' in response_data and response_data['PaymentStatus'] == 1:
                    self._payment_confirmed(order_id, response_data)
                    order_id.notification_pos()
                    return 'NOTIFY_RECEIVED'
            # request.env['pos.order'].sudo().notification_pos()

    @http.route('/api/v1/get_product_lock', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def get_product_lock(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        warehouse_id = request.env['stock.warehouse'].browse(
            int(payload.get('warehouse_id', 0)))
        res = []
        if warehouse_id:
            lock_product_id = request.env['pos.product.lock'].sudo().search(
                [('warehouse_id', '=', warehouse_id.id)])
            if lock_product_id:
                res = lock_product_id.product_ids.ids
        else:
            return invalid_response("Invalid data", "warehouse_id not in params", 400)
        if payload.get("sale_type_id", 0) == '2':
            product_size_id = request.env['product.size'].sudo().search(
                [('name', 'in', ['HOT', 'Hot', 'hot'])])
            product_ids = request.env['product.template'].sudo().search(
                [('size_id', '=', product_size_id.id)])
            res += product_ids.ids
        return valid_response(list(set(res)))

    def get_order_lines(self, order_id):
        res = []
        list_options = {
            'none': 'Không',
            'below': 'Ít',
            'normal': 'Bình Thường',
            'over': 'Nhiều'
        }
        for line_id in order_id.lines.filtered(
                lambda x: x.is_topping_line == False and x.product_id.product_tmpl_id.id != request.env.ref(
                    'phuclong_mobile_backend.product_shipping_fee').id):
            toppings = [{
                'product_id': x.product_id.product_tmpl_id.id,
                'qty': x.qty,
                'price': x.price_unit,
                'subtotal': x.price_subtotal_incl,
                'discount': x.loyalty_discount_percent
            } for x in order_id.lines.filtered(lambda x: x.related_line_id == line_id.id)]
            reward_id = None
            if line_id.coupon_app_id:
                reward_id = line_id.coupon_app_id.id
            else:
                voucher_lock_id = order_id.voucher_lock_ids.filtered(
                    lambda v: v.is_coupon_app and v.order_line_id and v.order_line_id.id == line_id.id and v.res_id)
                if voucher_lock_id:
                    reward_id = voucher_lock_id[0].res_id
            if reward_id:
                valid, reward_data = self.__get_coupon({
                    'partner_id': order_id.partner_id,
                    'reward_id': reward_id,
                    'voucher_type': 'reward',
                })
                if not valid:
                    reward_data = []
            else:
                reward_data = []
            res.append({
                'product_id': line_id.product_id.product_tmpl_id.id,
                'product_name': line_id.product_id.product_tmpl_id.name,
                'qty': line_id.qty,
                'price': line_id.price_unit,
                'description': line_id.note,
                'subtotal': line_id.price_subtotal_incl,
                'discount': line_id.loyalty_discount_percent,
                'combo': line_id.combo_id.name or None,
                'toppings': toppings,
                'reward_id': reward_id,
                'reward_data': reward_data,
                'materials': [{
                    'name': x.option_id.name,
                    'code': list_options[x.option_type]
                } for x in line_id.option_ids],
            })
        return res

    @validate_token
    @http.route('/api/v1/get_orders', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def get_orders(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        res, error_response = self._get_orders(payload)
        if not res:
            return error_response
        return valid_response(self._response_null(res))

    def _get_order(self, order_id):
        if order_id.state == 'draft' and order_id.order_status_app == 'new':
            status = 'new'
        elif order_id.state in ['paid', 'done'] and order_id.order_status_app == 'new':
            status = 'paid'
        elif order_id.state in ['paid', 'done'] and order_id.order_status_app == 'done':
            status = 'done'
        else:
            status = 'cancel'
        store_id = request.env['res.store'].sudo().search(
            [('warehouse_id', '=', order_id.session_id.config_id.stock_location_id.warehouse_id.id)])
        vouchers = []
        for voucher_lock_id in order_id.voucher_lock_ids:
            if voucher_lock_id.is_voucher:
                valid, voucher_data = self.__get_coupon({
                    'partner_id': order_id.partner_id,
                    'voucher_id': voucher_lock_id.res_id,
                    'voucher_type': 'voucher',
                })
                if not valid:
                    voucher_data = []
                vouchers.append({
                    'voucher': voucher_lock_id.voucher_code,
                    'amount': voucher_lock_id.discount_amount,
                    'voucher_data': voucher_data
                })
        return {
            'order_id': order_id.id,
            'order_name': order_id.name or None,
            'sale_type': order_id.sale_type_id.name or None,
            'date_order': order_id.date_order or None,
            'delivery_address': order_id.delivery_address or None,
            'address_id': order_id.address_id and order_id.address_id.id or False,
            'warehouse_id': order_id.warehouse_id and order_id.address_id.id or None,
            'note': order_id.description_for_app or None,
            'vouchers': vouchers,
            'status': status,
            'voucher_lock_ids': order_id.voucher_lock_ids and order_id.voucher_lock_ids.read() or [],
            'payments': [],
            'products': self.get_order_lines(order_id),
            'total_amount': order_id.amount_total,
            'amount_voucher': order_id.amount_voucher,
            'store_id': store_id.id or None,
            'store_name': store_id.name or None,
            'store_address': store_id.address or None,
            'shipping_fee': order_id.lines.filtered(
                lambda x: x.product_id.product_tmpl_id.id == request.env.ref(
                    'phuclong_mobile_backend.product_shipping_fee').id).price_unit or None
        }

    def _get_orders(self, payload):
        order_id_int = int(payload.get('order_id', 0))
        partner_id_int = int(payload.get('partner_id', 0))
        order_obj = request.env['pos.order'].sudo()
        partner_obj = request.env['res.partner'].sudo()
        res = []
        if order_id_int:
            order_id = order_obj.sudo().search(
                [('id', '=', int(order_id_int)), ('order_in_app', '=', True)], limit=1)
            if order_id:
                res.append(self._get_order(order_id))
            else:
                return False, invalid_response("Not Found", "ID Đơn hàng không tồn tại", 404)
        else:
            partner_id = partner_obj.sudo().browse(partner_id_int)
            if partner_id:
                ids = []
                order_ids = order_obj.sudo().search(
                    [('partner_id', '=', partner_id.id), ('order_in_app', '=', True), ('state', '=', 'draft'), ('order_status_app', '=', 'new')])
                for order_id in order_ids:
                    ids.append(order_id.id)
                    res.append(self._get_order(order_id))
                order_ids = order_obj.sudo().search(
                    [('partner_id', '=', partner_id.id), ('order_in_app', '=', True), ('state', 'in', ['paid', 'done'])], limit=5)
                for order_id in order_ids:
                    ids.append(order_id.id)
                    res.append(self._get_order(order_id))
                order_ids = order_obj.sudo().search(
                    [('partner_id', '=', partner_id.id), ('order_in_app', '=', True), ('id', 'not in', ids)], limit=5)
                for order_id in order_ids:
                    res.append(self._get_order(order_id))
            else:
                return False, invalid_response("Not Found", "ID Khách hàng không tồn tại", 404)
        return res, False

    @http.route('/api/v1/init_data', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def init_data(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        return valid_response({
            'maximum_range': float(
                request.env['ir.config_parameter'].sudo().get_param('phuclong_mobile_backend.maximum_km'))
        })

    @http.route('/api/v1/get_status_update_card', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def get_status_update_card(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        if payload.get('request_id', False):
            request_id = request.env['request.update.card'].sudo().browse(
                payload['request_id'])
            states = dict(
                self._fields['state']._description_selection(self.env))
            return valid_response({
                'status': states.get(request_id.state, ''),
                'description': ''
            })

    @http.route('/api/v1/get_issue', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def get_issue(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        return valid_response(
            request.env['config.issue'].sudo().search_read([], fields=['id', 'name']))

    @validate_token
    @http.route('/api/v1/get_coupon', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def get_coupon(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        return self._get_coupon(payload)

    def _get_coupon(self, payload):
        valid, result = self.__get_coupon(payload)
        if valid:
            return valid_response(result)
        return result

    def _response_null(self, old_data, lists=[], nulls=[]):
        if isinstance(old_data, list):
            for data in old_data:
                if isinstance(data, dict):
                    for key in data:
                        if key in lists:
                            if not data[key]:
                                data[key] = []
                                continue
                        if key in nulls:
                            if not data[key]:
                                data[key] = None
                                continue
                        else:
                            if not data[key] and not isinstance(data[key], (int, float, list, tuple, dict)):
                                data[key] = None
                                continue
                            if isinstance(data[key], (list, dict)):
                                data[key] = self._response_null(
                                    data[key], lists)
                                continue
        if isinstance(old_data, dict):
            for key in data:
                if key in lists:
                    if not data[key]:
                        data[key] = []
                        continue
                else:
                    if not data[key] and not isinstance(data[key], (int, float, list, tuple, dict)):
                        data[key] = None
                        continue
                    if isinstance(data[key], (list, dict)):
                        data[key] = self._response_null(
                            data[key], lists)
                        continue
        return old_data

    def check_active_coupon_app(self, coupon_app_id, partner_id):
        if request.env['crm.voucher.lock'].check_lock_voucher(coupon_app_id.name):
            return False, _('Mã quà tặng đã bị khoá, Vui lòng kiểm tra lại !!')
        today = fields.Date.context_today(request)
        if coupon_app_id.partner_id != partner_id:
            return False, _('Mã quà tặng không khả dụng với bạn, Vui lòng kiểm tra lại !!')
        if coupon_app_id.state == 'expire' or (coupon_app_id.effective_date_from and coupon_app_id.effective_date_from > today) or (coupon_app_id.effective_date_to and coupon_app_id.effective_date_to < today):
            return False, _('Mã quà tặng đã hết hạn(%s), Vui lòng kiểm tra lại !!' % coupon_app_id.effective_date_to or '')
        if coupon_app_id.state == 'used' and coupon_app_id.pos_order_id:
            return False, _('Mã quà tặng đã được sử dụng ở Đơn hàng: %s, CH sử dụng: %s, Ngày giờ: %s' % (coupon_app_id.pos_order_id.name, coupon_app_id.warehouse_id and coupon_app_id.warehouse_id.name or '', coupon_app_id.date_used or ''))
        if coupon_app_id.state != 'new' or coupon_app_id.pos_order_id:
            return False, _('Mã quà tặng không khả dụng, Vui lòng kiểm tra lại !!')
        if coupon_app_id.type == 'birthday':
            if partner_id.month_birthday != today.month:
                return False, _('Mã quà tặng không khả dụng trong tháng sinh nhật, Vui lòng kiểm tra lại !!')
        return coupon_app_id, False

    def check_active_coupon(self, coupon_code, warehouse_id):
        if request.env['crm.voucher.lock'].check_lock_voucher(coupon_code):
            return False, _('Coupon đã bị khoá, Vui lòng kiểm tra lại !!')
        coupon_data = request.env['crm.voucher.publish'].sudo(
        ).with_context(from_mobile_app=True).check_coupon_apply_combo({'code': coupon_code}, warehouse_id)
        if coupon_data and len(coupon_data):
            if coupon_data[0] in ['employee', 'product_coupon']:
                return False, _('Mã quà tặng không khả dụng, Vui lòng kiểm tra lại !!')
            if coupon_data[0] == 'date':
                return False, _('Coupon đã hết hạn (%s), Vui lòng kiểm tra lại !!' % coupon_data[1])
            if coupon_data[0] == 'count':
                return False, _('Coupon đã hết xài hết số lần sử dụng cho phép !!')
            if coupon_data[0] == 'combo':
                return coupon_data, False
        coupon_data = request.env['sale.promo.header'].sudo(
        ).with_context(from_mobile_app=True).check_coupon_apply({'code': coupon_code}, 'coupon', warehouse_id)
        if coupon_data and len(coupon_data):
            if coupon_data[0] == 'date':
                return False, _('Coupon đã hết hạn (%s), Vui lòng kiểm tra lại !!' % coupon_data[1])
            if coupon_data[0] == 'count':
                return False, _('Mã Coupon đã được sử dụng ở Đơn hàng: %s, CH sử dụng: %s, Ngày giờ: %s' % (coupon_data[2], coupon_data[3] or '', coupon_data[4]))
            return coupon_data, False
        return False, False

    def check_active_voucher(self, voucher_code, warehouse_id):
        if request.env['crm.voucher.lock'].check_lock_voucher(voucher_code):
            return False, _('Voucher đã bị khoá, Vui lòng kiểm tra lại !!')
        voucher_data = request.env['sale.promo.header'].sudo(
        ).with_context(from_mobile_app=True).check_coupon_apply({'code': voucher_code}, 'voucher', warehouse_id)
        if voucher_data and len(voucher_data):
            if voucher_data[0] == 'date':
                return False, _('Voucher đã hết hạn (%s), Vui lòng kiểm tra lại !!' % voucher_data[1])
            if voucher_data[0] == 'count':
                return False, _('Mã Voucher đã được sử dụng ở Đơn hàng: %s, CH sử dụng: %s, Ngày giờ: %s' % (voucher_data[2], voucher_data[3] or '', voucher_data[4]))
            return voucher_data, False
        return False, False

    def __get_coupon(self, payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        request.env['coupon.app'].cron_expire_coupon_app()
        partner_id = request.env['res.partner'].sudo().search([('id', '=',
                                                                int(payload.get('partner_id', 0)))], limit=1)
        if partner_id:
            field = [
                'name',
                'type',
                'gift_type',
                'publish_date',
                'effective_date_from',
                'effective_date_to',
                'pos_order_id',
                'warehouse_id',
                'store_id',
                'state',
                'image',
                'content',
                'contact',
                'discount',
                'point_cost',
                'product_ids',
                'loyalty_reward_id',
                'loyalty_level_id',
                'date_used',
            ]
            field_list = ['loyalty_reward_id',
                          'loyalty_level_id', 'pos_order_id', 'warehouse_id', 'store_id']
            null_list = ['date_used', 'image', 'content',
                         'contact', 'type', 'gift_type', 'publish_date']
            reward_id = int(payload.get('reward_id', 0))
            if reward_id:
                return True, self._response_null(request.env['coupon.app'].sudo().search([('partner_id', '=', partner_id.id), ('id', '=', reward_id)], limit=1).read(field), field_list, null_list)
            voucher_id = int(payload.get('voucher_id', 0))
            coupon_id = int(payload.get('coupon_id', 0))
            if voucher_id or coupon_id:
                voucher = request.env['crm.voucher.info'].sudo().search(
                    [('id', '=', voucher_id)], limit=1)
                if voucher:
                    if coupon_id:
                        return False, [{
                            'voucher_type': 'coupon',
                            'name': voucher.ean,
                            'promotion_line_id': voucher.publish_id and voucher.publish_id.promotion_line_id and voucher.publish_id.promotion_line_id.id or False,
                        }]
                    if voucher_id:
                        return True, [{
                            'voucher_type': 'voucher',
                            'voucher_name': voucher.publish_id and voucher.publish_id.name or voucher.ean,
                            'name': voucher.ean,
                            'type': voucher.publish_id and voucher.publish_id.voucher_type and voucher.publish_id.voucher_type or 'all_order',
                            'voucher_amount': voucher.publish_id and voucher.publish_id.voucher_amount or 0,
                        }]
                return False, invalid_response('Lỗi', _('Không tìm thấy'), 404)
            voucher_type = payload.get('voucher_type', False)
            coupon_code = str(payload.get('coupon_code', ''))
            if coupon_code:
                warehouse_id = int(payload.get('warehouse_id', 0))
                if (voucher_type == False or voucher_type == 'reward'):
                    coupon_code_ids = request.env['coupon.app'].sudo().search(
                        [('name', '=', coupon_code)])
                    if len(coupon_code_ids) > 1:
                        return invalid_response('Error', 'Mã quà tặng bị trùng, Vui lòng kiểm tra lại !!')
                    elif len(coupon_code_ids) == 1:
                        coupon_code_id, error = self.check_active_coupon_app(
                            coupon_code_ids[0], partner_id)
                        if not coupon_code_id and error:
                            return False, invalid_response('Error', error)
                        return True, self._response_null(coupon_code_id.read(field), field_list, null_list)
                if (voucher_type == False or voucher_type == 'voucher'):
                    voucher_data, error = self.check_active_voucher(
                        coupon_code, warehouse_id)
                    if not voucher_data and error:
                        return False, invalid_response('Error', error)
                    elif voucher_data and not error:
                        data = {
                            'voucher_type': 'voucher',
                            'voucher_name': voucher_data[2],
                            'name': coupon_code,
                            'type': voucher_data[1],
                            'voucher_amount': voucher_data[0],
                        }
                        return True, [data]
                if (voucher_type == False or voucher_type == 'coupon'):
                    coupon_data, error = self.check_active_coupon(
                        coupon_code, warehouse_id)
                    if not coupon_data and error:
                        return False, invalid_response('Error', error)
                    elif coupon_data and not error:
                        if coupon_data[0] == 'combo':
                            data = {
                                'voucher_type': 'combo',
                                'name': coupon_code,
                                'promo_combo_id': coupon_data[4] or None
                            }
                        else:
                            data = {
                                'voucher_type': 'coupon',
                                'name': coupon_code,
                                'promotion_line_id': coupon_data[4] or None,
                            }
                        return True, [data]
                return False, invalid_response('Lỗi', 'Không tìm thấy', 404)
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
            return True, self._response_null(request.env['coupon.app'].sudo().search([
                ('partner_id', '=', partner_id.id)
            ], limit=limit, offset=offset).read(field), field_list, null_list)
        else:
            return False, invalid_response('Not found', 'Partner not exists')

    # @validate_token
    @http.route('/api/v1/get_promotion', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def get_promotion(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        partner_id = request.env['res.partner'].sudo().search([('id', '=',
                                                                int(payload.get('partner_id', 0)))], limit=1)
        if partner_id:
            res = []
            today = fields.Date.context_today(request)
            warehouse_id = False
            sale_type_id = False
            if payload.get('sale_type_id', False):
                sale_type_id = request.env['pos.sale.type'].sudo().search(
                    [('type_for_app', '=', str(payload['sale_type_id']))], limit=1)
            if payload.get('warehouse_id', False):
                warehouse_id = request.env['stock.warehouse'].sudo().search([('id', '=',
                                                                              int(payload.get('warehouse_id', 0)))], limit=1)
            promo_ids = request.env['sale.promo.header'].search([
                ('list_type', 'in', ['PRO', 'DIS']),
                ('start_date_active', '<=', today),
                ('end_date_active', '>=', today),
                ('state', '=', 'approved'),
                '|',
                ('sale_type_ids', '=', sale_type_id and sale_type_id.id or False),
                ('sale_type_ids', '=', False),
                '|',
                ('apply_type', '=', 'all_warehouse'),
                '&',
                ('apply_type', '=', 'select_warehouse'),
                ('warehouse_ids', '=', warehouse_id and warehouse_id.id or False),
                '|',
                ('day_of_week.value', '=', list_weekday[str(today.isoweekday())]),
                ('day_of_week', '=', False)])
            for promo_id in promo_ids:
                discount_line = []
                for line in promo_id.discount_line:
                    if not line.product_attribute:
                        continue
                    if line.start_date_active and line.start_date_active > today:
                        continue
                    if line.end_date_active and line.end_date_active < today:
                        continue
                    discount_line.append(line.read())
                if not discount_line:
                    continue
                data = {
                    'promo_id': promo_id.id,
                    'name': promo_id.name,
                    'use_for_coupon': promo_id.use_for_coupon,
                    'list_type': promo_id.list_type,
                    'apply_type': promo_id.apply_type,
                    'warehouse_ids': promo_id.warehouse_ids.ids,
                    'discount_line': discount_line
                }
                res.append(data)
            return valid_response(res)
        else:
            return invalid_response('Not found', 'Partner not exists')

    @validate_token
    @http.route('/api/v1/get_reward', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def get_reward(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        partner_id = request.env['res.partner'].sudo().search([('id', '=',
                                                                int(payload.get('partner_id', 0)))], limit=1)
        if partner_id:
            res = []
            if partner_id.loyalty_level_id:
                program_obj = request.env['loyalty.program'].sudo()
                today = fields.Date.context_today(request)
                program_event_id = program_obj.sudo().search(
                    [('program_type', '=', 'event_program'),
                     ('from_date', '<=', today),
                     ('to_date', '>=', today)])
                program_base_id = program_obj.sudo().search(
                    [('program_type', '=', 'base_program'), ('from_date', '<=', today),
                     ('to_date', '>=', today)])
                if program_event_id and program_event_id.reward_ids:
                    for reward in program_event_id.reward_ids:
                        product_ids = []
                        if reward.type == 'discount':
                            product_ids.append(reward.discount_product_id.id)
                        else:
                            if reward.apply_on == 'category':
                                product_ids = request.env['product.template'].sudo().search(
                                    [('categ_id', '=', reward.category_id.id), ('available_in_mobile', '=', True)]).ids
                            elif reward.apply_on == 'product_list':
                                product_ids = reward.gift_product_ids.ids
                            else:
                                product_ids.append(reward.gift_product_id.id)
                        res.append({
                            'name': reward.name or None,
                            'reward_id': reward.id,
                            'image': reward._prepair_url_image(),
                            'effective_date_from': program_event_id.from_date,
                            'effective_date_to': program_event_id.to_date,
                            'type': 'reward',
                            'gift_type': reward.type,
                            'discount': reward.discount or 0.0,
                            'minimum_point': reward.minimum_points or 0.0,
                            'point_cost': reward.point_cost or 0.0,
                            'products': product_ids,
                            'content': reward.content or '',
                            'contact': reward.contact or '',
                        })
                if program_base_id and program_base_id.reward_ids:
                    for reward in program_base_id.reward_ids:
                        product_ids = []
                        if reward.type == 'discount':
                            product_ids.append(reward.discount_product_id.id)
                        else:
                            if reward.apply_on == 'category':
                                product_ids = request.env['product.template'].sudo().search(
                                    [('categ_id', '=', reward.category_id.id), ('available_in_mobile', '=', True)]).ids
                            elif reward.apply_on == 'product_list':
                                product_ids = reward.gift_product_ids.ids
                            else:
                                product_ids.append(reward.gift_product_id.id)
                        res.append({
                            'name': reward.name or None,
                            'reward_id': reward.id,
                            'image': reward._prepair_url_image(),
                            'effective_date_from': program_base_id.from_date,
                            'effective_date_to': program_base_id.to_date,
                            'type': 'reward',
                            'gift_type': reward.type,
                            'discount': reward.discount or 0.0,
                            'minimum_point': reward.minimum_points or 0.0,
                            'point_cost': reward.point_cost or 0.0,
                            'products': product_ids,
                            'content': reward.content or '',
                            'contact': reward.contact or '',
                        })
                if partner_id.loyalty_level_id and self.check_exits_coupon_birthday(partner_id):
                    product_ids = []
                    if partner_id.loyalty_level_id.birthday_reward_type == 'gift':
                        if partner_id.loyalty_level_id.birthday_reward_apply_on == 'category':
                            product_ids = request.env['product.template'].sudo().search(
                                [('categ_id', '=', partner_id.loyalty_level_id.category_id.id), ('available_in_mobile', '=', True)]).ids
                        else:
                            product_ids = partner_id.loyalty_level_id.gift_product_ids.ids
                    res.append({
                        'name': 'Birthday',
                        'type': 'birthday',
                        'image': partner_id.loyalty_level_id._prepair_url_image(),
                        'effective_date_from': today.replace(day=1),
                        'effective_date_to': today.replace(day=1) +
                        relativedelta.relativedelta(months=1, days=-1),
                        'gift_type': partner_id.loyalty_level_id.birthday_reward_type,
                        'discount': partner_id.loyalty_level_id.discount_percent_birthday or 0.0,
                        'minimum_point': 0.0,
                        'point_cost': 0.0,
                        'products': product_ids,
                        'content': partner_id.loyalty_level_id.content_birthday or '',
                        'contact': partner_id.loyalty_level_id.contact_birthday or '',
                    })
            return valid_response(res)
        else:
            return invalid_response('Not found', 'Partner not exists')

    def _get_prefix(self, prefix, partner_id):
        def _interpolate(s, d):
            return (s % d) if s else ''

        def _interpolation_dict(partner_id):
            now = fields.Datetime.context_timestamp(
                request, fields.Datetime.now())

            sequences = {
                'year': '%Y', 'month': '%m', 'day': '%d', 'y': '%y', 'doy': '%j', 'woy': '%W',
                'weekday': '%w', 'h24': '%H', 'h12': '%I', 'min': '%M', 'sec': '%S'
            }
            res = {}
            for key, format in sequences.items():
                res[key] = now.strftime(format)
            res['object'] = partner_id
            return res

        d = _interpolation_dict(partner_id)
        try:
            interpolated_prefix = _interpolate(prefix, d)
        except ValueError:
            return prefix
        return interpolated_prefix

    def generate_coupon(self, type, partner_id):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        get_param = request.env['ir.config_parameter'].sudo().get_param
        size = int(get_param(
            'phuclong_mobile_backend.code_size', 6))
        if not size:
            return False, _("You can't set None Code Length. We can't create cardcode")
        stand = int(get_param('phuclong_mobile_backend.stand', 0))
        alphabet = int(get_param('phuclong_mobile_backend.alphabet', 0))
        if type == 'birthday':
            prefix = get_param('phuclong_mobile_backend.prefix_birthday', '')
        else:
            prefix = get_param('phuclong_mobile_backend.prefix_reward', '')
        if prefix:
            prefix = self._get_prefix(prefix, partner_id)
        max = 10**size
        if size == 1:
            min = 0
        else:
            min = 10**(size-1)
        quantum = 1
        max_quantum = 10**(size + alphabet + len(prefix)) - \
            10**(size + alphabet + len(prefix) - 1)
        if(max_quantum < quantum):
            return False, _("Your code size can't create this cardcode")
        error = 0
        max_error = max_quantum
        full_code = False
        while True:
            number = random.randrange(min, max)
            code = str(number).zfill(size)
            if stand != 0 and alphabet != 0:
                code = request.env['cardcode.publish'].add_alphabet(
                    code, alphabet, stand)
            if prefix:
                full_code = prefix + code
            else:
                full_code = code
            existed_coupon = request.env['coupon.app'].sudo().search([('name', '=', full_code)],
                                                                     limit=1)
            if not existed_coupon:
                existed_coupon = request.env['crm.voucher.info'].sudo().search([('ean', '=', full_code)],
                                                                               limit=1)
            if existed_coupon:
                error += 1
                if error > max_error:
                    return False, _('Không tạo được mã quà tặng')
            else:
                return full_code, False

    def check_exits_coupon_birthday(self, partner_id):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        today = fields.Date.context_today(request)
        if partner_id.month_birthday != today.month:
            return False
        current_year = today.year
        year_discount_birth = partner_id.year_discount_birth
        if year_discount_birth == current_year:
            maximum_count = partner_id.loyalty_level_id.maximum_count
            count_discount_birth = partner_id.count_discount_birth
            if maximum_count != 0 and maximum_count <= count_discount_birth:
                return False
        return True

    @validate_token
    @http.route('/api/v1/create_coupon', type="http", auth="none", methods=["POST"], csrf=False, cors="*")
    def create_coupon(self, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        partner_id = request.env['res.partner'].sudo().search([('id', '=',
                                                                int(payload.get('partner_id', 0)))], limit=1)
        if partner_id and partner_id.loyalty_level_id:
            today = fields.Date.context_today(request)
            type = payload.get('type', False)
            reward_id = payload.get('reward_id', 0)
            coupon_obj = request.env['coupon.app'].sudo()
            reward_obj = request.env['loyalty.reward'].sudo()
            if type == 'birthday':
                if not self.check_exits_coupon_birthday(partner_id):
                    return invalid_response(_('Không tạo được mã quà tặng'), _('Không đổi được mã quà tặng sinh nhật'))
                code, error = self.generate_coupon(type, partner_id)
                if code == False:
                    return invalid_response(_('Không tạo được mã quà tặng'), error)
                product_ids = []
                if partner_id.loyalty_level_id.birthday_reward_type == 'gift':
                    if partner_id.loyalty_level_id.birthday_reward_apply_on == 'category':
                        product_ids = request.env['product.template'].sudo().search(
                            [('categ_id', '=', partner_id.loyalty_level_id.category_id.id), ('available_in_mobile', '=', True)]).ids
                    else:
                        product_ids = partner_id.loyalty_level_id.gift_product_ids.ids
                date_from = today.replace(day=1)
                coupon_id = coupon_obj.create({
                    'name': code,
                    'type': 'birthday',
                    'gift_type': 'discount' if partner_id.loyalty_level_id.birthday_reward_type == 'discount' else 'product',
                    'discount': partner_id.loyalty_level_id.discount_percent_birthday or 0.0,
                    'publish_date': today,
                    'effective_date_from': date_from,
                    'effective_date_to': date_from + relativedelta.relativedelta(months=1, days=-1),
                    'partner_id': partner_id.id,
                    'product_ids': product_ids,
                    'loyalty_level_id': partner_id.loyalty_level_id.id,
                    'content': partner_id.loyalty_level_id.content_birthday or '',
                    'contact': partner_id.loyalty_level_id.contact_birthday or '',
                })
                if coupon_id:
                    year_discount_birth = today.year
                    if year_discount_birth != partner_id.year_discount_birth:
                        count_discount_birth = 1
                    else:
                        count_discount_birth = partner_id.count_discount_birth + 1
                    partner_id.write({
                        'year_discount_birth': year_discount_birth,
                        'count_discount_birth': count_discount_birth
                    })
                    return self._get_coupon(payload={
                        'partner_id': partner_id.id,
                        'reward_id': coupon_id.id
                    })
            elif type == 'reward' and reward_id:
                reward = reward_obj.search(
                    [('id', '=', int(reward_id)), ('loyalty_program_id', '!=', False), ('loyalty_program_id.from_date', '<=', today), ('loyalty_program_id.to_date', '>=', today)], limit=1)
                if reward:
                    total_point_act = partner_id.total_point_act
                    point_cost = reward.point_cost
                    if total_point_act < point_cost:
                        return invalid_response(_('Không tạo được mã quà tặng'), _('Điểm hiện tại không đủ'))
                    code, error = self.generate_coupon(type, partner_id)
                    if code == False:
                        return invalid_response(_('Không tạo được mã quà tặng'), error)
                    product_ids = []
                    if reward.type == 'discount':
                        product_ids.append(reward.discount_product_id.id)
                    else:
                        if reward.apply_on == 'category':
                            product_ids = request.env['product.template'].sudo().search(
                                [('categ_id', '=', reward.category_id.id), ('available_in_mobile', '=', True)]).ids
                        elif reward.apply_on == 'product_list':
                            product_ids = reward.gift_product_ids.ids
                        else:
                            product_ids.append(reward.gift_product_id.id)
                    coupon_id = coupon_obj.create({
                        'name': code,
                        'type': 'point',
                        'gift_type': reward.type == 'discount' and 'discount' or 'product',
                        'publish_date': fields.Date.context_today(request),
                        'effective_date_from': reward.loyalty_program_id.from_date,
                        'effective_date_to': partner_id.expired_date,
                        'discount': reward.discount or 0.0,
                        'partner_id': partner_id.id,
                        'product_ids': product_ids,
                        'loyalty_reward_id': reward.id,
                        'content': reward.content or '',
                        'contact': reward.contact or '',
                        'point_cost': reward.point_cost or 0.0,
                    })
                    if coupon_id:
                        total_point_act -= point_cost
                        partner_id.write({'total_point_act': total_point_act})
                        return self._get_coupon(payload={
                            'partner_id': partner_id.id,
                            'reward_id': coupon_id.id
                        })
            return invalid_response(_('Không tạo được mã quà tặng'), 'Không tạo được mã quà tặng')
        else:
            return invalid_response(_('Không tạo được mã quà tặng'), 'Không tìm thấy khách hàng', 404)

    @validate_token
    @http.route('/api/address/<id>', type="http", auth="none", methods=["GET"], csrf=False, cors="*")
    def get_address(self, id=None):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        if id:
            domain = [
                ('parent_id', '=', int(id)),
                ('type', '=', 'delivery')
            ]
            fields = [
                'name',
                'address',
                'address_note',
                'lat',
                'lng',
                'order_in_app_ids'
            ]
            return valid_response(self._response_null(request.env['res.partner'].search(domain, order='create_date DESC', limit=10).read(fields), ['order_in_app_ids']))
        else:
            return invalid_response('Not found', 'Partner not exists')

    @validate_token
    @http.route('/api/address/<id>', type="http", auth="none", methods=["POST"], csrf=False, cors="*")
    def create_address(self, id=None, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        parner_id = request.env['res.partner'].search(
            [('id', '=', int(id))], limit=1)
        if parner_id:
            vals = {
                'type': 'delivery',
                'name': payload.get('name', ''),
                'address': payload.get('address', ''),
                'address_note': payload.get('address_note', ''),
                'lat': payload.get('lat', ''),
                'lng': payload.get('lng', ''),
                'city': False,
                'comment': False,
                'company_type': "person",
                'country_id': False,
                'customer': False,
                'district_id': False,
                'email': False,
                'function': False,
                'image': False,
                'is_company': False,
                'mobile': False,
                'parent_id': parner_id.id,
                'phone': False,
                'state_id': False,
                'street': False,
                'street2': False,
                'supplier': False,
                'title': False,
                'user_id': False,
                'ward_id': False,
                'zip': False
            }
            parner_id.write({
                'child_ids': [(0, 0, vals)]
            })
            domain = [
                ('parent_id', '=', int(id)),
                ('type', '=', 'delivery')
            ]
            child_ids = request.env['res.partner'].search(
                domain, order='create_date DESC', offset=10)
            if child_ids:
                child_ids.unlink()
            return self.get_address(parner_id.id)
        else:
            return invalid_response('Not found', 'Partner not exists')

    @validate_token
    @http.route('/api/address/<parner_id>/<id>', type="http", auth="none", methods=["PUT"], csrf=False, cors="*")
    def update_address(self, parner_id=None, id=None, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        child_id = request.env['res.partner'].search(
            [('id', '=', int(id)), ('type', '=', 'delivery'), ('parent_id', '=', int(parner_id))], limit=1)
        if child_id:
            vals = {
                'type': 'delivery',
                'name': payload.get('name', ''),
                'address': payload.get('address', ''),
                'address_note': payload.get('address_note', ''),
                'lat': payload.get('lat', ''),
                'lng': payload.get('lng', ''),
                'city': False,
                'comment': False,
                'company_type': "person",
                'country_id': False,
                'customer': False,
                'district_id': False,
                'email': False,
                'function': False,
                'image': False,
                'is_company': False,
                'mobile': False,
                'phone': False,
                'state_id': False,
                'street': False,
                'street2': False,
                'supplier': False,
                'title': False,
                'user_id': False,
                'ward_id': False,
                'zip': False
            }
            child_id.write(vals)
            return self.get_address(child_id.parent_id and child_id.parent_id.id or None)
        else:
            return invalid_response('Not found', 'Partner not exists')

    @validate_token
    @http.route('/api/address/<parner_id>/<id>', type="http", auth="none", methods=["DELETE"], csrf=False, cors="*")
    def delete_address(self, parner_id=None, id=None, **payload):
        request.session.uid = SUPERUSER_ID
        request.uid = SUPERUSER_ID
        child_id = request.env['res.partner'].search(
            [('id', '=', int(id)), ('type', '=', 'delivery'), ('parent_id', '=', int(parner_id))], limit=1)
        if child_id:
            parent_id = child_id.parent_id and child_id.parent_id.id or None
            child_id.unlink()
            return self.get_address(parent_id)
        else:
            return invalid_response('Not found', 'Partner not exists')

    # @http.route('/api/v1/create_coupon', type="http", auth="none", methods=["POST"], csrf=False, cors="*")
    # def create_coupon(self, **payload):
