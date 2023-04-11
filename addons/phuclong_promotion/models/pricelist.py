# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError

class ProductPricelist(models.Model):
    _inherit = "product.pricelist"
    
    @api.depends('currency_id', 'is_dollar_pos')
    def _get_dollar_currency(self):
        for pricelist in self:
            if pricelist.is_dollar_pos:
                dollar_currency_id = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
                if dollar_currency_id:
                    pricelist.dollar_currency_id = dollar_currency_id.id
                else:
                    pricelist.dollar_currency_id = pricelist.currency_id.id
            else:
                pricelist.dollar_currency_id = pricelist.currency_id.id

    sale_type_ids = fields.Many2many('pos.sale.type', 'pricelist_sale_type_rel', 'pricelist_id', 'sale_type_id', string='Sale Type')
    is_dollar_pos = fields.Boolean('Is Dollar Pricelist', default=False, copy=False)
    dollar_currency_id = fields.Many2one('res.currency', compute='_get_dollar_currency', string='Dollar Currency', readonly=False, store=True)
    
    @api.onchange('is_dollar_pos')
    def _onchange_is_dollar_pos(self):
        res = {}
        for pricelist in self:
            if pricelist.is_dollar_pos:
                dollar_currency_id = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
                if not dollar_currency_id:
                    pricelist.is_dollar_pos = False
                    res['warning'] = {'title': _('Warning'), 'message': _('Dollar currency (USD) is not active')}
                    return res
    
    
class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"   
    
    def init(self):
        field_id = self.env['ir.model.fields']._get(self._name, 'compute_price').selection_ids.filtered(lambda l:l.value == 'formula')
        if field_id:
            self._cr.execute('DELETE FROM ir_model_fields_selection WHERE id = %s'%(field_id.id))
        return
    
    compute_price = fields.Selection(selection=[('fixed', 'Fix Price'), 
                                      ('percentage', 'Percentage (discount)')])
    dollar_currency_id = fields.Many2one(
        'res.currency', 'Dollar Currency',
        readonly=True, related='pricelist_id.dollar_currency_id', store=True)
    
