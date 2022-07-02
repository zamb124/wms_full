###################################################################################

from odoo import models, fields, _
import logging
_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    """"
    Добовим кор счет
    """
    _inherit = 'product.template'

    def _get_default_category_id(self):
        return False

    owner_id = fields.Many2one('res.partner', index=True)
    categ_id = fields.Many2one(
        'product.category', 'Product_Category',
        change_default=True, default=_get_default_category_id,
        required=False, help="Select category for the current product")
    article = fields.Char(
        'Article'
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
        'retailCrm ID'
    )
