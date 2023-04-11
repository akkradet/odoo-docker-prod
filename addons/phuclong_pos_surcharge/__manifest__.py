# -*- coding: utf-8 -*-
{
    'name': 'PhucLong POS Surcharge',
    'category': 'PhucLong',
    'author': 'BESCO Consulting (chris.vang <thai.vang@besco.vn>)',
    'depends': [
        'phuclong_pos_base',
    ],
    'data': [
        # security
        'security/security.xml',
        'security/ir.model.access.csv',
        # views
        'views/surcharge_view.xml',
        'views/action.xml',
        'views/menu_item.xml',
        'views/assets.xml',
        'views/order.xml'
    ],
    'installable': True,
    'auto_install': False,
}
