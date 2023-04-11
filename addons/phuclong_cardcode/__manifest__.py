# -*- coding: utf-8 -*-
{
    'name': 'PhucLong Cardcode',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'depends': [
#         'besco_base',
        'phuclong_partner',
        'besco_pos_base'
        ],
    'data': [
        #security
        'security/security.xml',
        'security/ir.model.access.csv',
        #wizard
        'wizards/wizard_cardcode_history_info.xml',
        'wizards/wizard_update_cardcode_publish.xml',
        #views
        'views/cardcode_info_views.xml',
        'views/cardcode_publish_views.xml',
        'views/cardcode_history_views.xml',
        'views/menu.xml',
        'views/hr_employee_views.xml',
        'views/res_partner_views.xml',
        'views/pos_session_views.xml',
        #report
        'report/report_py3o.xml',
        'views/templates.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'auto_install': False,
}
