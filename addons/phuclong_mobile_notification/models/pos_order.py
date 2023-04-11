from odoo import api, fields, models, tools, _, SUPERUSER_ID
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

_intervalTypes = {
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7*interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}


class POSOrder(models.Model):
    _inherit = 'pos.order'

    def cancel_order(self):
        result = super(POSOrder, self).cancel_order()
        if self._context.get('cancel_from_wizard', False):
            auto_id = self.env.ref(
                'phuclong_mobile_notification.mobile_notification_auto_6')
            if auto_id and auto_id.run == True:
                try:
                    for rec in self:
                        if rec.partner_id and rec.order_in_app:
                            self.env['mobile.notification'].sudo().with_context(send_now=True).create({
                                'name': auto_id._safe_eval(rec, auto_id.title),
                                'message': auto_id._safe_eval(rec, auto_id.message),
                                'display': auto_id.display,
                                'noti_type': auto_id.noti_type,
                                'image_1920': auto_id.image_1920,
                                'image_thumbnail': auto_id.image_thumbnail,
                                'link_type': 'pos',
                                'pos_order_id': rec.id,
                                'partner_ids': [(6, 0, rec.partner_id.ids)],
                                'notification_auto_id': auto_id.id,
                            })
                except Exception as e:
                    auto_id.log(str(e))
        return result

    def action_notification_payment(self):
        auto_id = self.env.ref(
            'phuclong_mobile_notification.mobile_notification_auto_9')
        if auto_id and auto_id.run == True:
            try:
                create_date = fields.Datetime.now(
                ) - _intervalTypes[auto_id.interval_type](auto_id.interval_number)
                pos_orders = self.search([('partner_id', '!=', False), ('order_in_app', '=', True), (
                    'create_date', '>', create_date), ('state', '=', 'draft')])
                for rec in pos_orders:
                    if rec.partner_id.type != 'contact':
                        continue
                    self.env['mobile.notification'].sudo().with_context(send_now=True).create({
                        'name': auto_id._safe_eval(rec, auto_id.title),
                        'message': auto_id._safe_eval(rec, auto_id.message),
                        'display': auto_id.display,
                        'noti_type': auto_id.noti_type,
                        'image_1920': auto_id.image_1920,
                        'image_thumbnail': auto_id.image_thumbnail,
                        'link_type': 'pos',
                        'pos_order_id': rec.id,
                        'partner_ids': [(6, 0, rec.partner_id.ids)],
                        'notification_auto_id': auto_id.id,
                    })
            except Exception as e:
                auto_id.log(str(e))

    def notification_pos(self):
        result = super(POSOrder, self).notification_pos()
        auto_id = self.env.ref(
            'phuclong_mobile_notification.mobile_notification_auto_8')
        if auto_id and auto_id.run == True:
            try:
                for rec in self:
                    if rec.partner_id and rec.order_in_app:
                        if rec.partner_id.type != 'contact':
                            continue
                        self.env['mobile.notification'].sudo().with_context(send_now=True).create({
                            'name': auto_id._safe_eval(rec, auto_id.title),
                            'message': auto_id._safe_eval(rec, auto_id.message),
                            'display': auto_id.display,
                            'noti_type': auto_id.noti_type,
                            'image_1920': auto_id.image_1920,
                            'image_thumbnail': auto_id.image_thumbnail,
                            'link_type': 'pos',
                            'pos_order_id': rec.id,
                            'partner_ids': [(6, 0, rec.partner_id.ids)],
                            'notification_auto_id': auto_id.id,
                        })
            except Exception as e:
                auto_id.log(str(e))
        return result
