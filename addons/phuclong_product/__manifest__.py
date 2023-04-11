# -*- coding: utf-8 -*-
{
    'name': 'PhucLong Product',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'depends': ['besco_product'],
    'data': [
        'security/ir.model.access.csv',
        'data/product_material_option_data.xml',
        'views/product_size.xml',
        'views/product_category_view.xml',
        'views/pos_category_view.xml',
        'views/product_template_view.xml',
        'views/product_material_views.xml',
        'views/product_custom_material.xml',
        'views/res_users_view.xml',
        'views/templates.xml'
    ],
    'installable': True,
    'auto_install': False,
}
