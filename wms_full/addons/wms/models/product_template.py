
from odoo import models, fields, _
import logging
_logger = logging.getLogger(__name__)


class Product(models.Model):
    _inherit = "product.product"

    owner_id = fields.Many2one('res.partner', required=True)
