# -*- coding: utf-8 -*-
{
    'name': 'PhucLong Mobile Report',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'depends': [
        'phuclong_mobile_backend',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/report_mobile_order_views.xml',
        'views/pos_payment_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'auto_install': False,
}
