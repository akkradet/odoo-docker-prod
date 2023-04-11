# -*- coding: utf-8 -*-
{
    'name': 'Web Invisible Delete Button',
    'category': 'BESCO Web OCA',
    'author': 'Vuong Nguyen <vuong.nguyen@besco.vn>',
    'description':
        """
         Invisible delete button on form, list view when user doesn't has group "base.group_system"
        """,
    "depends": ['base', 'web'],    
    'data': [
        'views/ir_model_views.xml',
        'views/template.xml',
    ],
    'installable': True,
    'auto_install': False,
    
}
