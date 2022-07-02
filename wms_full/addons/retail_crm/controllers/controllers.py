# -*- coding: utf-8 -*-
# from odoo import http


# class Wms(http.Controller):
#     @http.route('/wms/wms', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/wms/wms/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('wms.listing', {
#             'root': '/wms/wms',
#             'objects': http.request.env['wms.wms'].search([]),
#         })

#     @http.route('/wms/wms/objects/<model("wms.wms"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('wms.object', {
#             'object': obj
#         })
