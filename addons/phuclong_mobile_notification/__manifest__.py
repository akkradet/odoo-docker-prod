# -*- coding: utf-8 -*-
{
    'name': 'PhucLong Mobile Notification',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'depends': [
        'phuclong_mobile_backend',
        'web_boolean_button'
    ],
    'data': [
        'data/data.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/mobile_notification_views.xml',
        'views/mobile_notification_auto_views.xml',
        'views/menu.xml'
    ],
    'external_dependencies': {
        'python': [
            'firebase_admin',
        ],
    },
    'installable': True,
    'auto_install': False,
}
