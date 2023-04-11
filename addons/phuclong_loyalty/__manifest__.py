# -*- coding: utf-8 -*-
{
    'name': 'PhucLong Loyalty',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'depends': [
        'besco_loyalty',
        'phuclong_cardcode',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/update_loyalty_expired_date_views.xml',
        'views/menu.xml'
    ],
    'installable': True,
    'auto_install': False,
}
