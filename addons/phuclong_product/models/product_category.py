# -*- coding: utf-8 -*-
from odoo import fields, models, api

class ProductCategory(models.Model):
    _inherit = "product.category"

    fnb_type = fields.Selection([('topping', 'Topping'), ('food', 'Food'),
                                 ('drink', 'Drink'), ('cup', 'Cup'), ('lid', 'Lid'), 
                                 ('packaged_product', 'Packaged Product'),
                                 ('customizable_material', 'Customizable Material'),
                                 ('material', 'Material')], string='FnB Type', copy=False, default=False)
    
    def write(self, vals):
        for categ in self:
            if 'fnb_type' in vals:
                self._cr.execute('''UPDATE product_product pp SET has_cache = false FROM product_template pt JOIN product_category pc 
                                    ON pt.categ_id = pc.id where pp.product_tmpl_id = pt.id and pc.id = %s'''%(categ.id))
        return super(ProductCategory,self).write(vals)
    
