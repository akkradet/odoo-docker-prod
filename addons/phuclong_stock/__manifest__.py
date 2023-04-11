# -*- coding: utf-8 -*-
{
    'name': 'PhucLong Stock',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'depends': [
        'besco_stock_account',
        'besco_stock_report',
        'phuclong_product',
        'phuclong_purchase',
        ],
    'data': [
        #data
        'data/ir_cron_views.xml',
        'data/res_calendar_weekday_data.xml',
        'data/res_calendar_daymonth_data.xml',
        #security
        'security/security.xml',
        'security/ir.model.access.csv',
        #wizard
        'wizard/stock_scheduler_compute_views.xml',
        'wizard/wizard_report_move_line_view.xml',
        'wizard/stock_location_change_view.xml',
        'wizard/wizard_stock_balance_product_view.xml',
        'wizard/stock_backorder_confirmation_view.xml',
        'wizard/stock_immediate_transfer_view.xml',
        'wizard/stock_overprocessed_transfer_views.xml',
        #report
        'reports/reports.xml',
        #views
        'views/stock_template.xml',
        'views/stock_inventory_views.xml',
        'views/stock_quant_views.xml',
        'views/stock_region_views.xml',
        'views/stock_warehouse_views.xml',
        'views/stock_warehouse_orderpoint_views.xml',
        'views/stock_move_views.xml',
        'views/stock_picking_view.xml',
        'views/stock_picking_type_views.xml',
        'views/stock_balance_sheet_view.xml',
        'views/purchase_type_config_views.xml',
        'views/stock_inventory_view.xml',
        'views/stock_current_inventory_view.xml',
        'views/stock_menu.xml',
    ],
    'qweb': [
        'static/src/xml/inventory_report.xml',
    ],
    'installable': True,
    'auto_install': False,
}
