# -*- coding: utf-8 -*-
{
    'name': 'PhucLong Voucher & Coupon Management',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'depends': [
        'besco_voucher_coupon',
    ],
    'data': [
        'security/security.xml',
        'wizard/wizard_check_voucher_coupon_view.xml',
        'views/menu.xml',
        'views/crm_voucher_info_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
