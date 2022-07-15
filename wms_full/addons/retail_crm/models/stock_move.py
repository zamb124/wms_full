# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
from ast import literal_eval


class StockMove(models.Model):
    _inherit = 'stock.move'

    picking_id = fields.Many2one('stock.picking', 'Transfer', index=True, states={'done': [('readonly', True)]},
                                 check_company=True)
    owner_id = fields.Many2one('res.partner', related='picking_id.owner_id')
    url_image = fields.Char(related='product_id.url_image')

    product_id = fields.Many2one(
        'product.product', 'Product',
        check_company=True,
        domain="[('type', 'in', ['product', 'consu']),('owner_id', '=', owner_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        index=True, required=True,
        states={'done': [('readonly', True)]})

    def _get_new_picking_values(self):
        """ return create values for new picking that will be linked with group
        of moves in self.
        """
        origins = self.filtered(lambda m: m.origin).mapped('origin')
        origins = list(dict.fromkeys(origins))  # create a list of unique items
        # Will display source document if any, when multiple different origins
        # are found display a maximum of 5
        if len(origins) == 0:
            origin = False
        else:
            origin = ','.join(origins[:5])
            if len(origins) > 5:
                origin += "..."
        partners = self.mapped('partner_id')
        partner = len(partners) == 1 and partners.id or False
        return {
            'origin': origin,
            'company_id': self.mapped('company_id').id,
            'user_id': False,
            'move_type': self.mapped('group_id').move_type or 'direct',
            'partner_id': partner,
            'owner_id': partner,
            'picking_type_id': self.mapped('picking_type_id').id,
            'location_id': self.mapped('location_id').id,
            'location_dest_id': self.mapped('location_dest_id').id,
        }

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('product_uom_id'):
                vals['product_uom_id'] = 1

        mls = super().create(vals_list)
        return mls

    def _action_done(self):
        res = super()._action_done()
        return res

class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.model_create_multi
    def create(self, vals_list):
        sq = super().create(vals_list)
        for i in sq:
            if not i.owner_id:
                raise exceptions.UserError('Stock quant Missing partner')
        return sq

    def _action_done(self):
        res = super()._action_done()
        return res

# -*- coding: utf-8 -*-
