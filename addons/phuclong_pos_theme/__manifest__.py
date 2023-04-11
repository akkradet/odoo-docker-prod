# -*- coding: utf-8 -*-
{
    'name': 'PhucLong POS Theme',
    'category': 'PhucLong',
    'author': 'BESCO Consulting (chris.vang<thai.vang@besco.vn>)',
    'depends': [
        'phuclong_pos_config',
        'phuclong_promotion',
        'phuclong_pos_loyalty',
        'phuclong_pos_reward_code',
        'phuclong_pos_surcharge',
        'web_notify',
        'pos_longpolling',
    ],
    'data': [
        # security
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/cron.xml',
        # report
        'reports/reports.xml',
        'views/templates.xml',
        'views/pos_order.xml',
        'views/pos_session.xml',
        'views/res_users_view.xml',
        # report
        'reports/reports.xml',
        # wizard
        # 'wizards/reports.xml',
        'wizards/pos_cashier_scanner.xml',
        'wizards/login_scanner_wizard_view.xml',
        'views/pos_order_duplicate_log_view.xml',
        'views/pos_report_queue_views.xml',
        'views/menu.xml',
    ],
    'qweb': [
        'static/src/qweb/templates.xml',
        'static/src/qweb/bill.xml',
        'static/src/qweb/bill_pos_backend.xml'
    ],
    'installable': True,
    'auto_install': False,
}
