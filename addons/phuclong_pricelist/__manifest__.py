# -*- coding: utf-8 -*-
{
    'name': 'PhucLong Pricelist',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'depends': [
        'besco_pricelist',
        'phuclong_cardcode'
    ],
    'data': [
        'views/product_pricelist_views.xml',
        'views/res_partner_views.xml',
        'views/menu.xml',
        'report/report_py3o.xml'
    ],
    'installable': True,
    'auto_install': False,
}
