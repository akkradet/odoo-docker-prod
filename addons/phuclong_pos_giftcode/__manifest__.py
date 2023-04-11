# -*- coding: utf-8 -*-
{
    'name': 'PhucLong POS Giftcode',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'depends': [
        'phuclong_pos_theme',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/payment_method.xml',
        'views/template.xml',
        'views/views.xml',
        'views/config.xml',
        'views/menu.xml',
    ],
    'qweb': [
        'static/src/xml/popup.xml'
    ],
    'installable': True,
    'auto_install': False,
}
