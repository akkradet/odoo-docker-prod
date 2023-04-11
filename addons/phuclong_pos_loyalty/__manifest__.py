# -*- coding: utf-8 -*-
{
    'name': 'PhucLong POS Loyalty',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'depends': [
        'besco_pos_base',
        'phuclong_pos_base',
        'phuclong_cardcode',
        'phuclong_partner',
        'phuclong_pricelist',
        'web_ir_actions_act_window_message'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/templates.xml',
        'views/hr_employee_view.xml',
        'views/loyalty_view.xml',
        'views/menu_view.xml',

        "report/report_customer_views.xml",
        "report/report_py3o.xml",
        "report/report_loyalty_gift_view.xml"
    ],
    'installable': True,
    'auto_install': False,
}
