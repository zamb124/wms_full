# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from functools import partial
from itertools import groupby
import json

from markupsafe import escape, Markup
from pytz import timezone, UTC
from werkzeug.urls import url_encode

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang, format_amount


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Purchase Order"
    _order = 'priority desc, id desc'

    READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    name = fields.Char('Order Reference', required=True, index=True, copy=False, default='New')
    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'Urgent')], 'Priority', default='0', index=True)
    origin = fields.Char('Source Document', copy=False,
                         help="Reference of the document that generated this purchase order "
                              "request (e.g. a sales order)")
    date_calendar_start = fields.Date('date_start')
    date_order = fields.Datetime('Order Deadline', required=True, states=READONLY_STATES, index=True, copy=False,
                                 default=fields.Datetime.now,
                                 help="Depicts the date within which the Quotation should be confirmed and converted into a purchase order.")
    date_approve = fields.Datetime('Confirmation Date', readonly=1, index=True, copy=False)
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True, states=READONLY_STATES,
                                 change_default=True, tracking=True,
                                 domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                 help="You can find a vendor by its Name, TIN, Email or Internal Reference.")
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, states=READONLY_STATES,
                                  default=lambda self: self.env.company.currency_id.id)
    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Acceptance Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    order_line = fields.One2many('purchase.order.line', 'order_id', string='Order Lines',
                                 states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True)
    notes = fields.Html('Terms and Conditions')
    user_id = fields.Many2one(
        'res.users', string='Purchase Representative', index=True, tracking=True,
        default=lambda self: self.env.user, check_company=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, states=READONLY_STATES,
                                 default=lambda self: self.env.company.id)
    picking_ids = fields.Many2many('stock.picking', 'purchase_order_id', string='Receptions', copy=False)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True, default=1)

    def _compute_access_url(self):
        super(PurchaseOrder, self)._compute_access_url()
        for order in self:
            order.access_url = '/my/purchase/%s' % (order.id)

    def button_start_picking(self):
        picking_obj = self.env['stock.picking']
        move_obj = self.env['stock.move']
        for order in self:
            if order.picking_ids:
                raise UserError('Picking already started')
            picking = picking_obj.create({
                'owner_id': order.partner_id.id,
                'move_type': 'direct',
                'picking_type_id': order.warehouse_id.in_type_id.id,
                'partner_id': order.partner_id.id,
                'company_id': order.company_id.id,
                'purchase_order_id': order.id,
                'location_id': self.env.ref('stock.stock_location_suppliers').id,
                'location_dest_id': order.warehouse_id.in_type_id.default_location_dest_id.id,
                # 'warehouse_id': order.warehouse_id.id
            })
            stock_moves = []
            for line in order.order_line:
                stock_moves.append({
                    'picking_id': picking.id,
                    'partner_id' : picking.partner_id.id,
                    'owner_id': picking.owner_id.id,
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_qty,
                    'product_uom': line.product_id.uom_id.id,
                    'location_id': self.env.ref('stock.stock_location_suppliers').id,
                    'purchase_line_id': line.id,
                    'location_dest_id': order.warehouse_id.in_type_id.default_location_dest_id.id,
                })
            move_obj.create(stock_moves)
            order.state = 'purchase'
            order.picking_ids = picking
            picking.action_confirm()

class PurchaseOrderLine(models.Model):
    _name = 'purchase.order.line'
    _description = 'Purchase Order Line'
    _order = 'order_id, sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    product_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True)
    date_planned = fields.Datetime(string='Delivery Date', index=True,
                                   help="Delivery date expected from vendor. This date respectively defaults to vendor pricelist lead time then today's date.")
    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)],
                                 change_default=True)
    product_type = fields.Selection(related='product_id.detailed_type', readonly=True)
    price_unit = fields.Float(string='Unit Price', digits='Product Price')

    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)

    order_id = fields.Many2one('purchase.order', string='Order Reference', index=True, required=True,
                               ondelete='cascade')
    company_id = fields.Many2one('res.company', related='order_id.company_id', string='Company', store=True,
                                 readonly=True)
    state = fields.Selection(related='order_id.state', store=True)
    partner_id = fields.Many2one('res.partner', related='order_id.partner_id', string='Partner', readonly=True,
                                 store=True)
    currency_id = fields.Many2one(related='order_id.currency_id', store=True, string='Currency', readonly=True)
    date_order = fields.Datetime(related='order_id.date_order', string='Order Date', readonly=True)
    move_ids = fields.One2many('stock.move', 'purchase_line_id', string='Reservation', readonly=True, copy=False)
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")

    def _compute_amount(self):
        for i in self:
            i.price_subtotal = i.price_total = 0.0


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    purchase_order_id = fields.Many2one('purchase.order', 'Purchase Order', ondelete='set null', index=True, readonly=True)


class StockMove(models.Model):
    _inherit = 'stock.move'

    purchase_line_id = fields.Many2one('purchase.order.line', 'Purchase Order Line', ondelete='set null', index=True, readonly=True)
