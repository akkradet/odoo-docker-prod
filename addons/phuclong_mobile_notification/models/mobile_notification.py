# -*- coding: utf-8 -*-

from datetime import datetime, date, timedelta
from odoo.tools.safe_eval import safe_eval
from odoo import api, fields, models, _
from firebase_admin import messaging
import json
import logging
_logger = logging.getLogger(__name__)


class MobileNotification(models.Model):
    _name = 'mobile.notification'
    _description = 'Mobile Notification'
    _order = 'date_scheduled DESC'
    _inherit = ['image.mixin']

    name = fields.Char(string='Title', default=_("Notification"))
    message = fields.Text(string='Message')
    display = fields.Boolean(string='Display', default=True)
    image_thumbnail = fields.Binary(string='Thumbnail')
    image_1920 = fields.Binary(string='Image Popup')
    all = fields.Boolean(string='All Partners')
    partner_ids = fields.Many2many(
        'res.partner', 'mobile_notification_res_partner_rel', 'n_id', 'p_id', string='Partners')
    date_scheduled = fields.Datetime(
        string='Scheduled Date', default=lambda self: fields.Datetime.now())
    noti_type = fields.Selection(string='Type', selection=[(
        'popup', 'Pop-up '), ('push', 'Push'), ('logout', 'Logout')], default='push')
    show_case_id = fields.Many2one(
        comodel_name='show.case', string='Show Case')
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template', string='Product')
    pos_order_id = fields.Many2one(
        comodel_name='pos.order', string='Pos Order')
    coupon_app_id = fields.Many2one(
        comodel_name='coupon.app', string='Coupon App')
    link_type = fields.Selection(string='Link Type', selection=[
        ('news', 'News'),
        ('product', 'Product'),
        ('pos', 'Pos Order'),
        ('reward', 'Reward'),
    ])
    state = fields.Selection(string='State', selection=[
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('error', 'Error')
    ], default='draft', copy=False)
    date_complete = fields.Datetime(string='Completion Date', copy=False)
    data = fields.Text(copy=False, default='{}')
    notification_auto_id = fields.Many2one(
        comodel_name='mobile.notification.auto', string='Notification Auto', copy=False)
    log_ids = fields.One2many(
        comodel_name='mobile.notification.log', inverse_name='notification_id', string='Logs', copy=False)
    notification_read_ids = fields.One2many(
        comodel_name='mobile.notification.read', inverse_name='notification_id', string='Read', copy=False)

    def log(self, log=False, type=_('Error')):
        self.ensure_one()
        if log:
            self.write({
                'log_ids': [(0, 0, {
                    'log': log,
                    'type': type,
                    'notification_auto_id': self.notification_auto_id and self.notification_auto_id.id or False
                })]
            })

    def _prepair_url_image(self, base_url=False, field='image_1920'):
        self.ensure_one()
        if not base_url:
            base_url = self.env['ir.config_parameter'].sudo(
            ).get_param('web.base.url')
        return '%s/web/image/%s/%s/%s' % (base_url, self._name, self.id, field)

    def __get_notifications_by_partner(self, partner_id, limit=None, offset=0):
        partner = self.env['res.partner'].browse(partner_id)
        # sql = '''
        #     SELECT id FROM mobile_notification mn LEFT JOIN mobile_notification_res_partner_rel mnr ON mn.id = mnr.n_id
        #     WHERE mn.state = 'done' and mn.display IS TRUE and date_scheduled >= (SELECT )
        # '''
        return self.search([('state', '=', 'done'), ('display', '=', True), '|', ('all', '=', True), '&', ('all', '!=', True), ('partner_ids', '=', partner_id), ('date_scheduled', '>=', partner.create_date)], limit=limit, offset=offset)

    def _get_notifications_by_partner(self, partner_id, limit=None, offset=0):
        return self.__get_notifications_by_partner(partner_id, limit, offset)._get_notifications(partner_id)

    def _get_notifications(self, partner_id):
        results = []
        for rec in self:
            result = rec.read([
                'name',
                'message',
                'data',
                'date_scheduled',
                'date_complete'
            ])[0]
            result['data'] = json.loads(result['data'])
            result['read_ids'] = rec.notification_read_ids.filtered(
                lambda p: p.partner_id.id == partner_id).read([
                    'partner_id',
                    'create_date'
                ])
            results.append(result)
        return results

    def _read_all_notification(self, partner_id):
        return self.__get_notifications_by_partner(partner_id)._read_notification(partner_id)

    def _read_notification(self, partner_id):
        self.write({
            'notification_read_ids': [(0, 0, {
                'partner_id': partner_id
            })]
        })
        return self._get_notifications(partner_id)

    def _delete_notification(self, partner_id):
        self.write({
            'display': False
        })
        return self._get_notifications(partner_id)

    def _cron_send_now(self, record_id=0, log=False):
        try:
            record_ids = self.sudo().search([('state', '=', 'done')])
            cron_ids = record_ids.mapped('cron_id')
            if cron_ids:
                cron_ids.sudo().unlink()
            self.browse(record_id).action_done()
        except Exception as e:
            if log:
                log(str(e))

    def send_multicast(self, partner_ids=False, title=False, body=False, data={}):
        if partner_ids:
            messages = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title and title or _("Notification"),
                    body=body and body or "",
                ),
                data=data,
                android=messaging.AndroidConfig(
                    ttl=timedelta(seconds=3600),
                    priority='normal',
                    notification=messaging.AndroidNotification(
                        click_action='FLUTTER_NOTIFICATION_CLICK',
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(badge=42),
                    ),
                ),
                tokens=partner_ids.mapped('token_device'),
            )
            return messaging.send_multicast(messages)
        return False

    @api.model
    def create(self, values):
        # Add code here
        rec_id = super(MobileNotification, self).create(values)
        if self._context.get('send_now', False):
            rec_id.action_done()
        return rec_id

    def action_done(self):
        base_url = self.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        for rec in self:
            data = {}
            try:
                if rec.state not in ['draft', 'confirm', 'in_progress']:
                    continue
                if rec.all:
                    partner_ids = self.env['res.partner'].search(
                        [('authorized', '=', True), ('token_device', '!=', False)])
                else:
                    partner_ids = rec.partner_ids.filtered(
                        lambda p: p.authorized and p.token_device)
                if rec.noti_type == 'logout':
                    partner_ids = partner_ids.filtered(
                        lambda p: p.token_device_active == True)
                if partner_ids:
                    data.update({
                        "noti_id": str(rec.id),
                        "noti_type": rec.noti_type or '',
                        "link_type": rec.link_type or '',
                        "image_popup": rec._prepair_url_image(base_url),
                        "image_thumbnail": rec._prepair_url_image(base_url, "image_thumbnail"),
                    })
                    if rec.link_type == 'news' and rec.show_case_id:
                        data.update({
                            "link_id": str(rec.show_case_id.id)
                        })
                    if rec.link_type == 'product' and rec.product_tmpl_id:
                        data.update({
                            "link_id": str(rec.product_tmpl_id.id)
                        })
                    if rec.link_type == 'pos' and rec.pos_order_id:
                        data.update({
                            "link_id": str(rec.pos_order_id.id)
                        })
                    if rec.link_type == 'reward' and rec.coupon_app_id:
                        data.update({
                            "link_id": str(rec.coupon_app_id.id)
                        })
                    if rec.noti_type:
                        if rec.noti_type == 'logout':
                            for partner_id in partner_ids:
                                data.update({
                                    'partner_id': str(partner_id.id)
                                })
                                self.send_multicast(partner_id,
                                                    rec.name, rec.message, data)
                        else:
                            self.send_multicast(partner_ids,
                                                rec.name, rec.message, data)
                    if rec.cron_id and self._context.get('send_now'):
                        rec.cron_id.write({
                            'numbercall': 0,
                            'active': False
                        })
                rec.write({
                    'data': json.dumps(data, indent=4),
                    'date_complete': fields.Datetime.now(),
                    'state': 'done',
                })
            except Exception as e:
                rec.write({
                    'data': json.dumps(data, indent=4),
                    'state': 'error',
                })
                rec.log(str(e))

    cron_id = fields.Many2one(
        'ir.cron', string='Cron', copy=False)

    def unlink(self):
        # Add code here
        cron_ids = self.sudo().mapped('cron_id')
        if cron_ids:
            cron_ids.sudo().unlink()
        return super(MobileNotification, self).unlink()

    def set_cron_send_now(self, values):
        self.ensure_one()
        return self.env['ir.cron'].sudo().create({
            'name': '%s: %s-%s' % (_('Mobile Notification'), values.get('name', ''), values.get('id', '')),
            'active': True,
            'model_id': self.env['ir.model'].sudo().search([('model', '=', self._name)], limit=1).id,
            'state': 'code',
            'code': 'model._cron_send_now(record_id=%s, log=log)' % self.id,
            'interval_number': 1,
            'interval_type': 'minutes',
            'numbercall': 1,
            'nextcall': self.date_scheduled
        })

    def action_draft(self):
        cron_ids = self.mapped('cron_id')
        if cron_ids:
            cron_ids.write({
                'numbercall': 0,
                'active': False
            })
        self.write({
            'state': 'draft',
        })

    def action_confirm(self):
        for rec in self:
            if rec.cron_id:
                rec.cron_id.write({
                    'nextcall': rec.date_scheduled
                })
        self.write({
            'state': 'confirm'
        })

    def action_send(self):
        now = fields.Datetime.now()
        for rec in self:
            try:
                if rec.state == 'confirm':
                    if rec.date_scheduled < now:
                        rec.action_done()
                    else:
                        if not rec.cron_id:
                            cron_id = self.sudo().set_cron_send_now({
                                'name': rec.name,
                                'id': rec.id
                            })
                            if not cron_id:
                                val = {
                                    'state': 'error',
                                    'cron_id': cron_id and cron_id.id or False,
                                }
                                rec.log(_('Can not create cron.'))
                            else:
                                val = {
                                    'state': 'in_progress',
                                    'cron_id': cron_id and cron_id.id or False,
                                }
                            rec.write(val)
                        else:
                            rec.cron_id.write({
                                'numbercall': 1,
                                'active': True
                            })
                            rec.write({
                                'state': 'in_progress',
                            })
            except Exception as e:
                rec.write({
                    'state': 'error',
                })
                rec.log(str(e))


class MobileNotificationRead(models.Model):
    _name = 'mobile.notification.read'

    notification_id = fields.Many2one(
        comodel_name='mobile.notification', string='Notification')
    partner_id = fields.Many2one('res.partner', string='Partner')
