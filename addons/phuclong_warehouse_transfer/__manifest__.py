# -*- coding: utf-8 -*-
{
    'name': 'PhucLong Warehouse Transfer Management',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'description': """
    """,
    'website': 'https://www.besco.vn',
    'depends': [
        'besco_warehouse_transfer',
        'besco_stock_account',
        'web_ir_actions_act_window_message'
    ],
    'data': [
        'security/security.xml',
        'views/warehouse_transfer_views.xml',
        'views/stock_picking_views.xml',

        'wizards/warehouse_transfer_quantity_history_view.xml',

        'reports/reports.xml',
    ],
    'auto_install': False,
    'application': True,

}
