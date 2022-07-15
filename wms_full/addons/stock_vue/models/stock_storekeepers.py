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
    last_sid = fields.Char(
        'last_sid', index=True
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
        pick_steps = self.env['stock.picking.steps']
        res.in_type_id.pick_steps = pick_steps.create([
            {
                'sequence': 0,
                'stock_pikcking_type_id': res.in_type_id.id,
                'name': 'product_id',
                'input': 'qty_done',
                'input_type': 'integer'
            },
            {
                'sequence': 2,
                'stock_pikcking_type_id': res.id,
                'name': 'location_dest_id',
            }
        ])
        res.int_type_id.pick_steps = pick_steps.create([
            {
                'sequence': 0,
                'stock_pikcking_type_id': res.int_type_id.id,
                'name': 'location_id',
            },
            {
                'sequence': 1,
                'stock_pikcking_type_id': res.id,
                'name': 'product_id',
                'input': 'qty_done',
                'input_type': 'integer',
                'can_obj_change': True,
            },
            {
                'sequence': 2,
                'stock_pikcking_type_id': res.id,
                'name': 'location_dest_id',
            }
        ])
        res.out_type_id.pick_steps = pick_steps.create([
            {
                'sequence': 0,
                'stock_pikcking_type_id': res.out_type_id.id,
                'name': 'location_id',
            },
            {
                'sequence': 1,
                'stock_pikcking_type_id': res.id,
                'name': 'product_id',
                'input': 'qty_done',
                'input_type': 'integer'
            },
        ])
        res.pack_type_id.pick_steps = pick_steps.create([
            {
                'sequence': 0,
                'stock_pikcking_type_id': res.pack_type_id.id,
                'name': 'location_id',
            },
            {
                'sequence': 1,
                'stock_pikcking_type_id': res.id,
                'name': 'product_id',
                'input': 'qty_done',
                'input_type': 'integer'
            },
            {
                'sequence': 2,
                'stock_pikcking_type_id': res.id,
                'name': 'result_package_id',
                'can_obj_create': True
            }, ])

        res.pick_type_id.pick_steps = pick_steps.create([
            {
                'sequence': 0,
                'stock_pikcking_type_id': res.pick_type_id.id,
                'name': 'location_id',
            },
            {
                'sequence': 1,
                'stock_pikcking_type_id': res.id,
                'name': 'product_id',
                'input': 'qty_done',
                'input_type': 'integer'
            },
            {
                'sequence': 2,
                'stock_pikcking_type_id': res.id,
                'name': 'result_package_id',
                'can_obj_create': True
            }])
        res.return_type_id.pick_steps = pick_steps.create([
            {
                'sequence': 0,
                'stock_pikcking_type_id': res.return_type_id.id,
                'name': 'product_id',
                'input': 'qty_done',
                'input_type': 'integer'
            },
            {
                'sequence': 1,
                'stock_pikcking_type_id': res.id,
                'name': 'location_dest_id',
                'can_obj_change': True,
            }
        ])


        return res
