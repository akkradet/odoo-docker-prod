# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval
from datetime import datetime, date, timedelta


class Cron(models.Model):
    _inherit = 'ir.cron'

    notification_auto_id = fields.Many2one(
        comodel_name='mobile.notification.auto', string='Notification Auto')


class MobileNotificationLog(models.Model):
    _name = 'mobile.notification.log'
    _description = 'Notification Log'
    _order = 'create_date DESC'

    notification_auto_id = fields.Many2one(
        comodel_name='mobile.notification.auto', string='Notification Auto')
    notification_id = fields.Many2one(
        comodel_name='mobile.notification', string='Notification')
    log = fields.Text(string='Log')
    type = fields.Char(string='Type', default=_('Error'))


class MobileNotificationAuto(models.Model):
    _name = 'mobile.notification.auto'
    _description = 'Notification Auto'
    _rec_name = 'name'
    _inherit = ['image.mixin']

    name = fields.Char(string='Name', compute='_compute_name', store=True)

    @api.depends('type')
    def _compute_name(self):
        types = dict(
            self._fields['type']._description_selection(self.env))
        for rec in self:
            rec.name = types.get(rec.type, '')

    title = fields.Char(string='Title', required=False)
    message = fields.Text(string='Message', required=False)
    image_thumbnail = fields.Binary(string='Thumbnail')
    image_1920 = fields.Binary(string='Image Popup')
    upgrade = fields.Text(string='Upgrade', required=False)
    downgrade = fields.Text(string='Downgrade', required=False)
    run = fields.Boolean(string='Run', default=False)
    display = fields.Boolean(string='Display', default=True)
    noti_type = fields.Selection(string='Noti Type', selection=[(
        'popup', 'Pop-up '), ('push', 'Push')], default='push')
    type = fields.Selection(string='Type', selection=[
        ('1', 'Sắp hết hạn thẻ'),
        ('2', 'Tăng hạng mức thành viên'),
        ('3', 'Đủ điểm đổi quà'),
        ('4', 'Tăng/giảm hạng thẻ'),
        ('5', 'Xác nhận yêu cầu cập nhật thẻ'),
        ('6', 'Huỷ đơn hàng'),
        ('7', 'Ưu đãi sinh nhật'),
        ('8', 'Thanh toán đơn hàng thành công'),
        ('9', 'Nhắc nhở thanh toán đơn hàng'),
    ], required=False)
    cron_ids = fields.One2many(
        comodel_name='ir.cron', inverse_name='notification_auto_id', string='Crons', context={'active_test': False})
    notification_ids = fields.One2many(
        comodel_name='mobile.notification', inverse_name='notification_auto_id', string='Notifications')
    log_ids = fields.One2many(
        comodel_name='mobile.notification.log', inverse_name='notification_auto_id', string='Logs')
    number = fields.Integer(
        default=30, string='Number')
    interval_number = fields.Integer(
        default=1, help="Repeat every x.", required=False)
    interval_type = fields.Selection([('minutes', 'Minutes'),
                                      ('hours', 'Hours'),
                                      ('days', 'Days'),
                                      ('weeks', 'Weeks'),
                                      ('months', 'Months')], string='Interval Unit', default='days', required=False)
    nextcall = fields.Datetime(string='Next Execution Date', required=False,
                               default=fields.Datetime.now, help="Next planned execution date for this job.")

    def _safe_eval(self, records, data):
        self.ensure_one()
        try:
            context = {
                'object': self,
                'records': records,
                'record': records and len(records) > 0 and records[0] or records,
                'user': self.env.user,
                'datetime': datetime,
                'date': datetime,
                'timedelta': timedelta,
            }
            result = safe_eval(data, context)
            return result
        except Exception as e:
            pass
        return data

    def log(self, log=False, type=_('Error')):
        self.ensure_one()
        if log:
            self.write({
                'log_ids': [(0, 0, {
                    'log': log,
                    'type': type
                })]
            })

    @api.constrains('type')
    def _check_type(self):
        for rec in self:
            if self.search_count([('type', '=', rec.type), ('id', '!=', rec.id)]):
                raise ValidationError(_("Duplicate"))

    def _check_active_cron(self):
        self.ensure_one()
        return self.run == True

    def toggle_run(self):
        for rec in self:
            if not rec.cron_ids and rec.type in ['1', '2', '7', '9']:
                cron_id = rec.set_cron()
                if not cron_id:
                    raise UserError(_('Can not create cron.'))
            rec.run = not rec.run
            if rec.cron_ids:
                rec.cron_ids.sudo().write({
                    'active': rec._check_active_cron()
                })

    def write(self, values):
        # Add code here
        if any(val in ['interval_number', 'interval_type', 'nextcall'] for val in values):
            value = {}
            if 'interval_number' in values:
                value['interval_number'] = values.get('interval_number')
            if 'interval_type' in values:
                value['interval_type'] = values.get('interval_type')
            if 'nextcall' in values:
                value['nextcall'] = values.get('nextcall')
            cron_ids = self.mapped('cron_ids')
            if cron_ids:
                cron_ids.sudo().write(value)
        return super(MobileNotificationAuto, self).write(values)

    def unlink(self):
        # Add code here
        if any(auto.run for auto in self):
            raise UserError(_("Can not Delete Run Record"))
        cron_ids = self.mapped('cron_ids')
        if cron_ids:
            cron_ids.sudo().unlink()
        return super(MobileNotificationAuto, self).unlink()

    def _get_code_model(self, type):
        self.ensure_one()
        if int(type) == 1:
            return 'model.action_notification_expired_loyalty()', self.env.ref("base.model_res_partner").id
        if int(type) == 2:
            return 'model.action_notification_change_date_level()', self.env.ref("base.model_res_partner").id
        if int(type) == 7:
            return 'model.action_notification_birthday()', self.env.ref("base.model_res_partner").id
        if int(type) == 9:
            return 'model.action_notification_payment()', self.env.ref("point_of_sale.model_pos_order").id
        return False, False

    def set_cron(self):
        self.ensure_one()
        code, model_id = self._get_code_model(int(self.type or 0))
        if not code:
            return False
        return self.env['ir.cron'].sudo().create({
            'name': '%s: %s' % (_('Notification Auto'), self.type),
            'active': False,
            'model_id': model_id,
            'state': 'code',
            'code': code,
            'interval_number': self.interval_number,
            'interval_type': self.interval_type,
            'numbercall': -1,
            'nextcall': self.nextcall,
            'notification_auto_id': self.id
        })
