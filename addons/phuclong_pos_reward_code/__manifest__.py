# -*- coding: utf-8 -*-
{
    'name': 'PhucLong POS POS Reward Code',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'depends': ['phuclong_product', 'besco_pos_base'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/reward_code_view.xml',
        'views/action.xml',
        'views/menu_item.xml',
        #wizard
        'wizards/update_reward_effective_date.xml',
        #report
        'report/report_py3o.xml',
    ],
    'installable': True,
    'auto_install': False,
}
