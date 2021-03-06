# -*- coding: utf-8 -*-
{
    'name': "Monitoring Control for Belenes",

    'summary': """
        Module to add customizatios for monitorins control and change sales process""",

    'description': """
        Module to add customizatios for monitorins control and change sales process
    """,

    'author': "Xmarts, Pablo Osorio Gama",
    'website': "http://xmarts.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '4',

    # any module necessary for this one to work correctly
    'depends': ['base','stock','purchase','sale','contacts','sale_management'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'reports/reports.xml',
    ],
    'installable': True,
    'aplication': True,
    'auto_install': False,
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}