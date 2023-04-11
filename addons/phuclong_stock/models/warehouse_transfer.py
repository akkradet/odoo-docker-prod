from odoo import api, models, fields,  _
from odoo.exceptions import ValidationError


class WarehouseTransfer(models.Model):
    _inherit = "warehouse.transfer"

    @api.constrains('is_return_transfer')
    def check_return_transfer(self):
        return

    @api.constrains('date_planned', 'date_request')
    def _check_date_planned_date_request(self):
        for rec in self:
            if rec.date_planned and rec.date_request and rec.date_planned < rec.date_request:
                raise ValidationError(
                    _("Scheduled Date must be equal or later than Order Date"))
