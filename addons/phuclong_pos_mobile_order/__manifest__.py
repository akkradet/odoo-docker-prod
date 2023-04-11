# -*- coding: utf-8 -*-
{
    'name': 'PhucLong POS Mobile Order',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'depends': ['phuclong_pos_giftcode', 'phuclong_mobile_backend', 'phuclong_pos_stock'],
    'data': [
        'wizard/wizard_cancel_pos_order_reason_view.xml',
        'views/pos_order_views.xml',
        'views/templates.xml',
    ],
    "qweb": [
        "static/src/xml/pos_mobile.xml",
    ],
    'installable': True,
    'auto_install': False,
}
