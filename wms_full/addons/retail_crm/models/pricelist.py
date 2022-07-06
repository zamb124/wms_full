# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Pricelist(models.Model):
    _inherit = 'product.pricelist'

    owner_id = fields.Many2one('res.partner', index=True)
    _sql_constraints = [('id_uniq', 'UNIQUE (owner_id)', 'Owner id must by unique'), ]

class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    retailcrm_id = fields.Integer(
        'retailCrm ID', index=True
    )
    external_id = fields.Char(
        'external ID', index=True
    )
    article = fields.Char(
        'Article', index=True
    )
    barcode = fields.Char(
        'Barcode', index=True
    )
    _sql_constraints = [('id_uniq', 'UNIQUE (owner_id, external_id)', 'Owner  and  external_id must by unique'), ]