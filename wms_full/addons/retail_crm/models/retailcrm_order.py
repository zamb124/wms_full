# -*- coding: utf-8 -*-

from odoo import models, fields, api


class DeliveryService(models.Model):
    _name = 'retailcrm.delivery'

    company_id = fields.Many2one(
        'res.company', 'Company', required=True, index=True,
        default=lambda self: self.env.company
    )
    name = fields.Char('Name', index=True)
    code = fields.Char('Code', index=True)

    _sql_constraints = [('code', 'UNIQUE (code, company_id)', 'Owner id must by unique'), ]


class DeliveryType(models.Model):
    _name = 'retailcrm.delivery_type'

    company_id = fields.Many2one(
        'res.company', 'Company', index=True, required=True
    )
    code = fields.Char('Phone', index=True, required=1)
    integration_code = fields.Char('integrationCode')

class RetailCrmOrder(models.Model):
    _name = 'retailcrm.order'

    company_id = fields.Many2one(
        'res.company', 'Company', required=True, index=True,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id', store=True, ondelete="restrict"
    )
    status = fields.Char('Status')
    owner_id = fields.Many2one('res.partner', index=True)
    client_id = fields.Many2one(
        'res.partner', required=True, index=True
    )
    retailcrm_id = fields.Integer(
        'retailCrm ID',
        index=True
    )
    external_id = fields.Char(
        'external ID',
        index=True
    )
    status_updated = fields.Datetime(
        'Status updated in RA',
        required=False
    )
    sum = fields.Float('Order sum', required=True)
    total_sum = fields.Float('Total sum', required=True)
    order_type = fields.Char('orderType')
    delivery = fields.Many2one('retailcrm.delivery')
    prepaysum = fields.Float('Payed sum', required=True)
    order_line_ids = fields.One2many('retailcrm.order.line', 'order_id')
    remaind_sum = fields.Float('Remaind', compute='_compute_summs')
    paid = fields.Boolean('Paid', compute='_compute_summs')
    state = fields.Selection([
        ('new', 'New'),
        ('picking', 'Picking'),
        ('packing', 'Packing'),
        ('ready_to_ship', 'Ready to ship'),
        ('shipped', 'Shipped'),
    ], string='Status', readonly=True, copy=False, index=True, default='new')

    def _compute_company_id(self):
        for move in self:
            move.company_id = self.env.company

    def _compute_summs(self):
        for i in self:
            i.remaind_sum = i.prepaysum - i.total_sum
            i.paid = (i.prepaysum - i.total_sum) == 0

    def name_get(self):
        result = []
        for order in self:
            name = f'{order.owner_id.name}: {order.external_id}'
            result.append((order.id, name))
        return result


class RetailCrmOrderLine(models.Model):
    _name = 'retailcrm.order.line'

    order_id = fields.Many2one(
        'retailcrm.order', string='Order line'
    )
    owner_id = fields.Many2one(
        'res.partner',
        related='order_id.owner_id'
    )
    retailcrm_id = fields.Integer(
        'retailCrm ID',
        index=True
    )
    company_id = fields.Many2one(
        related='order_id.company_id', store=True, readonly=True,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        related='order_id.currency_id', string='Currency',
        readonly=True, store=True
    )
    state = fields.Selection(
        related='order_id.state')

    product_id = fields.Many2one(
        'product.product', 'Product',
        domain="[('type', 'in', ['product', 'consu']), ('owner_id','=', owner_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    price = fields.Float('Product price')
    order_qty = fields.Float('Order Qty', help='Quantity in order')
    qty_shipped = fields.Float('Order Qty', compute='_compute_qtys')
    subtotal = fields.Float('Subtotal', compute='_compute_qtys')

    def _compute_qtys(self):
        for i in self:
            i.qty_shipped = 0 # TODO:
            i.subtotal = i.order_qty * i.price
