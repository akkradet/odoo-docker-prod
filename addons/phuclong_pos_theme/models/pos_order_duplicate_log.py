# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import ast

class PosOrderDuplicateLog(models.Model):
    _name = 'pos.order.duplicate.log'
    _description = 'pos.order.duplicate.log'
    
    name = fields.Char('Pos Reference')
    amount_total = fields.Float()
    warehouse_id = fields.Many2one('stock.warehouse', string="Store")
    date_order = fields.Datetime()
    log_data = fields.Text()
    recreated = fields.Boolean(default=False)
    
    def recreate_order(self):
        if not self.env.is_admin():
            raise UserError(_('Only Administrator can do this function'))
        data = ast.literal_eval(self.log_data)
        existing_order = self.env['pos.order'].search([('pos_reference', '=', data['name'])], limit=1)
        if len(existing_order):
            if existing_order.date_order == self.date_order:
                raise UserError(_('The order is existing in system'))
            else:
                data['name'] = data['name'] + '-1'
        data_to_create = {'data':data}
        self.env['pos.order']._process_order(data_to_create, False, False)
        self.recreated = True
    
    @api.model    
    def delete_all_log(self):
        self._cr.execute('''DELETE FROM pos_order_duplicate_log WHERE id IN 
                            (SELECT id FROM pos_order_duplicate_log WHERE DATE_PART('day',current_date::timestamp
                            - date_order::timestamp) > 7) ''')
        return True