# -*- coding: utf-8 -*-

from odoo import models, fields, api
from ast import literal_eval


class StockMove(models.Model):
    _inherit = 'stock.move'

    picking_id = fields.Many2one('stock.picking', 'Transfer', index=True, states={'done': [('readonly', True)]},
                                 check_company=True)
    owner_id = fields.Many2one('res.partner', related='picking_id.owner_id')

    product_id = fields.Many2one(
        'product.product', 'Product',
        check_company=True,
        domain="[('type', 'in', ['product', 'consu']),('owner_id', '=', owner_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        index=True, required=True,
        states={'done': [('readonly', True)]})

