# Copyright (c) 2015-2016 ACSONE SA/NV (<http://acsone.eu>)
# Copyright 2013-2016 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)
import json
import logging
from odoo import _, http, fields, exceptions, models
import datetime
from odoo.http import request
from odoo.addons.bus.controllers.main import BusController

_logger = logging.getLogger(__name__)


class StockBus(models.Model):
    _name = 'stock.bus'

    session_uid = fields.Char('Session uid', required=True, index=True)
    user_id = fields.Many2one('res.users', required=True)
    last_update = fields.Datetime('last_update', required=True, index=True)

    def get_orders_by_user(self, session_uid=False):
        bus = self.search([('session_uid', '=', session_uid)])
        if not bus:
            orders = self.env['stock.picking'].search([
                ('state', '=', 'assigned')
            ])
            self.create({
                'session_uid': session_uid,
                'user_id': self.env.user.id,
                'last_update': datetime.datetime.utcnow()
            })
        else:
            bus = self.search([('session_uid', '=', session_uid)])
            orders = self.env['stock.picking'].search(
                [('write_date', '>', bus.last_update)]
            )
            bus.last_update = datetime.datetime.utcnow()
        return  orders