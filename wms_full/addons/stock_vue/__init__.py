from . import models, controllers

from odoo import api, SUPERUSER_ID


def _create_warehouse_data(cr, registry):
    """ Create steps for each warehouse
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    warehouse_ids = env['stock.warehouse'].search([])
    for wh in warehouse_ids:
        wh._create_steps_data()