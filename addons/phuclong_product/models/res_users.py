# -*- coding: utf-8 -*-

from odoo import api, fields, models, SUPERUSER_ID
from odoo.tools import safe_eval

class ResUser(models.Model):
    _inherit = 'res.users'

    @api.depends('category_allow_ids')
    def _get_product_category_dom(self):
        for user in self:
            if user.category_allow_ids:
                categ_list = self.env['product.category']
                for categ in user.category_allow_ids:
                    child_categ_ids = self.env['product.category'].search([('id','child_of',categ.id)])
                    categ_list |= child_categ_ids
            else:
                categ_list = self.env['product.category'].search([])
            domain = "[%s]"%(','.join(map(str, [i.id for i in categ_list])))
            user.product_category_dom = domain
            
    category_allow_ids = fields.Many2many('product.category', 'res_users_product_category_rel', 'user_id', 'category_id', string='Product Category')
    product_category_dom = fields.Char(compute='_get_product_category_dom', store=True)

    @api.constrains('category_allow_ids')
    def check_category_allow_ids(self):
        self.update_profile()
        
    def _product_category_domain(self):
        domain = "[]"
        if self.product_category_dom:
            domain = safe_eval(self.product_category_dom) 
        return domain
