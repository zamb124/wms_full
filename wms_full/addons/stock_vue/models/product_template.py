###################################################################################

from odoo import models, fields, _, api
import logging
_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    url_image = fields.Char(string='Image', related='product_variant_id.url_image')

class ProductProduct(models.Model):
    """"
    Добовим кор счет
    """
    _inherit = 'product.product'

    article = fields.Char(
        'Article', index=True
    )
    url_image = fields.Char(
        'imageUrl'
    )

