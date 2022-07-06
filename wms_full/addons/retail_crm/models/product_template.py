###################################################################################

from odoo import models, fields, _, api
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

    owner_id = fields.Many2one('res.partner', index=True)
    article = fields.Char(
        'Article', index=True
    )
    url = fields.Char(
        'url'
    )
    url_image = fields.Char(
        'imageUrl'
    )
    external_id = fields.Char(
        'external ID'
    )
    quantity = fields.Integer(
        'quantity'
    )
    retailcrm_id = fields.Integer(
        'retailCrm ID', index=True
    )
    _sql_constraints = [('id_uniq', 'UNIQUE (owner_id, external_id)', 'Owner  and ''external_id ''must by unique'), ]

