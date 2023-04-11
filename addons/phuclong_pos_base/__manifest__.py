# -*- coding: utf-8 -*-
{
    'name': 'PhucLong POS Base',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'depends': [
        'phuclong_product',
        'fe_pos_loyalty',
        'fe_pos_return_product',
        'fe_pos_print_bill',
        'besco_pos_modify_payment',
        'restrict_logins',
        'web_ir_actions_act_window_message',
        'base'],
    'data': [
        'data/cron.xml',
        'views/templates.xml',
        'security/security.xml',
        'security/ir.model.access.csv',

        'wizard/wizard_modify_payment_view.xml',
        'wizard/wizard_input_session_balance_view.xml',
        'wizard/wizard_clear_user_session_view.xml',

        'views/hr_employee_views.xml',
        'views/pos_sale_type_view.xml',
        'views/pos_session_view.xml',
        'views/pos_order_view.xml',
        'views/product_template_view.xml',
        'views/voucher_coupon_view.xml',
        'views/pos_operation_history_view.xml',
        'views/pos_payment_method.xml',
        'views/pos_payment_views.xml',
        'views/product_cup_update_tool_view.xml',
        'views/res_users_view.xml',
        'views/pos_menu.xml'
    ],
    'qweb': [
        'static/src/qweb/popup.xml',
    ],
    'installable': True,
    'auto_install': False,
}
