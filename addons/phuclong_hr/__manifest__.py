# -*- coding: utf-8 -*-
{
    'name': 'PhucLong Employees',
    'category': 'PhucLong',
    'author': 'BESCO Consulting',
    'depends': [
        'besco_base',
        'hr',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml'
    ],
    'installable': True,
    'auto_install': False,
}
