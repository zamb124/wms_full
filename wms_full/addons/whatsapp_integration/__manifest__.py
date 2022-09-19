# -*- coding: utf-8 -*-
{
    'name': 'WhatsApp Odoo Integration',
    'version': '15.0.2.1.1',
    'category': 'Tools',
    'author': 'InTechual Solutions',
    'license': 'OPL-1',
    'summary': 'WhatsApp Integration with Odoo',
    'description': """
This module can be used to send messages to WhatsApp
----------------------------------------------------
Send Messages via WhatsApp
Core module for WhatsApp Odoo Integration
""",
    'depends': ['base', 'base_setup', 'web', 'mail'],
    'data': [
        'data/whatsapp_cron.xml',
        'data/wp_sequence.xml',
        'security/ir.model.access.csv',
        'wizard/send_wp_msg_views.xml',
        'wizard/whatsapp_template_preview_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'views/whatsapp_template_views.xml',
        'views/ir_actions_views.xml',
        'security/whatsapp_security.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'whatsapp_integration/static/src/js/many2many_tags_mobile.js',
            'whatsapp_integration/static/src/js/refresh_qr_code.js',
        ],
        'point_of_sale.assets': [
            # 'whatsapp_integration/static/src/js/ReceiptScreen/ReceiptScreen.js',
        ],
        'web.assets_qweb': [
            'whatsapp_integration/static/src/xml/mobile_widget.xml',
            # 'whatsapp_integration/static/src/xml/pos_whatsapp.xml',
        ],
    },
    'external_dependencies': {'python': ['phonenumbers', 'selenium']},
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'application': True,
    'sequence': 1,
    'auto_install': False,
    'currency': 'EUR',
    'price': 25,

}
