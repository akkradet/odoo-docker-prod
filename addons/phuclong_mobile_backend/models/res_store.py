from odoo import api, fields, models, _

class ResStore(models.Model):
    _name = 'res.store'
    _inherit = ['image.mixin']
    _description = 'Store'

    @api.model
    def _default_duration_ids(self):
        res = []
        day_of_weeks = self.env['day.of.week.config'].search([])
        for day in day_of_weeks:
            res.append((0, 0, {
                'name': day.id,
                'opening_time': 7.00,
                'closing_time': 22.50,
            }))
        return res

    name = fields.Char(string="Name", required=1)
    address = fields.Char(string="Address", required=1)
    delivery_hotline = fields.Char(string="Delivery Hotline", required=1)
    customer_hotline = fields.Char(string="Customer Hotline", required=1)
    active = fields.Boolean(string="Active", default=True)
    warehouse_id = fields.Many2one('stock.warehouse',string="Warehouse")
    latitude = fields.Char('Latitude', help="Vĩ Độ")
    longitude = fields.Char('Longitude', help="Kinh Độ")
    state_id = fields.Many2one('res.country.state', string="City")
    durations_ids = fields.One2many('duration.open.store', 'store_id', 'Duration Time', default=_default_duration_ids)

class DurationOpenStore(models.Model):
    _name = 'duration.open.store'

    name = fields.Many2one('day.of.week.config', 'Weekdays')
    store_id = fields.Many2one('res.store')
    opening_time = fields.Float('Opening Time')
    closing_time = fields.Float('Closing Time')