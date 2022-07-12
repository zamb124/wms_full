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

from odoo import models, fields, api
from ast import literal_eval


class StockStorekeeper(models.Model):
    _name = 'stock.storekeeper'

    user_id = fields.Many2one(
        'res.users', 'Related user', required=True
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse', 'Warehouse', required=True
    )
    user_barcode = fields.Char(
        'User Barcode', index=True
    )
    user_role = fields.Selection(
        [('executer', 'Executer'), ('manager', 'Store Manager')],
        'User role', required=True, default='executer'
    )

    def _init_stock_vue_data(self):
        records = self.search([])
        if not records:
            storekeeper_created = self.create({
                'user_id': self.env.ref('base.user_admin').id,
                'user_barcode': '1111',
                'user_role': 'executer',
                'warehouse_id': self.env.ref('stock.warehouse0').id
            })

    def open_ui(self):
        """Open the pos interface with config_id as an extra argument.

        In vanilla PoS each user can only have one active session, therefore it was not needed to pass the config_id
        on opening a session. It is also possible to login to sessions created by other users.

        :returns: dict
        """
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # check all constraints, raises if any is not met
        return {
            'type': 'ir.actions.act_url',
            'url': f'/app/?url={base_url}',
            'target': 'self',
        }


class Warehouse(models.Model):
    _inherit = 'stock.warehouse'

    @api.model
    def create(self, vals):
        res = super().create(vals)
        res.reception_steps = 'two_steps'
        res.delivery_steps = 'pick_pack_ship'
        return res
