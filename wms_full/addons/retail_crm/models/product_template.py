###################################################################################

from odoo import models, fields, _, api, tools
import logging
_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    url_image = fields.Char(string='Image', related='product_variant_id.url_image')

    owner_id = fields.Many2one('res.partner', string='Owner', store=True, compute='_compute_crm_fields')

    @api.depends('product_variant_ids', 'product_variant_ids.owner_id')
    def _compute_crm_fields(self):
        for i in self:
            i.owner_id = i.product_variant_id.owner_id

class ProductProduct(models.Model):
    """"
    Добовим кор счет
    """
    _inherit = 'product.product'

    def _get_default_category_id(self):
        return False

    owner_id = fields.Many2one('res.partner', index=True, required=True)

    url = fields.Char(
        'url'
    )
    url_image = fields.Char(
        'imageUrl'
    )
    external_id = fields.Char(
        'external ID', index=True
    )
    quantity = fields.Integer(
        'quantity'
    )
    _sql_constraints = [('id_uniq', 'UNIQUE (owner_id, external_id)', 'Owner  and ''external_id ''must by unique'), ]

    def init(self):
        constraint_definition = tools.constraint_definition(self._cr, self._table, 'product_product_barcode_uniq')
        if constraint_definition:
            tools.drop_constraint(
                self._cr,
                self._table,
                'product_product_barcode_uniq'
            )