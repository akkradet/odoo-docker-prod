# -*- coding: utf-8 -*-
{
    'name': 'PhucLong POS Presentation',
    'category': 'PhucLong',
    'author': 'BESCO Consulting (chris.vang <thai.vang@besco.vn>)',
    'depends': [
        'phuclong_pos_theme'],
    'data': [
        'views/templates.xml',
        'views/config.xml'
    ],
    'qweb': [
        'static/src/qweb/order_present.xml',
    ],
    'installable': True,
    'auto_install': False,
}
