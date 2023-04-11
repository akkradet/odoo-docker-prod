# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError

class SalePromoHeader(models.Model):
    _inherit = "sale.promo.header"

    order_type = fields.Selection([('all','All'),
                                   ('pos', 'Sale B2C'),
                                   ('sale', 'Sale B2B'),
                                   ], string='Apply To', required=True, default='all')
    sale_type_ids = fields.Many2many('pos.sale.type', 'promotion_sale_type_rel', 'promotion_id', 'sale_type_id', string='Sale Type')
    pos_payment_method_id = fields.Many2one('pos.payment.method', string='Payment Method', ondelete="cascade")
    day_of_week = fields.Many2many('day.of.week.config', 'promotion_day_rel', 'promotion_id', 'day_id', string='Day of Week')
    
class SalePromoLines(models.Model):
    _inherit = "sale.promo.lines"
        
    @api.model
    def _get_product_attribute(self):
        product_attribute = [('product_template',_('Product Template')),
                      ('combo',_('Product List')),
                      ('cat',_('Category')),
                      ('list_cat',_('List Categories')),
                      ('order', _('Order Amount'))]
        if self.env['res.users'].has_group('product.group_product_variant'):
            product_attribute.append(('product',_('Product')))
        return product_attribute
    
    @api.model
    def _get_benefit_type(self):
        benefit_type = [('product_template',_('Product Template')),
                          ('cat',_('Category')),
                          ('list_cat',_('List Categories')),
                          ('list_product_template',_('List Product Template')),
                          ('combo_product',_('Combo Product'))]
        if self.env['res.users'].has_group('product.group_product_variant'):
            benefit_type.append( ('product',_('Product')))
        return benefit_type
    
    product_attribute = fields.Selection(selection='_get_product_attribute', 
                                         string='Apply On', default='product_template', required= True)
    check_orgin_price = fields.Boolean(string='Apply on Origin Product Price', default=True)
    amount_discount_limit = fields.Float(default=0)
    same_price = fields.Boolean('Same and lower price products',default=True)
    product_benefit_ids = fields.One2many('sale.promo.lines.benefit', 'promo_line_id', string="Combo Product")
    reward_code_ids = fields.Many2many('reward.code.publish', 'promotion_reward_rel', 'promotion_id', 'reward_id', string='Reward Codes')
    product_default_code = fields.Char(related="benefit_product_tmpl_id.default_code")
    count_discount_limit = fields.Integer(default=0)
    
    @api.model
    def default_get(self, fields):
        context = self._context or {}
        res = super(SalePromoLines, self).default_get(fields)
        res.update({'break_type':'Point'})
        return res
    
    @api.constrains('product_attribute', 'benefit_type', 'benefit_product_tmpl_id' , 'benefit_categ_id', 'benefit_product_tmpl_ids', 'benefit_categ_ids', 'product_benefit_ids')
    def check_benefit(self):
        for line in self:
            if not (line.product_attribute in ('order','combo') and line.modify_type != 'pro_goods'):
                if (line.benefit_type == 'product_template' and not line.benefit_product_tmpl_id)\
                    or (line.benefit_type == 'list_product_template' and not line.benefit_product_tmpl_ids)\
                    or (line.benefit_type == 'cat' and not line.benefit_categ_id)\
                    or (line.benefit_type == 'list_cat' and not line.benefit_categ_ids)\
                    or (line.benefit_type == 'combo_product' and not len(line.product_benefit_ids)):
                    raise UserError(_("Please input benefit of promotion !"))
    
#     @api.onchange('benefit_product_tmpl_id')
#     def on_change_benefit_product_tmpl_id(self):
#         result = {}
#         if self.benefit_product_tmpl_id and self.benefit_product_tmpl_id.default_code == 'reward_code':
#             promo_line_rewards = self.search([('reward_code_ids','!=',False)])
#             reward_list = promo_line_rewards.mapped('reward_code_ids')
#             reward_ids = reward_list.ids
#             reward_domain = [
#                 ('id', 'not in', reward_ids)
#             ]
#             result = {
#                 'domain': {
#                     'reward_code_ids': reward_domain,
#                 },
#             }
#         return result
    
class SalePromoLinesBenefit(models.Model):
    _name = "sale.promo.lines.benefit"
    _description = "SalePromoLinesBenefit"
    
    product_ids = fields.Many2many('product.template', 'promo_line_benefit_product_rel', 'promo_line_benefit_id', 'product_id', string="Products")
    allow_additional_price = fields.Boolean(default=False)
    additional_price = fields.Float(default=0.0)
    product_qty = fields.Float(string="Quantity", default=1)
    promo_line_id = fields.Many2one('sale.promo.lines', required=True, ondelete='cascade')
    
class RewardCodePublish(models.Model):
    _inherit = "reward.code.publish"
    
    promotion_ids = fields.Many2many('reward.code.publish', 'promotion_reward_rel', 'reward_id', 'promotion_id', string='Promotion')
    
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        args = args or []
        context = self._context or {}
        if context.get('benefit_type') and context.get('product_default_code') and not context.get('search_pass_promotion'):
            if context.get('benefit_type') == 'product_template' and context.get('product_default_code') == 'reward_code':
                promo_line_rewards = self.env['sale.promo.lines'].with_context(search_pass_promotion=True).search([('benefit_product_tmpl_id','!=',False),
                                                  ('benefit_product_tmpl_id.default_code','=','reward_code'),
                                                  ('reward_code_ids','!=',False)])
                reward_list = promo_line_rewards.mapped('reward_code_ids')
                reward_ids = reward_list.ids
                args += [('id', 'not in', reward_ids)]
        return super(RewardCodePublish, self).search(args, offset, limit, order, count=count)
    
    
    
    
    