# -*- coding: utf-8 -*-
from odoo import fields, models, api


class POSConfig(models.Model):
    _inherit = "pos.config"

    sale_type_ids = fields.Many2many(
        'pos.sale.type',
        'config_saletype_rel', 'config_id', 'sale_type_id',
        string='Sale type')
    sale_type_default_id = fields.Many2one(
        'pos.sale.type', string="Sale type default")
    is_dollar_pos = fields.Boolean('Use dollar', default=False)
    logo = fields.Binary('Receipt Logo', copy=False)
    use_barcode_scanner_to_open_session = fields.Boolean(
        'Open Session via Card', default=True)
    use_multi_printer = fields.Boolean(
        'Use multiple printers', default=False)

    is_sandbox_env = fields.Boolean('Is Sanbox enviroment')
    max_order_to_create = fields.Integer(
        'Number of orders will be duplicated and saved\
            to DB on POS at the same time after each POS Order',
        default=7)
    update_cashier_to_session = fields.Boolean(default=False)
    use_for_mobile = fields.Boolean("Use for Mobile App", default=True)
    is_callcenter_pos = fields.Boolean("Is Call Center POS", default=False)
    stock_location_id = fields.Many2one(
        'stock.location', string='Stock Location',
        domain=[('usage', '=', 'internal')], required=False)
    use_replacement_printer = fields.Boolean('Use Replacement Printer', default=False)
    printer_ip = fields.Char('IP Address')
    
    @api.onchange('is_callcenter_pos')
    def on_change_is_callcenter_pos(self):
        domain = []
        if self.is_callcenter_pos:
            self.sale_type_default_id = False
            self.stock_location_id = False
            domain = [
                ('use_for_call_center','=',True)
            ]
        result = {
            'domain': {
                'sale_type_default_id': domain,
            },
        }
        return result
    
    
    def update_pos_config_printer(self, ip):
        if not ip:
            if not self.use_replacement_printer and not self.printer_ip:
                return True
            self._cr.execute('''UPDATE pos_config SET use_replacement_printer = false, printer_ip= null WHERE id = %s'''%(self.id))
        else:
            if self.use_replacement_printer and self.printer_ip == ip:
                return True
            self._cr.execute('''UPDATE pos_config SET use_replacement_printer = true, printer_ip='%s' WHERE id = %s'''%(ip, self.id))
        return True

    @api.depends(
        'journal_id.currency_id',
        'journal_id.company_id.currency_id',
        'company_id',
        'company_id.currency_id',
        'is_dollar_pos')
    def _compute_currency(self):
        for pos_config in self:
            dollar_currency_id = False
            if pos_config.is_dollar_pos:
                dollar_currency_id = self.env['res.currency'].search([('name', '=', 'USD')], limit=1) or False
                
            if dollar_currency_id:
                pos_config.currency_id = dollar_currency_id.id
            else:
                if pos_config.journal_id:
                    pos_config.currency_id = pos_config.journal_id.currency_id.id or pos_config.journal_id.company_id.currency_id.id
                else:
                    pos_config.currency_id = pos_config.company_id.currency_id.id