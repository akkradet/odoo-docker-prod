# -*- coding: utf-8 -*-
{
    'name': 'PhucLong POS Lock Product by Warehouse',
    'category': 'PhucLong',
    'author': 'BESCO Consulting (chris.vang <thai.vang@besco.vn>)',
    'depends': [
        'phuclong_pos_theme', 'web_confirm_on_save', 'phuclong_stock'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/lock_product.xml',
    ],
    'qweb': [
        'static/src/qweb/templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}
