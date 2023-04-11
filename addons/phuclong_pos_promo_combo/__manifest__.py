# -*- coding: utf-8 -*-
{
    'name': 'PhucLong POS Promotion for Combo',
    'category': 'PhucLong',
    'author': 'BESCO Consulting (chris.vang <thai.vang@besco.vn>)',
    'depends': [
        'phuclong_pos_base',
    ],
    'data': [
        'views/assets.xml',
        'data/day_of_week.xml',
        'views/promo_combo.xml',
        'views/pos_order_line.xml',
        'views/day_of_week.xml',
        'views/coupon_combo_view.xml',
        'security/security.xml',
        'views/menu.xml',
        'security/ir.model.access.csv',
        'report/report_py3o.xml',
        'report/report_coupon_voucher.xml'
    ],
    'installable': True,
    'auto_install': False,
}
