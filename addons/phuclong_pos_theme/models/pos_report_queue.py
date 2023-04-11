from odoo import api, fields, models, _
from datetime import timedelta
import base64
from odoo.exceptions import UserError

class PosReportQueueConfig(models.Model):
    _name = 'pos.report.queue.config'
    _description = 'Pos Report Queue Config'
    _order = 'create_date DESC'

    type = fields.Selection([
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('payment_method', 'Payment Method'),
        ('revenue_product', 'Product'),
        ('revenue_product_vat', 'Product VAT'),
        ('revenue_stores', 'Revenue Stores'),
        ('payment_method_bill', 'Payment Method By Bill'),
        ('payment_method_day', 'Payment By Day'),
        ('combo', 'Revenue Combo'),
        ('discount', 'Discount')
    ], string='Report Name',
        default='revenue_stores',
    )
    duration = fields.Integer(string='Duration (days)', default=1)
    number_of_shops = fields.Integer(string='Number of Shops', default=1)

    @api.onchange('duration', 'number_of_shops')
    def _onchange_duration_number_of_shops(self):
        if not self.duration or self.duration <= 0 or not self.number_of_shops or self.number_of_shops <= 0:
            raise UserError(_('Duration and Number of Shop must be greater than 0.'))

    def get_queue(self, type, duration, number_of_shops):
        return self.search_count([
            ('type', '=', type),
            ('duration', '<=', duration),
            ('number_of_shops', '<=', number_of_shops)
        ]) != 0


class PosReportQueueOutput(models.Model):
    _name = 'pos.report.queue.output'
    _description = 'Pos Report Queue Output'
    _rec_name = 'report_name'
    _order = 'create_date DESC'

    def unlink(self):
        # Add code here
        cron_ids = self.sudo().mapped('cron_id')
        if cron_ids:
            cron_ids.sudo().unlink()
        return super(PosReportQueueOutput, self).unlink()

    ir_actions_report_id = fields.Many2one(
        'ir.actions.report', string='Report')
    cron_id = fields.Many2one(
        'ir.cron', string='Cron')
    report_name = fields.Char(string='Name')
    report_data = fields.Binary(string='Attachment', attachment=True)
    date_complete = fields.Datetime(string='Completion Date')
    log_error = fields.Text(string='Log Error')
    state = fields.Selection(string='Status', selection=[(
        'in_progress', 'In Progress'), ('done', 'Done'), ('error', 'Error')], default='in_progress')

    @api.model
    def create(self, values):
        # Add code here
        queue = super(PosReportQueueOutput, self).create(values)
        queue.action_run()
        return queue

    def set_cron(self, values):
        self.ensure_one()
        return self.env['ir.cron'].sudo().create({
            'name': '%s: %s' % (_('Generate Report Queue'), values.get('report_name')),
            'active': True,
            'model_id': self.env['ir.model'].sudo().search([('model', '=', self._name)], limit=1).id,
            'state': 'code',
            'code': 'model._cron_report_data(%s)' % self.id,
            'interval_number': 0,
            'interval_type': 'minutes',
            'numbercall': 1,
            'nextcall': fields.Datetime.now() - timedelta(minutes=10),
        })

    def action_run(self):
        self = self.sudo()
        for rec in self:
            if not rec.cron_id:
                cron_id = self.set_cron({
                    'report_name': rec.report_name
                })
                log_error = False
                state = 'in_progress'
                if not cron_id:
                    log_error = _('Can not create cron.')
                    state = 'error'
                rec.write({
                    'cron_id': cron_id and cron_id.id or False,
                    'state': state,
                    'log_error': log_error
                })
            else:
                rec.cron_id.write({
                    'numbercall': 1
                })
                rec.write({
                    'state': 'in_progress',
                    'log_error': False
                })

    warehouse_ids = fields.Many2many(
        'stock.warehouse',
        'queue_revenue_report_warehouse_rel',
        'queue_id', 'warehouse_id',
        string='Stores')
    date_from = fields.Date('Date Time From', require=True)
    date_to = fields.Date('Date Time To')
    start_hour = fields.Float(string='Start Hour', default=0.0)
    end_hour = fields.Float(string='End Hour', default=23.983)
    type = fields.Selection([
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('payment_method', 'Payment Method'),
        ('revenue_product', 'Product'),
        ('revenue_product_vat', 'Product VAT'),
        ('revenue_stores', 'Revenue Stores'),
        ('payment_method_bill', 'Payment Method By Bill'),
        ('payment_method_day', 'Payment By Day'),
        ('combo', 'Revenue Combo'),
        ('discount', 'Discount')
    ], string='Report Type',
        default='hourly',
    )
    combo_id = fields.Many2one('sale.promo.combo', string='Combo')
    no_vat = fields.Boolean('No VAT')
    
    def _cron_report_data(self, res_id):
        self.browse(res_id)._set_report_data()

    def _cron_unlink_cron(self):
        record_ids = self.search([('state', '=', 'done')])
        cron_ids = record_ids.mapped('cron_id')
        if cron_ids:
            cron_ids.unlink()

    def _set_report_data(self):
        self.ensure_one()
        report_name = self.report_name
        try:
            if self.ir_actions_report_id and self.state == 'in_progress':
                wizard_id = self.env['wizard.report.pos.revenue'].create({
                    'warehouse_ids': [(6, 0, self.warehouse_ids.ids)],
                    'date_from': self.date_from,
                    'date_to': self.date_to,
                    'start_hour': self.start_hour,
                    'end_hour': self.end_hour,
                    'type': self.type,
                    'combo_id': self.combo_id and self.combo_id.id or False,
                })
                data = {}
                data['ids'] = wizard_id.ids
                data['form'] = wizard_id.read([])[0]
                report_data, converter_type = self.ir_actions_report_id.render(
                    wizard_id.ids, data)
                self.write({
                    'report_name': str(report_name) + converter_type,
                    'report_data': base64.b64encode(report_data),
                    'state': 'done',
                    'date_complete': fields.Datetime.now(),
                    'log_error': False
                })
                self.create_uid.notify_success(
                    message=_('The report %s of %s has been successfully completed. Please access the menu <button %s>Report in Queue</button> to check the result.') % (report_name, self.create_uid.display_name, "class='btn btn-primary do-action-click' data-name='%s' data-res-id='%s' data-res-model='%s' data-target='new'" % (report_name, self.id, self._name)), sticky=True)
        except Exception as e:
            self.write({
                'log_error': str(e),
                'state': 'error',
                'report_name': report_name
            })
            self.create_uid.notify_danger(
                message=_('The report %s of %s has been failed completed. Please access the menu <button %s>Report in Queue</button> to run the report again.') % (report_name, self.create_uid.display_name, "class='btn btn-primary do-action-click' data-name='%s' data-res-id='%s' data-res-model='%s' data-target='new'" % (report_name, self.id, self._name)), title=_('Failure'), sticky=True)
