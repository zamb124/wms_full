# -*- coding: utf-8 -*-

from odoo import models, fields, api



class ProductCategory(models.Model):
    """"
    Добовим кор счет
    """
    _inherit = 'product.category'
    external_id = fields.Char(
        'shop external ID'
    )
    owner_id = fields.Many2one('res.partner', index=True)
    active = fields.Boolean('Active', default=True)

