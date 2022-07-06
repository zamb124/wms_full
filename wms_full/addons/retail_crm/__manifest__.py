# -*- coding: utf-8 -*-
{
    'name': "retail_crm",

    'summary': """
        Интеграция с RetailCrm""",

    'description': """
        Модуль позволяет интегрирываться с retail_crm 
    """,

    'author': "shvedvik",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'stock',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'product',
        'stock',
        'ec_web_widget_image_url',
        'wms'
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/order.xml',
        'views/menus.xml',
        'views/product.xml',
        'data/cron_schelued_actions.xml',

        #'views/stock_picking_form.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
