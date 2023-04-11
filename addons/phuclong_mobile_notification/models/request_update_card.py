from odoo import models, fields, api, _
from odoo.exceptions import UserError


class RequestUpdateCard(models.Model):
    _inherit = 'request.update.card'

    def action_done(self):
        result = super(RequestUpdateCard, self).action_done()
        auto_id = self.env.ref(
            'phuclong_mobile_notification.mobile_notification_auto_5')
        if auto_id and auto_id.run == True:
            try:
                request_ids = self.filtered(
                    lambda request_id: request_id.partner_id)
                if request_ids:
                    for request_id in request_ids:
                        if request_id.partner_id.type != 'contact':
                            continue
                        self.env['mobile.notification'].sudo().with_context(send_now=True).create({
                            'name': auto_id._safe_eval(request_id, auto_id.title),
                            'message': auto_id._safe_eval(request_id, auto_id.message),
                            'display': auto_id.display,
                            'noti_type': auto_id.noti_type,
                            'image_1920': auto_id.image_1920,
                            'image_thumbnail': auto_id.image_thumbnail,
                            'partner_ids': [(6, 0, request_id.partner_id.ids)],
                            'notification_auto_id': auto_id.id,
                        })
            except Exception as e:
                auto_id.log(str(e))
        return result
