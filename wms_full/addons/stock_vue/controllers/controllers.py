# Copyright (c) 2015-2016 ACSONE SA/NV (<http://acsone.eu>)
# Copyright 2013-2016 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)
import json
import logging
from odoo import _, http, fields, exceptions
from odoo.http import request

_logger = logging.getLogger(__name__)

class MobileApp(http.Controller):
    @http.route('/app/', type='http', auth='user')
    def pos_web(self, **kwargs):
        response = request.render('stock_vue.stock_app')
        response.headers['Cache-Control'] = 'no-store'
        return response

    def authorization(self, req):
        storekeeper = req.env['stock.storekeeper']
        token = request.httprequest.headers.environ.get('HTTP_AUTHORIZATION').split('\t')[1]
        data = json.loads(request.httprequest.data)
        storekeeper = storekeeper.sudo().search([('last_sid', '=', token)])
        return storekeeper.user_id, data, storekeeper.last_sid

    def set_user(self, request, token, sid):
        user_obj = request.env['stock.storekeeper']
        user = user_obj.sudo().search([('user_barcode', '=', token)])
        user.sudo().write({'last_sid': sid})
        return user.user_id

    @http.route("/app/v1/login", type="json", auth="none", csrf=False, methods=['GET', 'POST', 'OPTIONS'], cors='*')
    def login(self, **kwargs):
        from uuid import uuid4
        sid = uuid4().__str__()
        data = json.loads(request.httprequest.data)
        user = self.set_user(request, data['qr'], sid)
        return {
            'token': sid,
            'user_data': user.name,
            'store_title': user.name,

        }

    @http.route("/app/v1/main", type="json", auth="none", csrf=False, methods=['GET', 'POST', 'OPTIONS'], cors='*')
    def get_piking_types(self, **kwargs):
        user, data, session_id = self.authorization(request)
        picking_types_objs = request.env['stock.picking.type'].sudo().search([
            ('company_id', '=', user.company_id.id), ('active', '=', True)
        ])
        picking_types = [
            {
                'name': i.name,
                'id': i.id,
                'description': i.description,
                'count_picking': i.count_picking,
                'count_picking_draft': i.count_picking_draft,
                'count_picking_late': i.count_picking_late,
                'count_picking_ready': i.count_picking_ready,
                'count_picking_waiting': i.count_picking_waiting
            }
            for i in picking_types_objs
        ]

        return {
            'picking_types': picking_types
        }

    @http.route("/app/v1/pickings", type="json", auth="none", csrf=False, methods=['GET', 'POST', 'OPTIONS'], cors='*')
    def pickings(self, **kwargs):
        picking_fields = ['name', 'partner_id', 'location_dest_id', 'scheduled_date', 'state']
        user, data, session_id = self.authorization(request)
        pt = data['picking_type']
        picking_type_obj = request.env['stock.picking.type']
        picking_type = picking_type_obj.sudo().search_read([('id', '=', int(pt))], ['name', 'warehouse_id', 'description'])[0]
        picking_obj = request.env['stock.picking']
        pickings = picking_obj.sudo().search_read([('picking_type_id', '=', int(pt)), ('state', '=', 'assigned')], picking_fields)
        return {
            'pickings': pickings,
            'picking_type': picking_type
        }

    @http.route("/app/v1/picking", type="json", auth="none", csrf=False, methods=['GET', 'POST', 'OPTIONS'], cors='*')
    def picking(self, **kwargs):
        user, data , session_id = self.authorization(request)
        pt = data['picking_id']
        picking_obj = request.env['stock.picking']
        picking = picking_obj.with_user(user).search([('id', '=', int(pt))])

        return {
            'stock_moves': picking.move_lines.read(),
            'picking': picking[0].read()[0],
            'show_entire_packs': picking.picking_type_id.show_entire_packs # Если тип задания подразумевает обязательную упаковку
        }

    @http.route("/app/v1/picking_force_complete", type="json", auth="none", csrf=False, methods=['GET', 'POST', 'OPTIONS'], cors='*')
    def picking_force_complete(self, **kwargs):
        user, data, session_id = self.authorization(request)
        picking = request.env['stock.picking'].sudo().search([('id', '=', data['picking_id'])])
        picking.env.context = picking.with_context(
            skip_backorder=True,
            skip_immediate=True,
            cancel_backorder=True,
            picking_ids_not_to_backorder=[picking.id,]
        ).env.context
        a = picking.with_user(user).with_context(cancel_backorder=True).mapped('move_lines.move_line_ids')._action_done()
        b = picking.move_lines.with_user(user).write({'state': 'done', 'date': fields.Datetime.now()})
        if b:
            return {
                'status': b,
            }
        else:
            UserWarning('dadasdasdas')

    @http.route("/app/v1/scan_product_with_picking", type="json", auth="none", csrf=False,
                methods=['GET', 'POST', 'OPTIONS'], cors='*')
    def scan_product_with_picking(self, **kwargs):
        user, data, session_id = self.authorization(request)
        picking_id = data['payload']['picking']
        picking = request.env['stock.picking'].sudo().search([
            ('id', '=', picking_id)
        ])
        barcode = data['payload']['barcode']
        offer_obj = request.env['product.pricelist.item']
        move_obj = request.env['stock.move']
        offer = offer_obj.sudo().search([('barcode', '=', barcode)])
        if offer:
            stock_move = move_obj.sudo().search([
                ('picking_id', '=', picking_id), ('product_id', '=', offer.product_id.id)
            ])
            return {
                'stock_move': {
                    'id': stock_move.id
                }}
        # TODO: Если нет?

    @http.route("/app/v1/get_stock_move", type="json", auth="none", csrf=False, methods=['GET', 'POST', 'OPTIONS'],
                cors='*')
    def get_stock_move(self, **kwargs):
        user, data, session_id = self.authorization(request)
        stock_mode_id = data['stock_move_id']
        stock_move = request.env['stock.move'].sudo().search([('id', '=', stock_mode_id)])
        return {
            'stock_move': {
                'id': stock_move.id,
                'display_name': stock_move.display_name,
                'picking_id': stock_move.picking_id.id,
                'quantity_done': stock_move.quantity_done,
                'barcode': stock_move.product_id.barcode,
                'qty_done': stock_move.qty_done, # how to need
                'product_qty': stock_move.reserved_availability,
                'move_line_ids': stock_move.move_line_ids.filtered(lambda x: x.qty_done > 0).read(),
                'partner_id': {
                    'id': stock_move.picking_id.owner_id.id,
                    'name': stock_move.picking_id.owner_id.name,
                },
                'product_id': stock_move.product_id.with_user(user).read()[0] if stock_move.product_id else False,
                'location_id': stock_move.location_id.read()[0] if stock_move.location_id else False,
                'location_dest_id': stock_move.location_dest_id.read()[0] if stock_move.location_dest_id else False,
                'result_package_id': stock_move.result_package_id.read()[0] if stock_move.result_package_id else False,
                'steps': stock_move.picking_type_id.pick_steps.sorted(lambda x: x.sequence).read()
            }
        }

    @http.route("/app/v1/get_or_create_object", type="json", auth="none", csrf=False,
                methods=['GET', 'POST', 'OPTIONS'],
                cors='*')
    def get_or_create_object(self, **kwargs):
        """
        Берем упаковку или создаем новую
        """
        created = False
        user, data, session_id = self.authorization(request)
        scan_value, object_name, can_obj_create = data['scan_value'], data['object_name'], data['can_obj_create']
        move_line_obj = request.env['stock.move.line']
        comodel = move_line_obj._fields[object_name].comodel_name
        object = request.env[comodel].with_user(user).search([('barcode', '=', scan_value)])
        if object:
            object.ensure_one()
        if not object:
            if can_obj_create:
                object = object.with_user(user).create({
                    'name': scan_value,
                    'barcode': scan_value,
                    'company_id': user.company_id.id,
                })
            else:
                raise exceptions.UserError('Can\'t create rules')
            created = True
        return {
            object_name: object.read()[0],
            'created': created
        }

    @http.route("/app/v1/stock_move_line_done", type="json", auth="none", csrf=False, methods=['GET', 'POST', 'OPTIONS'],
                cors='*')
    def stock_move_line_done(self, **kwargs):
        user, data, session_id = self.authorization(request)
        sml_obj = request.env['stock.move.line']
        sm = request.env['stock.move'].sudo().search([('id', '=', data['stock_move_id'])])
        line_vals = {
            'move_id': sm.id,
            'picking_id': sm.picking_id.id,
            'product_id': sm.product_id.id,
            'product_uom_qty': 0,  # bypass reservation here
            'product_uom_id': sm.product_id.uom_id.id,
            'qty_done': data['qty_done'],
            'location_id': sm.location_id.id,
            'location_dest_id': data.get('location_dest_id'),
            'owner_id': sm.owner_id.id,
            'company_id': sm.company_id.id,
            'result_package_id': data.get('result_package_id')
        }
        sml_obj.sudo().create(
            line_vals
        )
        return {
            'status': True
        }

    @http.route("/app/v1/stock_poll", type="json", auth="none", csrf=False,
                methods=['GET', 'POST', 'OPTIONS'],
                cors='*')
    def stock_poll(self, **kwargs):
        user, data, session_uid = self.authorization(request)
        sml_obj = request.env['stock.move.line']
        orders = request.env['stock.bus'].with_user(user).get_orders_by_user(session_uid)
        result = {}
        return {
            'orders': orders.with_user(user).read_for_controller()
        }
