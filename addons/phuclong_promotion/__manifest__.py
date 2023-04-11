# -*- coding: utf-8 -*-
{
    'name': 'PhucLong Promotion',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'depends': ['phuclong_pos_promo_combo', 'phuclong_pos_reward_code'],
    'data': [
        'security/ir.model.access.csv',
        'views/templates.xml',
        'views/promotion_view.xml',
        'views/pricelist_view.xml'
    ],
    'installable': True,
    'auto_install': False,
}
