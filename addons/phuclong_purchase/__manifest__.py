# -*- coding: utf-8 -*-
{
    'name': 'PhucLong Purchase',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'description': """
        This module is used to improve Purchase Management
    """,
    'depends': [
                'besco_purchase',
                'phuclong_product',
                'odoo_report_xlsx',
                'web_m2x_options'
                ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',

        'wizard/wizard_purchase_stock_scheduler_compute_views.xml',
        'wizard/wizard_purchase_multi_product_views.xml',
        'views/purchase_order_views.xml',
        'views/stock_picking_views.xml',
        'views/reason_config_views.xml',
        'views/purchase_type_config_views.xml',
        'views/menu_views.xml',

        #report
        'report/report_purchase_details_views.xml',
        'report/report_xlsx_views.xml',
        'report/purchase_order_template.xml',
        'report/report_py3o.xml',
            ],
    'installable': True,
    'auto_install': False,
}
