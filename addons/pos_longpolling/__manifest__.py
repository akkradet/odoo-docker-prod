# -*- coding: utf-8 -*-
{
    'name': 'POS Longpolling',
    'version': '13.0',
    'category': 'Point of Sale',
    'author': 'BESCO Consulting (vuong.nguyen@besco.vn)',
    'depends': ['point_of_sale','bus'],
    'data': [
        "views/pos_longpolling_template.xml",
    ],
    "qweb": [
        "static/src/xml/pos_longpolling_connection.xml",
    ],
    'installable': True,
    'auto_install': False,
    
    "post_load": None,
    "pre_init_hook": None,
    "post_init_hook": None,
}
