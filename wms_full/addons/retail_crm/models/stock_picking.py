# -*- coding: utf-8 -*-

from odoo import models, fields, api
from ast import literal_eval


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    owner_id = fields.Many2one(
        'res.partner', 'Assign Owner',
        check_company=True,
        required=True,
        store=True,
        help="When validating the transfer, the products will be assigned to this owner.")

    @api.onchange('partner_id', 'owner_id')
    def set_owner_id(self):
        for i in self:
            i.owner_id = i.partner_id

    @api.onchange('show_operations')
    def _onchange_show_operations(self):
        if self.show_operations and self.code != 'incoming':
            self.show_reserved = True

    @api.model
    def create(self, vals):
        res = super(StockPicking, self).create(vals)
        return res

class PickingType(models.Model):
    _inherit = "stock.picking.type"


    def _get_action(self, action_xmlid):
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        if self:
            action['display_name'] = self.display_name

        # default_immediate_tranfer = True
        # if self.env['ir.config_parameter'].sudo().get_param('stock.no_default_immediate_tranfer'):
        #     default_immediate_tranfer = False
        default_immediate_tranfer = False

        context = {
            'search_default_picking_type_id': [self.id],
            'default_picking_type_id': self.id,
            'default_immediate_transfer': default_immediate_tranfer,
            'default_company_id': self.company_id.id,
        }

        action_context = literal_eval(action['context'])
        context = {**action_context, **context}
        action['context'] = context
        return action