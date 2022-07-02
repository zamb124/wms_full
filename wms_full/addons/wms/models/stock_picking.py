# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    owner_id = fields.Many2one(
        'res.partner', 'Assign Owner',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        check_company=True,
        required=True,
        help="When validating the transfer, the products will be assigned to this owner.")

    @api.onchange('partner_id')
    def set_owner_id(self):
        for i in self:
            i.owner_id = i.partner_id
