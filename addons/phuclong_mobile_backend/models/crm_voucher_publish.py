# -*- coding: utf-8 -*-

from odoo import api, fields, models


class VoucherPublish(models.Model):
    _inherit = 'crm.voucher.publish'

    apply_only_on_app = fields.Boolean(string='Apply only on App')
