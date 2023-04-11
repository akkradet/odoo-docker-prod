# -*- coding: utf-8 -*-
{
    'name': 'PhucLong Mobile Backend',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'depends': [
        'besco_base',
        'phuclong_partner',
        'phuclong_product',
        'phuclong_pos_theme',
        'phuclong_restful_api',
        'phuclong_voucher_coupon',
        'mass_mailing',
        'besco_loyalty',
        'besco_pos_base'
    ],
    'data': [
        # security
        'security/security.xml',
        'security/ir.model.access.csv',
        # data
        'data/data.xml',
        # views
        'views/mobile_homepage_slide_views.xml',
        'views/showcase_views.xml',
        'views/shipping_fee_views.xml',
        'views/res_store_views.xml',
        'views/config_qanda_views.xml',
        'views/config_issue_views.xml',
        'views/request_update_card_views.xml',
        'views/policy_terms_views.xml',
        'views/configuration_login_views.xml',
        'views/res_partner_views.xml',
        'views/res_users_views.xml',
        'views/loyalty_level_views.xml',
        'views/loyalty_reward_views.xml',
        'views/product_category_mobile_views.xml',
        'views/product_template_views.xml',
        'views/api_history_views.xml',
        'views/pos_sale_type_views.xml',
        'views/partner_wallet_views.xml',
        'views/pos_order_views.xml',
        'views/product_material_views.xml',
        'views/sale_promo_combo_views.xml',
        'views/res_config_settings_views.xml',
        'views/coupon_app_views.xml',
        'views/crm_voucher_lock_views.xml',
        'views/crm_voucher_publish_views.xml',
        'views/crm_voucher_info_views.xml',
        'views/menu_views.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'auto_install': False,
}