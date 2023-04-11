from odoo import models, fields, api, _
from odoo.addons.phuclong_restful_api.common import invalid_response, valid_response
import json


class LoginMethod(models.Model):
    _name = 'login.method'

    _description = 'Login Method'

    name = fields.Char(string="Key")
    partner_id = fields.Many2one('res.partner', string="User")
    login_id = fields.Many2one('configuration.login', string="Login Method")


class MobileOTP(models.Model):
    _name = 'mobile.otp'

    name = fields.Char()
    otp = fields.Char()
    expires_in = fields.Datetime()


class ResPartner(models.Model):
    _inherit = 'res.partner'

    expired_date = fields.Date(inverse='_inverse_expired_date')
    coupon_app_ids = fields.One2many(
        comodel_name='coupon.app', inverse_name='partner_id', string='Coupon Apps')
    order_in_app_ids = fields.One2many(
        comodel_name='pos.order', inverse_name='address_id', string='Order In Apps')

    def _inverse_expired_date(self):
        for rec in self:
            coupon_ids = rec.coupon_app_ids.filtered(
                lambda c: c.type == 'point' and c.state == 'new')
            if coupon_ids:
                coupon_ids.write({
                    'effective_date_to': rec.expired_date
                })

    authorized = fields.Boolean(string="Register use App", default=False)
    can_loyalty_level = fields.Boolean(default=True)
    method_login_ids = fields.One2many('login.method', 'partner_id')
    wallet_id = fields.Many2one('partner.wallet', string="Wallet")
    token_device = fields.Char('Token Device')
    token_device_active = fields.Boolean(default=False)
    month_birthday = fields.Integer(
        compute='_compute_month_birthday', store=True)

    def write(self, values):
        # Add code here
        if 'token_device_active' in values:
            token_device_active = False
            if values.get('token_device_active', False) == 'true':
                token_device_active = True
            values.update({'token_device_active': token_device_active})
        return super(ResPartner, self).write(values)

    @api.depends('birthday')
    def _compute_month_birthday(self):
        for rec in self:
            rec.month_birthday = rec.birthday and rec.birthday.month or 0

    @api.depends('current_point_act', 'customer', 'can_loyalty_level')
    def _compute_loyalty_level(self):
        for record in self:
            if not record.can_loyalty_level:
                record.loyalty_level_id = False
                continue
            if record.customer == False and record.loyalty_level_id:
                record.loyalty_level_id = False
                continue
            self._cr.execute('''
                        SELECT id FROM loyalty_level 
                        WHERE from_point_act <= %s AND to_point_act >= %s AND active = true
                        ''' % (record.current_point_act, record.current_point_act))
            res = self._cr.fetchone()
            if not res:
                record.loyalty_level_id = False
            else:
                record.loyalty_level_id = res
        return True

    address = fields.Char(default='')
    address_note = fields.Char(default='')
    lat = fields.Char(default='')
    lng = fields.Char(default='')

    def send_otp(self, payload):
        if 'mobile' not in payload:
            return valid_response({
                'code': 1,
                'message': 'Missing fields mobile'
            })
        else:
            return valid_response({
                'code': 200,
                'otp': '123456'
            })

    def login_otp(self, payload):
        flag = []
        if 'mobile' not in payload:
            flag.append('mobile')
        if 'otp' not in payload:
            flag.append('otp')
        if 'password' not in payload:
            flag.append('password')
        if not flag:
            if payload['otp'] == '123456':
                partner_id = self.env['res.partner'].sudo().search(
                    [('mobile', '=', payload['mobile'])])
                if partner_id:
                    try:
                        partner_id.write({'password': payload['password']})
                        return valid_response({
                            'code': 200,
                            'message': 'Login successfully'
                        })
                    except Exception as e:
                        return valid_response({
                            'code': 4,
                            'message': e.name
                        })
                else:
                    return valid_response({
                        'code': 3,
                        'message': 'Mobile invalid'
                    })
            else:
                return valid_response({
                    'code': 2,
                    'message': 'Otp invalid'
                })
        else:
            return valid_response({
                'code': 1,
                'message': 'Missing fields %s' % (', '.join(flag))
            })

    def check_appear_code(self, payload):
        card_id = self.env['cardcode.info'].sudo().search(
            [('appear_code', '=', payload.get('appear_code_id', ''))])
        if card_id and payload.get('appear_code_id', False):
            partner_id = self.sudo().search(
                [('customer', '=', True), ('appear_code_id', '=', card_id.id)])
            if partner_id:
                return valid_response({
                    'code': 2,
                    'message': False,
                    'user_id': partner_id.id
                })
            else:
                return valid_response({
                    'code': 1,
                    'message': 'OK',
                    'user_id': False
                })
        else:
            return valid_response({
                'code': 3,
                'message': 'appear_code_id does not exist',
                'user_id': False
            })

    def create_mass_partner(self, payload):
        partner_obj = self.env['res.partner']
        datas = []
        if payload.get('datas', False):
            if not isinstance(payload['datas'], list):
                try:
                    payload['datas'] = json.loads(payload['datas'])
                except Exception as e:
                    return invalid_response('Something went wrong', e)
            for index, data in enumerate(payload.get('datas', [])):
                flag = []
                if not 'name' in data:
                    flag.append('name')
                if not 'appear_code_id' in data:
                    flag.append('appear_code_id')
                if not 'phone' in data:
                    flag.append('phone')
                if flag:
                    mess = 'Index %s: Field %s must be required!' % (
                        index, ', '.join(flag))
                    datas.append({
                        'partner_id': False,
                        'error': True,
                        'message': mess
                    })
                else:
                    try:
                        card_id = self.env['cardcode.info'].sudo().search(
                            [('appear_code', '=', data.get('appear_code_id', False))])
                        if card_id:
                            data['appear_code_id'] = card_id.id
                        else:
                            data['appear_code_id'] = False
                        partner_id = partner_obj.create(data)
                        datas.append({
                            'partner_id': partner_id.id,
                            'error': False,
                            'message': 'Create successfully!'
                        })
                    except Exception as e:
                        datas.append({
                            'partner_id': False,
                            'error': True,
                            'message': 'Index %s: %s' % (index, e.name)
                        })
            return valid_response(datas)
        else:
            return invalid_response('Missing field required', 'Field datas must be required')

    def update_mass_partner(self, payload):
        datas = []
        partner_obj = self.env['res.partner']
        if payload.get('datas', False):
            if not isinstance(payload['datas'], list):
                try:
                    payload['datas'] = json.loads(payload['datas'])
                except Exception as e:
                    return invalid_response('Something went wrong', e)
            for index, data in enumerate(payload.get('datas', [])):
                flag = []
                if not 'appear_code_id' in data:
                    flag.append('appear_code_id')
                if flag:
                    mess = 'Index %s: Field %s must be required!' % (
                        index, ', '.join(flag))
                    datas.append({
                        'partner_id': False,
                        'error': True,
                        'message': mess
                    })
                else:
                    card_id = self.env['cardcode.info'].sudo().search(
                        [('appear_code', '=', data.get('appear_code_id', False))])
                    if card_id:
                        partner_id = partner_obj.search(
                            [('appear_code_id', '=', card_id.id)], limit=1)
                        if partner_id:
                            data.pop('appear_code_id', None)
                            try:
                                partner_id.write(data)
                                datas.append({
                                    'partner_id': partner_id.id,
                                    'error': False,
                                    'message': 'Update successfully!'
                                })
                            except Exception as e:
                                mess = 'Index %s: %s' % (index, e.name)
                                datas.append({
                                    'partner_id': False,
                                    'error': True,
                                    'message': mess
                                })
                        else:
                            mess = 'Index %s: Partner not exist!' % index
                            datas.append({
                                'partner_id': False,
                                'error': True,
                                'message': mess
                            })
                    else:
                        mess = 'Index %s: Appear Code not exist!' % index
                        datas.append({
                            'partner_id': False,
                            'error': True,
                            'message': mess
                        })
            return valid_response(datas)
        else:
            return invalid_response('Missing field required', 'Field datas must be required')

    def create_wallet(self, payload):
        if not 'id_number' in payload:
            return invalid_response('Missing field required', 'Field id_number must be required')
        if not 'photo_card_before' in payload:
            return invalid_response('Missing field required', 'Field photo_card_before must be required')
        if not 'photo_card_after' in payload:
            return invalid_response('Missing field required', 'Field photo_card_after must be required')
        try:
            wallet_id = self.env['partner.wallet'].create({
                'name': self.name,
                'id_number': payload['id_number'],
                'image_front': payload['photo_card_before'],
                'image_back': payload['photo_card_after']
            })
            if wallet_id:
                self.write({'wallet_id': wallet_id})
                return valid_response({'wallet_id': wallet_id.id, 'message': 'Create wallet successfully'})
        except Exception as e:
            return invalid_response('Something went wrong', e.name)

    # def login(self, payload):
    #     account_input_name = payload['mobile'].replace(" ", "")
    #     account_input_password = payload['password']
    #
    #     account_partner = self.search(
    #         [('mobile', '=', account_input_name),
    #          ('password', '=', account_input_password)])
    #
    #     if account_partner:
    #         account_id = account_partner.id
    #         account_partner.authorized = True
    #         return valid_response({
    #             "account_id": account_id,
    #             "account_token": account_token
    #         })
    #     else:
    #         return invalid_response("account user", "wrong account mobile or password!")
