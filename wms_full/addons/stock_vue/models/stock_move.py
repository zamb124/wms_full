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
        selection=[('integer', 'Integer'), ('float', 'Floating point number'), ('bool', 'Boolean'), ('char', 'Character')],
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