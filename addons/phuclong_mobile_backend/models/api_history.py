from odoo import models, fields, api, _

class APIHistory(models.Model):
    _name = 'api.history'

    _description = 'History API call'

    name = fields.Char('Function')
    time_call = fields.Datetime('Time')
    request_params = fields.Text('Request Parameters')
    message_err = fields.Char('Error')