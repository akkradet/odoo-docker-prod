# -*- coding: utf-8 -*-
{
    'name': 'PhucLong POS Config',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'depends': ['phuclong_pos_base'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/pos_config.xml',
        'views/banner.xml',
        'views/template.xml',
        # 'crons/auto_disable_banner.xml',
    ],
    'installable': True,
    'auto_install': False,
}
