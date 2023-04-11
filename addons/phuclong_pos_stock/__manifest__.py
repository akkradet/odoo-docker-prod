# -*- coding: utf-8 -*-
{
    'name': 'PhucLong POS Stock',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'depends': ['besco_pos_cron_picking','phuclong_pos_base', 'besco_pos_view_stock', 'phuclong_stock'],
    'data': [
        'data/cron.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/stock_picking_view.xml',
        'views/pos_view.xml',
        'views/config_additional_warehouses_view.xml',
        'views/stock_move_views.xml',
        'views/templates.xml'
    ],
    'qweb': [
        'static/src/qweb/templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}
