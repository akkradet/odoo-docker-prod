# -*- coding: utf-8 -*-
{
    'name': 'PhucLong POS Modify Payment',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'depends': [
        'phuclong_pos_giftcode',
        'pos_momo_payment',
        'pos_moca_payment',
        'pos_zalo_payment'
    ],
    'data': [
        'views/view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
