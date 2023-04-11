# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class UpdateCardcodePublish(models.TransientModel):
    _name = "wizard.update.cardcode.publish"

    cardcode_publish_id = fields.Many2one(
        'cardcode.publish', string='Cardcode Publish')
    date_expired = fields.Date(string="Expired Date",)
    date_created = fields.Date(string="Date",)

    def update_date(self):
        publish = self.cardcode_publish_id
        if publish and publish.cardcode_line:
            publish.cardcode_line.write({
                'date_created': self.date_created,
                'date_expired': self.date_expired,
            })
        return
