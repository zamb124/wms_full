# Copyright 2017 - 2018 Modoolar <info@modoolar.com>
# License LGPLv3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.en.html).
{
    "name": "EC Web Image URL",
    "summary": "This module provides web widget for displaying image from URL",
    "images": ['images/main.png'],
    "category": "Web",
    "version": "14.0.1.0.1",
    "license": "LGPL-3",
    "author": "Modoolar, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/web/",
    "depends": ["web"],
    "data": [
        "views/ec_web_widget_image_url.xml",
    ],
    "qweb": ["static/src/xml/*.xml"],
    "installable": True,
}
