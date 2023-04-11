# -*- coding: utf-8 -*-
{
    'name': 'PhucLong POS Login IP',
    'category': 'PhucLong',
    'depends': [
        'phuclong_pos_theme'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/pos_address_config.xml',
    ],
    'qweb': [
        'static/src/qweb/templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}
