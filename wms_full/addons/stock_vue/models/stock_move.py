# -*- coding: utf-8 -*-

from odoo import models, fields, api
from ast import literal_eval


class PickTypeSteps(models.Model):
    _name = 'stock.picking.steps'
    _order = 'sequence asc'

    sequence = fields.Integer('Sequence', required=True)
    stock_pikcking_type_id = fields.Many2one('stock.picking.type', required=True, ondelete='cascade')
    name = fields.Selection(
        string='Step type', selection=[
            ('location_id', 'Scan Source location'),
            ('location_dest_id', 'Scan Destination location'),
            ('product_id', 'Scan Product'),
            ('result_package_id', 'Scan Package'),
        ],
        required=True
    )
    status = fields.Boolean('Status', default=False)
    input = fields.Selection(
        string='Rule',
        selection=[
            ('qty_done', 'Enter quantity'),
        ],
        default=False
    )
    input_type = fields.Selection(
        string='Type of input ',
        selection=[('integer', 'Integer'), ('float', 'Floating point number'), ('bool', 'Boolean'),
                   ('char', 'Character')],
        compute='_compute_input_type'
    )
    can_obj_create = fields.Boolean('Can force create obj',
                                    default=False
                                    )
    can_obj_change = fields.Boolean('Can change obj',
                                    default=False
                                    )

    def _compute_input_type(self):
        for step in self:
            stock_move_obj = self.env['stock.move.line']
            if step.input:
                step.input_type = stock_move_obj._fields[step.input].type
            else:
                step.input_type = False

    def name_get(self):
        result = []
        kay_val_dict = dict(self._fields['name'].selection)
        for step in self:
            result.append((step.id, f'{kay_val_dict.get(step.name)}'))
        return result


class PickingType(models.Model):
    _inherit = 'stock.picking.type'

    description = fields.Char('Description')

    pick_steps = fields.One2many('stock.picking.steps', 'stock_pikcking_type_id')


class Picking(models.Model):
    _inherit = 'stock.picking'

    def picking_serialaser(self, picking):
        from collections import defaultdict
        pick_fields = ['id', 'name', 'picking_type_id', 'partner_id', 'location_id', 'location_dest_id', 'partner_id',
                       'move_lines', 'state']
        repack_fields = ['move_lines']
        pick = {}
        for field in pick_fields:
            val = getattr(picking, field)
            if field == 'move_lines':
                sm = {}
                for move in picking.move_lines:
                    sm.update({
                        move.id: {
                            'id': move.id,
                            'quantity_done': move.quantity_done,
                            'picking_id': move.picking_id.id,
                            'barcode': move.product_id.barcode,
                            'qty_done': move.qty_done,  # how to need
                            'product_qty': move.reserved_availability,
                            'partner_id': {'id': move.partner_id.id, 'name': move.partner_id.name},
                            'steps': move.picking_type_id.pick_steps.sorted(lambda x: x.sequence).read(),
                            'product_id': {
                                'url_image': move.product_id.url_image,
                                'id': move.product_id.id,
                                'default_code': move.product_id.default_code,
                                'name': move.product_id.name,
                                'barcode': move.product_id.barcode
                            },
                            'location_id': {'id': move.location_id.id, 'name': move.location_id.name,
                                            'barcode': move.location_id.barcode},
                            'location_dest_id': {'id': move.location_dest_id.id, 'name': move.location_dest_id.name,
                                                 'barcode': move.location_dest_id.barcode},
                            'result_package_id': {'id': move.result_package_id.id,
                                                  'name': move.result_package_id.name} if move.result_package_id else False,
                            'write_uid': {'id': move.write_uid.id, 'name': move.write_uid.name},
                            'write_date': move.write_date
                        }})
                    sml = {}
                    for line in move.move_line_ids:
                        sml.update({
                            line.id: {
                                'id': line.id,
                                'qty_done': line.qty_done,
                                'product_id': {
                                    'url_image': line.product_id.url_image,
                                    'id': line.product_id.id,
                                    'default_code': line.product_id.default_code,
                                    'name': line.product_id.name,
                                    'barcode': line.product_id.barcode
                                },
                                'location_id': {'id': line.location_id.id, 'name': line.location_id.name,
                                                'barcode': line.location_id.barcode},
                                'location_dest_id': {'id': line.location_dest_id.id, 'name': line.location_dest_id.name,
                                                     'barcode': move.location_dest_id.barcode},
                                'result_package_id': {'id': line.result_package_id.id,
                                                      'name': line.result_package_id.name} if line.result_package_id else False,
                                'write_uid': {'id': line.write_uid.id, 'name': line.write_uid.name},
                                'write_date': line.write_date
                            }})
                    sm[move.id].update({'move_line_ids': sml})
                pick.update({'move_lines': sm})
            elif isinstance(val, models.Model):
                pick.update({
                    field: {
                        'id': val.id,
                        'name': val.name,
                        'barcode': val.barcode if hasattr(val, 'barcode') else False,
                        'warehouse_id': val.warehouse_id if hasattr(val, 'warehouse_id') else False,
                    },

                })
            else:
                pick.update({field: val})
        return pick

    def read_for_controller(self):
        res = {}
        for picking in self:
            res.update({picking.id: self.picking_serialaser(picking)})

        return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    url_image = fields.Char(related='product_id.url_image')

    result_package_id = fields.Many2one(
        'stock.quant.package', 'Destination Package',
        ondelete='restrict', required=False, check_company=True,
        help="If set, the operations are packed into this package")

    product_id = fields.Many2one(
        'product.product', 'Product',
        check_company=True,
        domain="[('type', 'in', ['product', 'consu']),('owner_id', '=', owner_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        index=True, required=True,
        states={'done': [('readonly', True)]})

    qty_done = fields.Float('Quantity Done', compute='_qty_done_compute', digits='How to need')

    def _qty_done_compute(self):
        for move in self:
            move.qty_done = move.product_uom_qty - move.quantity_done


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    barcode = fields.Char('Product barcode', compute='_enter_barcode', inverse='_set_new_barcode')

    def _enter_barcode(self):
        for line in self:
            line.barcode = line.product_id.barcode

    def _set_new_barcode(self):
        for line in self:
            line.product_id.barcode = line.barcode

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('product_uom_id'):
                vals['product_uom_id'] = 1

        mls = super().create(vals_list)
        return mls
