# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import time
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import pytz
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class WarehouseTransferQuantityHistory(models.TransientModel):
    _inherit = "warehouse.transfer.quantity.history"
    
    @api.model
    def _get_from_date(self):
        date_format = "%Y-%m-%d 17:00:00"
        date = fields.Datetime.now().strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        date = date - timedelta(days=1)
        from_date = date.strftime(date_format) 
        return from_date
    
    @api.model
    def _get_to_date(self):
        today = self.env['res.users']._convert_user_datetime(fields.Datetime.now())
        to_date = today.date().strftime("%Y-%m-%d 16:59:59")
        return to_date

    date_request_from = fields.Datetime(string='Request From', default=_get_from_date)
    date_request_to = fields.Datetime(string='Request To', default=_get_to_date)

    def open_table(self):
        result = super(WarehouseTransferQuantityHistory, self).open_table()
        domain = [('transfer_id.date_request', '>=', self.date_request_from),
                  ('transfer_id.date_request', '<=', self.date_request_to)]
        result['domain'] += domain
        return result

    def get_date_format_string(self, date):
        date = date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        tz_user = \
            pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
        date = pytz.utc.localize(datetime.strptime(
                date, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(tz_user)
        return date.strftime('%d/%m/%Y %H:%M:%S')
    
    def get_vietname_date(self, date):
        date = self.env['res.users']._convert_user_datetime(date)
        return date.strftime('%d/%m/%Y %H:%M:%S')
    
    def get_date_start(self):
        date = self.get_vietname_date(self.date_request_from)
        return date

    def get_date_end(self):
        date = self.get_vietname_date(self.date_request_to)
        return date

    def get_current_date(self):
        date = time.strftime(DATETIME_FORMAT)
        date = self.env['res.users']._convert_user_datetime(date)
        return date.strftime('%d/%m/%Y %H:%M:%S')

    def get_picking(self, transfer_id, product_id, supplier_wh_id):
        transfer_id = transfer_id
        product_id = product_id
        supplier_wh_id = self.env['stock.warehouse'].sudo().browse(supplier_wh_id)
        picking_name = ''
        move_ids = self.env['stock.move'].sudo().search([
            ('transfer_line_id.transfer_id', '=', transfer_id),
            ('product_id', '=', product_id),
            ('location_id.warehouse_id', '=', supplier_wh_id.id)])
        if move_ids:
            picking_name = ' ,'.join(map(str, [x.name for x in move_ids.mapped('picking_id')]))
        return picking_name

    def get_picking_dest(self, transfer_id, product_id, supplied_wh_id):
        transfer_id = transfer_id
        product_id = product_id
        supplied_wh_id = self.env['stock.warehouse'].sudo().browse(supplied_wh_id)
        picking_name = ''
        move_ids = self.env['stock.move'].sudo().search([
            ('transfer_line_id.transfer_id', '=', transfer_id),
            ('product_id', '=', product_id),
            ('location_dest_id.warehouse_id', '=', supplied_wh_id.id)])
        if move_ids:
            picking_name = ' ,'.join(map(str, [x.name for x in move_ids.mapped('picking_id')]))
        return picking_name

    def load_data_details(self):
        warehouse_ids = ''
        if self.warehouse_ids:
            warehouse_ids = 'and wt.supplier_wh_id in (%s)' % (','.join(map(str, [x.id for x in self.warehouse_ids])))
        sql = '''
        select
            wt.id as transfer_id, pp.id as product_id,
            wt.name, wtl.product_id,
            wt.date_request,
            wt.supplier_wh_id,
            sw_er.name as sw_supplier,
            wt.supplied_wh_id,
            sw_ed.name as sw_supplied,
            wt.origin,
            pt.ref_code,
            uom.name as uom_name,
            pt.name as product_name,
            SUM(COALESCE(wtl.qty_issued, 0)) as qty_issued,
            SUM(COALESCE(wtl.qty_received , 0)) as qty_received

        from warehouse_transfer_line wtl
        left join warehouse_transfer wt on wt.id = wtl.transfer_id
        left join product_product pp on pp.id = wtl.product_id
        left join product_template pt on pt.id = pp.product_tmpl_id
        left join uom_uom uom on uom.id = pt.uom_id
        left join stock_warehouse sw_er on sw_er.id = wt.supplier_wh_id
        left join stock_warehouse sw_ed on sw_ed.id = wt.supplied_wh_id

        where wt.state in ('transfer', 'done')
        and (wtl.qty_issued != 0 or wtl.qty_received != 0)
        and timezone('UTC', wt.date_request::timestamp) between timezone('UTC','%(date_request_from)s'::timestamp) and timezone('UTC','%(date_request_to)s'::timestamp)
        %(warehouse_id)s
        group by
                wt.id, pp.id,
                wt.name, wtl.product_id,
                wt.supplied_wh_id, wt.supplier_wh_id,
                wt.origin,pt.ref_code,uom.name,pt.name,
                wt.date_request,
                sw_er.name,
                sw_ed.name
        order by wt.date_request
        ''' % ({
            'warehouse_id': warehouse_ids,
            'date_request_from': self.date_request_from,
            'date_request_to': self.date_request_to,
        })
        self._cr.execute(sql)
        return self._cr.dictfetchall()

    def print_transfer_details(self):
        return self.env.ref(
                'phuclong_warehouse_transfer.report_warehouse_transfer_details').report_action(self)

