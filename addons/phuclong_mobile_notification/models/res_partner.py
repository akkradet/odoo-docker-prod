# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import timedelta
import logging
_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = 'res.partner'

    def send_noti_logout(self):
        for rec in self:
            self.env['mobile.notification'].sudo().with_context(send_now=True).create({
                'name': _('Logout'),
                'message': _('Login other device.'),
                'display': False,
                'noti_type': 'logout',
                'partner_ids': [(6, 0, rec.ids)],
            })

    def action_push_messaging_mobile(self):
        partner_ids = self.filtered(
            lambda p: p.authorized and p.token_device)
        return {
            'name': _('Notification'),
            'view_mode': 'form',
            'res_model': 'mobile.notification',
            'type': 'ir.actions.act_window',
            'context': {
                'default_partner_ids': [(6, 0, partner_ids.ids)]
            }
        }

    def action_notification_birthday(self, partner_ids=False):
        auto_id = self.env.ref(
            'phuclong_mobile_notification.mobile_notification_auto_7')
        if auto_id and auto_id.run == True:
            try:
                if not partner_ids:
                    month_birthday = fields.Date.context_today(
                        self).month
                    partner_ids = self.env['res.partner'].search(
                        [('authorized', '=', True), ('token_device', '!=', False), ('type', '=', 'contact'), ('loyalty_level_id', '!=', False), ('month_birthday', '=', month_birthday)])
                if partner_ids:
                    for partner_id in partner_ids:
                        self.env['mobile.notification'].sudo().with_context(send_now=True).create({
                            'name': auto_id._safe_eval(partner_id, auto_id.title),
                            'message': auto_id._safe_eval(partner_id, auto_id.message),
                            'display': auto_id.display,
                            'noti_type': auto_id.noti_type,
                            'link_type': 'reward',
                            'image_1920': auto_id.image_1920,
                            'image_thumbnail': auto_id.image_thumbnail,
                            'partner_ids': [(6, 0, partner_id.ids)],
                            'notification_auto_id': auto_id.id,
                        })
            except Exception as e:
                auto_id.log(str(e))

    def action_notification_change_date_level(self):
        auto_id = self.env.ref(
            'phuclong_mobile_notification.mobile_notification_auto_2')
        if auto_id and auto_id.run == True:
            try:
                number = auto_id.number
                change_date_level = fields.Date.context_today(
                    self) - timedelta(days=number)
                partner_ids = self.env['res.partner'].search(
                    [('authorized', '=', True), ('token_device', '!=', False), ('type', '=', 'contact'), ('loyalty_level_id', '=', False), ('change_date_level', '=', change_date_level)])
                if partner_ids:
                    for partner_id in partner_ids:
                        self.env['mobile.notification'].sudo().with_context(send_now=True).create({
                            'name': auto_id._safe_eval(partner_id, auto_id.title),
                            'message': auto_id._safe_eval(partner_id, auto_id.message),
                            'display': auto_id.display,
                            'noti_type': auto_id.noti_type,
                            'image_1920': auto_id.image_1920,
                            'image_thumbnail': auto_id.image_thumbnail,
                            'partner_ids': [(6, 0, partner_id.ids)],
                            'notification_auto_id': auto_id.id,
                        })
            except Exception as e:
                auto_id.log(str(e))

    def action_notification_expired_loyalty(self):
        auto_id = self.env.ref(
            'phuclong_mobile_notification.mobile_notification_auto_1')
        if auto_id and auto_id.run == True:
            try:
                number = auto_id.number
                expired_date = fields.Date.context_today(
                    self) + timedelta(days=number)
                partner_ids = self.env['res.partner'].search(
                    [('authorized', '=', True), ('token_device', '!=', False), ('type', '=', 'contact'), ('loyalty_level_id', '!=', False), ('expired_date', '=', expired_date)])
                if partner_ids:
                    for partner_id in partner_ids:
                        self.env['mobile.notification'].sudo().with_context(send_now=True).create({
                            'name': auto_id._safe_eval(partner_id, auto_id.title),
                            'message': auto_id._safe_eval(partner_id, auto_id.message),
                            'display': auto_id.display,
                            'noti_type': auto_id.noti_type,
                            'image_1920': auto_id.image_1920,
                            'image_thumbnail': auto_id.image_thumbnail,
                            'partner_ids': [(6, 0, partner_id.ids)],
                            'notification_auto_id': auto_id.id,
                        })
            except Exception as e:
                auto_id.log(str(e))

    def write(self, values):
        # Add code here
        if 'token_device' in values and values['token_device']:
            self.filtered(
                lambda p: p.authorized and p.token_device and p.token_device != values['token_device'] and p.token_device_active == True).send_noti_logout()
        auto_id = False
        if 'total_point_act' in values:
            auto_id = self.env.ref(
                'phuclong_mobile_notification.mobile_notification_auto_3')
            if auto_id and auto_id.run == True:
                partner_ids = self.filtered(
                    lambda p: p.authorized and p.token_device and p.total_point_act < auto_id.number)
        result = super(Partner, self).write(values)
        if auto_id and auto_id.run == True:
            try:
                partner_ids = partner_ids.filtered(
                    lambda p: p.total_point_act >= auto_id.number)
                if partner_ids:
                    for partner_id in partner_ids:
                        self.env['mobile.notification'].sudo().with_context(send_now=True).create({
                            'name': auto_id._safe_eval(partner_id, auto_id.title),
                            'message': auto_id._safe_eval(partner_id, auto_id.message),
                            'display': auto_id.display,
                            'noti_type': auto_id.noti_type,
                            'image_1920': auto_id.image_1920,
                            'image_thumbnail': auto_id.image_thumbnail,
                            'partner_ids': [(6, 0, partner_id.ids)],
                            'notification_auto_id': auto_id.id,
                        })
            except Exception as e:
                auto_id.log(str(e))
        return result

    @api.depends('current_point_act', 'customer', 'can_loyalty_level')
    def _compute_loyalty_level(self):
        auto_id = self.env.ref(
            'phuclong_mobile_notification.mobile_notification_auto_4')
        if auto_id and auto_id.run == True:
            for rec in self:
                prev_loyalty_level_id = rec.loyalty_level_id or False
                if not rec.can_loyalty_level:
                    rec.loyalty_level_id = False
                elif rec.customer == False and rec.loyalty_level_id:
                    rec.loyalty_level_id = False
                else:
                    self._cr.execute('''
                                SELECT id FROM loyalty_level 
                                WHERE from_point_act <= %s AND to_point_act >= %s AND active = true
                                ''' % (rec.current_point_act, rec.current_point_act))
                    res = self._cr.fetchone()
                    if not res:
                        rec.loyalty_level_id = False
                    else:
                        rec.loyalty_level_id = res
                try:
                    if rec.type != 'contact':
                        continue
                    current_loyalty_level_id = rec.loyalty_level_id
                    if prev_loyalty_level_id == False:
                        if current_loyalty_level_id:
                            if rec.birthday:
                                month_birthday = fields.Date.context_today(
                                    self).month
                                if month_birthday == rec.month_birthday:
                                    self.action_notification_birthday(rec)
                            self.env['mobile.notification'].sudo().with_context(send_now=True).create({
                                'name': auto_id._safe_eval(rec, auto_id.title),
                                'message': auto_id._safe_eval(current_loyalty_level_id, auto_id.upgrade),
                                'display': auto_id.display,
                                'noti_type': auto_id.noti_type,
                                'link_type': 'reward',
                                'image_1920': auto_id.image_1920,
                                'image_thumbnail': auto_id.image_thumbnail,
                                'partner_ids': [(6, 0, rec.ids)],
                                'notification_auto_id': auto_id.id,
                            })
                    else:
                        if current_loyalty_level_id:
                            if prev_loyalty_level_id != current_loyalty_level_id:
                                if prev_loyalty_level_id.to_point_act > current_loyalty_level_id.to_point_act:
                                    self.env['mobile.notification'].sudo().with_context(send_now=True).create({
                                        'name': auto_id._safe_eval(rec, auto_id.title),
                                        'message': auto_id._safe_eval(current_loyalty_level_id, auto_id.downgrade),
                                        'display': auto_id.display,
                                        'noti_type': auto_id.noti_type,
                                        'image_1920': auto_id.image_1920,
                                        'image_thumbnail': auto_id.image_thumbnail,
                                        'partner_ids': [(6, 0, rec.ids)],
                                        'notification_auto_id': auto_id.id,
                                    })
                                else:
                                    self.env['mobile.notification'].sudo().with_context(send_now=True).create({
                                        'name': auto_id._safe_eval(rec, auto_id.title),
                                        'message': auto_id._safe_eval(current_loyalty_level_id, auto_id.upgrade),
                                        'display': auto_id.display,
                                        'noti_type': auto_id.noti_type,
                                        'image_1920': auto_id.image_1920,
                                        'image_thumbnail': auto_id.image_thumbnail,
                                        'partner_ids': [(6, 0, rec.ids)],
                                        'notification_auto_id': auto_id.id,
                                    })
                except Exception as e:
                    auto_id.log(str(e))
            return True
        return super(Partner, self)._compute_loyalty_level()
