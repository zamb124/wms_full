# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from collections import OrderedDict
from datetime import datetime

from odoo import http
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request, Response
from odoo.tools import image_process
from odoo.tools.translate import _
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager


class CustomerPortal(portal.CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        PurchaseOrder = request.env['purchase.order']
        if 'rfq_count' in counters:
            values['rfq_count'] = PurchaseOrder.search_count([
                ('state', 'in', ['sent', 'draft'])
            ]) if PurchaseOrder.check_access_rights('read', raise_exception=False) else 0
        if 'purchase_count' in counters:
            values['purchase_count'] = PurchaseOrder.search_count([
                ('state', 'in', ['purchase', 'done', 'cancel'])
            ]) if PurchaseOrder.check_access_rights('read', raise_exception=False) else 0
        return values

    def _render_portal(self, template, page, date_begin, date_end, sortby, filterby, domain, searchbar_filters, default_filter, url, history, page_name, key):
        values = self._prepare_portal_layout_values()
        PurchaseOrder = request.env['purchase.order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
            'amount_total': {'label': _('Total'), 'order': 'amount_total desc, id desc'},
        }
        # default sort
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if searchbar_filters:
            # default filter
            if not filterby:
                filterby = default_filter
            domain += searchbar_filters[filterby]['domain']

        # count for pager
        count = PurchaseOrder.search_count(domain)

        # make pager
        pager = portal_pager(
            url=url,
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=count,
            page=page,
            step=self._items_per_page
        )

        # search the purchase orders to display, according to the pager data
        orders = PurchaseOrder.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        request.session[history] = orders.ids[:100]

        values.update({
            'date': date_begin,
            key: orders,
            'page_name': page_name,
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'default_url': url,
        })
        return request.render(template, values)

    def _purchase_order_get_page_view_values(self, order, access_token, **kwargs):
        #
        def resize_to_48(b64source):
            if not b64source:
                b64source = base64.b64encode(request.env['ir.http']._placeholder())
            return image_process(b64source, size=(48, 48))

        values = {
            'order': order,
            'resize_to_48': resize_to_48,
            'report_type': 'html',
        }
        if order.state in ('sent'):
            history = 'my_rfqs_history'
        else:
            history = 'my_purchases_history'
        return self._get_page_view_values(order, access_token, values, history, False, **kwargs)

    @http.route(['/my/rfq', '/my/rfq/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_requests_for_quotation(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        return self._render_portal(
            "retail_crm.portal_my_purchase_rfqs",
            page, date_begin, date_end, sortby, filterby,
            [('state', 'in', ['sent', 'draft'])],
            {},
            None,
            "/my/rfq",
            'my_rfqs_history',
            'rfq',
            'rfqs'
        )

    @http.route(['/my/purchase', '/my/purchase/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_purchase_orders(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        return self._render_portal(
            "retail_crm.portal_my_purchase_orders",
            page, date_begin, date_end, sortby, filterby,
            [],
            {
                'all': {'label': _('All'), 'domain': [('state', 'in', ['purchase', 'done', 'cancel'])]},
                'purchase': {'label': _('Purchase Order'), 'domain': [('state', '=', 'purchase')]},
                'cancel': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancel')]},
                'done': {'label': _('Locked'), 'domain': [('state', '=', 'done')]},
            },
            'all',
            "/my/purchase",
            'my_purchases_history',
            'purchase',
            'orders'
        )

    @http.route(['/my/purchase/<int:order_id>'], type='http', auth="public", website=True)
    def portal_my_purchase_order(self, order_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        report_type = kw.get('report_type')
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=order_sudo, report_type=report_type, report_ref='retail_crm.action_report_purchase_order', download=kw.get('download'))

        confirm_type = kw.get('confirm')
        if confirm_type == 'reminder':
            order_sudo.confirm_reminder_mail(kw.get('confirmed_date'))
        if confirm_type == 'reception':
            order_sudo._confirm_reception_mail()

        values = self._purchase_order_get_page_view_values(order_sudo, access_token, **kw)
        update_date = kw.get('update')
        if order_sudo.company_id:
            values['res_company'] = order_sudo.company_id
        if update_date == 'True':
            return request.render("retail_crm.portal_my_purchase_order_update_date", values)
        return request.render("retail_crm.portal_my_purchase_order", values)

    @http.route(['/my/purchase/<int:order_id>/update'], type='http', methods=['POST'], auth="public", website=True)
    def portal_my_purchase_order_update_dates(self, order_id=None, access_token=None, **kw):
        """User update scheduled date on purchase order line.
        """
        try:
            order_sudo = self._document_check_access('retail_crm.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        updated_dates = []
        for id_str, date_str in kw.items():
            try:
                line_id = int(id_str)
            except ValueError:
                return request.redirect(order_sudo.get_portal_url())
            line = order_sudo.order_line.filtered(lambda l: l.id == line_id)
            if not line:
                return request.redirect(order_sudo.get_portal_url())

            try:
                updated_date = line._convert_to_middle_of_day(datetime.strptime(date_str, '%Y-%m-%d'))
            except ValueError:
                continue

            updated_dates.append((line, updated_date))

        if updated_dates:
            order_sudo._update_date_planned_for_lines(updated_dates)
        return Response(status=204)


    @http.route('/my/new_acceptation', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def create_new_acceptance(self, **post):
        user_obj = request.env['res.users']
        values = self._prepare_portal_layout_values()
        values['get_error'] = get_error
        values['allow_api_keys'] = bool(request.env['ir.config_parameter'].sudo().get_param('portal.allow_api_keys'))
        import xlrd
        user = user_obj.search([('id', '=', request.uid)])
        warehouses = request.env['stock.warehouse'].sudo().search([])
        partner_id = user.partner_id
        values.update({
            'page_name': 'new_acceptance',
            'shops': partner_id.child_ids,
            'partner_id': partner_id,
            'error': {},
            'error_message': [],
            'warehouses': warehouses
        })
        if request.httprequest.method == 'POST':
            shop_id = post.get('shop_id')
            warh_id = post.get('warh_id')
            date = post.get('date')
            file = post.get('file')
            workbook = xlrd.open_workbook(
                file_contents=file.read())
            sheet = workbook.sheet_by_index(0)
            result = []
            row_order = {'name': 0, 'sku': 1, 'barcode': 2, 'quantity': 3}
            barcodes = []
            for row_num, row in enumerate(sheet.get_rows()):
                if row_num == 0:
                    for num, i in enumerate(row):
                        row_order.update({i.value.lower(): num})
                    continue
                article = str(row[row_order['sku']].value)
                barcode = str(row[row_order['barcode']].value)
                name = str(row[row_order['name']].value)
                barcodes.append(barcode)
                barcodes.append(article)
                barcodes.append(name)
                result.append((
                    row[row_order['name']].value,
                    article,
                    barcode,
                    row[row_order['quantity']].value,
                ))
            purch_order_obj = request.env['purchase.order']
            purch_order_line_obj = request.env['purchase.order.line']
            product_obj = request.env['product.product']
            products_map = {i.barcode: i for i in product_obj.sudo().search([
                ('barcode', 'in', barcodes)
            ])}
            products_map |= {i.default_code: i for i in product_obj.sudo().search([
                ('default_code', 'in', barcodes)
            ])}
            products_map |= {i.name: i for i in product_obj.sudo().search([
                ('name', 'in', barcodes)
            ])}
            p_lines_vals = []
            order = purch_order_obj.sudo().create({
                'partner_id': shop_id,
                'date_order': date,
                'warehouse_id': warh_id
            })
            for i in result:
                product = products_map.get(i[1])
                if not product:
                    product = products_map.get(i[2])
                    if not product:
                        product = products_map.get(i[0])
                        if not product:
                            raise UserError(f'Сouldn\'t find the product by parameters\n'
                                            f'Product name: {i[0]}\n'
                                            f'Product barcode: {i[1]}\n'
                                            f'Product sku: {i[2]}\n'
                            )
                if i[2]:
                    product.barcode = i[2]
                p_lines_vals.append({
                    'product_id': product.id,
                    'product_qty': i[3],
                    'order_id': order.id
                })

            order.order_line = purch_order_line_obj.sudo().create(p_lines_vals)
            return request.redirect(order.get_portal_url())
        return request.render('retail_crm.create_new_acceptation', values, headers={
            'X-Frame-Options': 'DENY'
        })


def get_error(e, path=''):
    """ Recursively dereferences `path` (a period-separated sequence of dict
    keys) in `e` (an error dict or value), returns the final resolution IIF it's
    an str, otherwise returns None
    """
    for k in (path.split('.') if path else []):
        if not isinstance(e, dict):
            return None
        e = e.get(k)

    return e if isinstance(e, str) else None
