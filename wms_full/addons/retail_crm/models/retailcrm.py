# -*- coding: utf-8 -*-
import requests
from odoo import models, fields, api
from odoo.exceptions import UserError
from collections import defaultdict


class RetailCrm(models.Model):
    _description = 'RetailCRM settings'
    _name = "retailcrm"

    company_id = fields.Many2one(
        'res.company', 'Company', index=True
    )
    integration_url = fields.Char(
        'Integration URL adress', help='You need to set the URL address of your system'
    )
    integration_apikey = fields.Char(
        'Integration apiKey', help='You need to set the apiKey address of your system'
    )

    def get_all_shops(self):
        self.ensure_one()
        partner_obj = self.env['res.partner']
        return partner_obj.search([
            ('type', '=', 'delivery'),
            ('retailcrm', '=', self.id),
            ('ymlurl', '!=', False)
        ])

    def get_or_create_crm_bank(self, contragent, contragent_data):
        """
        Создаем счет
        :param contragent_data:
        :return: обьект счета
        """
        bank_obj = self.env['res.bank']
        bank_partner_obj = self.env['res.partner.bank']
        if not contragent_data.get('BIK'):
            return False
        bank = bank_obj.search([
            ('bic', '=', contragent_data['BIK'])
        ])
        if not bank:
            bank = bank_obj.create({
                'name': contragent_data['bank'],
                'bic': contragent_data['BIK']

            })
        bank_partner = bank_partner_obj.search([
            ('bank_id', '=', bank.id),
            ('acc_number', '=', contragent_data['bankAccount'])
        ])
        bank_partner_values = {
            'partner_id': contragent.id,
            'acc_number': contragent_data['bankAccount'],
            'bank_id': bank.id,
            'corr_account': contragent_data['corrAccount'],
            'acc_holder_name': contragent_data['code']
        }
        if not bank_partner:
            bank_partner = bank_partner_obj.create(bank_partner_values)
        else:
            bank_partner.write(bank_partner_values)
        return bank_partner.id

    def get_or_create_crm_main_partner(self, contragent_data):
        partner_obj = self.env['res.partner']
        contragent = partner_obj.search(['&',
                                         ('vat', '=', contragent_data['INN']),
                                         ('parent_id', '=', False)
                                         ])
        contragent_values = {
            'retailcrm': self.id,
            'name': contragent_data['legalName'],
            'street': contragent_data.get('legalAddress', ''),
            'vat': contragent_data.get('INN', ''),
            'orgnip': contragent_data.get('OGRNIP', ''),
            'ogrn': contragent_data.get('OGRN', ''),
            'code': contragent_data.get('code', ''),
            'certificatenumber': contragent_data.get('certificateNumber', ''),
            'certificatedate': contragent_data.get('certificateDate', False),
        }
        if not contragent:
            contragent = partner_obj.create(contragent_values)
        else:
            contragent.write(contragent_values)
        contragent.write({
            'company_type': 'company',
            'bank_ids': [(4, self.get_or_create_crm_bank(contragent, contragent_data))],
        })
        # create portal_user
        login = f'{contragent.vat}@wms.ru'
        res_user_obj = self.env['res.users']
        exist = res_user_obj.search([('login', '=', login)])
        if not exist:
            res_user_obj.create({
                'name': contragent.name,
                'login': login,
                'partner_id': contragent.id,
                'password': 'Zz123456', #TODO:
                'groups_id': [(6, 0, self.env.ref('base.group_portal').ids)]
            })
        return contragent.id

    def parce_sites(self, responce_data):
        self.ensure_one()
        partner_obj = self.env['res.partner']
        sites = responce_data.get('sites')
        for name, site in sites.items():
            partner = partner_obj.search([
                ('retailcrm_id', '=', site['id'])
            ])
            partner_values = {
                'parent_id': self.get_or_create_crm_main_partner(site['contragent']) if site.get(
                    'contragent') else False,
                'retailcrm_id': site['id'],
                'retailcrm': self.id,
                'retailcrm_catalog_id': site['catalogId'],
                'name': site['name'],
                'ymlurl': site['ymlUrl'] if site.get('ymlUrl') else False,
                'code': site['code'],
                'email': site.get('senderEmail') if site.get('senderEmail') else site.get('senderName'),
                'type': 'delivery',
                'company_type': 'shop',
            }
            if not partner:
                try:
                    partner_obj.create(partner_values)
                    print(f'Partners: {len(partner_values)} - created')
                except Exception as ex:
                    raise UserError(_(
                        f'{partner_values} {ex}',
                    ))
            else:
                partner.write(partner_values)
                print(f'Partner: {partner.name} - updated')

    def sync_retail_srm_partners(self):
        path = '/api/v5/reference/sites'
        rsrms = self.search([])
        for rs in rsrms:
            url, apikey = rs.integration_url, rs.integration_apikey
            responce = requests.get(f'{url}{path}', params={'apiKey': apikey})
            if responce:
                if responce.status_code == 200:
                    rs.parce_sites(responce.json())
                else:
                    print(f'Cannot to connect\n URL:{url}\napiKey:{apikey}')
        return True

    def group_write_recursive(self, shop, product_groups):
        unwrite_groups = []
        groups_by_shop = {
            i.retailcrm_id: i.id for i in self.env['product.category'].search([
                ('owner_id', '=', shop.id)
            ])
        }
        new_groups, to_create, to_write = [], [], []
        for group in product_groups:
            present = groups_by_shop.get(group.get('id'), False)
            parent = False
            if group.get('parentId'):
                parent = groups_by_shop.get(group.get('parentId'), False)
                if not parent:
                    unwrite_groups.append(group)
                    continue
            vals = {
                'retailcrm_id': group['id'],
                'externalId': group.get('externalId', ''),
                'owner_id': shop.id,
                'name': group['name'],
                'parent_id': parent,
                'active': group['active']

            }
            if not present:
                to_create.append(vals)
            else:
                to_write.append(vals)

        return unwrite_groups, to_create, to_write

    def create_or_update_groups(self, shop, product_groups):
        category_obj = self.env['product.category']
        to_create = 0
        while product_groups:
            product_groups, to_cr, to_wr = self.group_write_recursive(
                shop, product_groups
            )
            category_obj.create(to_cr)
            to_create += len(to_cr)
        print(f'created: {to_create} groups for {shop.name}')

    def get_shop_groups(self, shop):
        self.ensure_one()
        path = '/api/v5/store/product-groups'
        url, apikey = self.integration_url, self.integration_apikey
        product_groups = []
        page = 1
        while True:
            params = {
                'apiKey': apikey,
                'filter[sites][]': f'{shop.code}',
                'limit': 100,
                'page': page
            }
            responce = requests.get(
                f'{url}{path}', params=params
            )
            if responce.status_code == 200:
                product_groups += responce.json()['productGroup']
            else:
                raise UserError(_(
                    f' Import Groups Field',
                ))
            if not responce.json()['productGroup']:
                break
            page += 1
        self.create_or_update_groups(
            shop, product_groups
        )
        self.env.cr.commit()

    def create_or_update_pricelist(self, shop):
        price_list = self.env['product.pricelist'].search([('owner_id', '=', shop.id)])
        if not price_list:
            price_list = self.env['product.pricelist'].create({
                'name': shop.name,
                'owner_id': shop.id
            })
        return price_list

    def create_offers_items(self, price_list, products, products_done):
        offers = {i['id']: i['offers'] for i in products}
        products_map = {i['retailcrm_id']: i for i in products_done}
        price_obj = self.env['product.pricelist.item']
        prices_exists = {i.retailcrm_id: i for i in price_obj.search([
            ('pricelist_id', '=', price_list.id)
        ])}
        to_create = []
        for i, offers in offers.items():
            busket = []
            for offer in offers:
                price_exist = prices_exists.get(offer['id'])
                product = products_map[i]
                vals = {
                    'applied_on': '0_product_variant',
                    'retailcrm_id': offer['id'],
                    'external_id': offer.get('externalId', False),
                    'pricelist_id': price_list.id,
                    'fixed_price': offer.get('price', 0.0),
                    'product_id': product.id,
                    'min_quantity': offer.get('quantity', 0.0),
                    'default_code': offer.get('article', False),
                    'barcode': offer.get('barcode', False)
                }
                if price_exist:
                    price_exist.write(vals)
                    print(f'Price for product: {offer.get("name")} updated')
                else:
                    busket.append(vals)
            to_create += busket
        price_obj.create(to_create)
        print(f'New prices {len(to_create)} created')

    def update_product(self, product, vals):
        new_vals = {}
        for key, value in vals.items():
            attr = getattr(product, key)
            if isinstance(attr, models.Model):
                attr = attr.id
            if attr != value:
                new_vals.update({key: value})
        product.write(new_vals)

    def create_or_update_products(self, shop, products):
        to_create = []
        shop_products = {i.retailcrm_id: i for i in self.env['product.product'].search([
            ('owner_id', '=', shop.id)
        ])}
        shop_groups = {i.retailcrm_id: i.id for i in self.env['product.category'].search([
            ('owner_id', '=', shop.id)
        ])}
        price_list = self.create_or_update_pricelist(shop)
        products_done = []
        for product in products:
            cat_id = False
            cats = product.get('groups')
            if cats:
                cat_id = shop_groups.get(cats[0]['id'], False)
            vals = {
                'name': product['name'],
                'owner_id': shop.id,
                'categ_id': cat_id if cat_id else 1,
                'default_code': product.get('article', False),
                'url': product.get('url', False),
                'url_image': product.get('imageUrl', False),
                'description': product.get('description', False),
                'external_id': product.get('externalId', False),
                'quantity': product.get('quantity', False),
                'retailcrm_id': product['id'],
                'detailed_type': 'product'
            }
            if not shop_products.get(product['id']):
                to_create.append(vals)
                print(f"product created for shop {shop.name}")
            else:
                product_to_write = shop_products.get(product['id'])
                self.update_product(product_to_write, vals)
                products_done += product_to_write
                print(f"product  writed for shop {shop.name}")
        products_done += self.env['product.product'].create(to_create)
        self.create_offers_items(price_list, products, products_done)
        print(f'Created: {len(to_create)} producst for {shop.name}')

    def parce_products(self, shop):
        self.ensure_one()
        path = '/api/v5/store/products'
        url, apikey = self.integration_url, self.integration_apikey
        products = []
        page = 1
        while True:
            params = {
                'apiKey': apikey,
                'filter[sites][]': f'{shop.code}',
                'limit': 100,
                'page': page
            }
            responce = requests.get(
                f'{url}{path}', params=params
            )
            if responce.status_code == 200:
                products += responce.json()['products']
            else:
                raise UserError(_(
                    f' Import Groups Field',
                ))
            if not responce.json()['products']:
                break
            page += 1
        self.create_or_update_products(
            shop, products
        )
        self.env.cr.commit()

    def sync_retail_srm_products(self):
        rsrms = self.search([])
        for rs in rsrms:
            for shop in rs.get_all_shops():
                rs.get_shop_groups(shop)
                rs.parce_products(shop)
        return True

    def create_product_by_offer(self, offer, shop, pricelist):
        price_item_obj = self.env['product.pricelist.item']
        product_obj = self.env['product.product']
        path = '/api/v5/store/products'
        url = self.integration_url
        params = {
            'apiKey': self.integration_apikey,
            '[offerIds][]': f'{offer["id"]}',

        }
        responce = requests.get(f'{url}{path}', params=params)
        product = responce.json().get('products')[0]
        offer = product['offers'][0]
        new_product_vals = {
            'name': product['name'],
            'owner_id': shop.id,
            'categ_id': 1,
            'default_code': product.get('article', False),
            'external_id': offer.get('externalId', False),
            'quantity': offer.get('quantity', False),
            'retailcrm_id': product['id'],
            'detailed_type': 'product'
        }
        product = product_obj.search([('retailcrm_id', '=', product['id'])])
        if not product:
            product = product_obj.create(new_product_vals)
        price_item__vals = {
            'applied_on': '0_product_variant',
            'retailcrm_id': offer['id'],
            'external_id': offer.get('externalId', False),
            'pricelist_id': pricelist.id,
            'fixed_price': offer.get('price', 0.0),
            'min_quantity': offer.get('quantity', 0.0),
            'default_code': offer.get('article', False),
            'barcode': offer.get('barcode', False),
            'product_id': product[0].id
        }
        price_item = product_obj.search([('retailcrm_id', '=', offer['id'])])
        if not price_item:
            price_item = price_item_obj.create(price_item__vals)
        return price_item[0]

    def create_objects_by_orders(self, shop, orders):
        to_create = []
        delivery_obj = self.env['retailcrm.delivery']
        order_obj = self.env['retailcrm.order']
        order_line_obj = self.env['retailcrm.order.line']
        deliveryes = {i.code: i for i in delivery_obj.search([])}
        pricelist_id = self.env['product.pricelist'].search([('owner_id', '=', shop.id)])
        pricelist_id.ensure_one()
        price_item_obj = self.env['product.pricelist.item']
        items_orders = {i['id']: i['items'] for i in orders}
        ids_crm = [s['offer']['id'] for l in [x for x in items_orders.values()] for s in l]
        ids_order_items = [s['id'] for l in [x for x in items_orders.values()] for s in l]
        ids_pr_tl = {
            i.retailcrm_id: i.id for i in price_item_obj.search([])}
        items_cleaned = defaultdict(list)
        for crm_id, i in items_orders.items():
            for item in i:
                offer_id = item['offer']['id']
                price_item_id = ids_pr_tl.get(offer_id)
                if not price_item_id:

                    offer = item['offer']
                    print(f'no price for order {shop.id} {offer["id"]}: {offer["name"]}')
                    price_item_id = self.create_product_by_offer(offer, shop, pricelist_id).product_id.id
                for price in item['prices']:
                    items_cleaned[crm_id].append({
                        'retailcrm_id': item['id'],
                        'product_id': price_item_id,
                        'price': price['price'],
                        'order_qty': price['quantity'],
                    })
        orders_exists = {
            i.retailcrm_id: i for i in
            order_obj.search([('retailcrm_id', 'in', list(items_orders.keys()))])
        }
        order_lines_exists = {i.retailcrm_id: i for i in order_line_obj.search([('retailcrm_id','in', ids_order_items)])}
        updated = 0
        for order in orders:
            delivery_code = order['delivery'].get('code', 'unknown')
            delivery_id = deliveryes.get(delivery_code)
            if not delivery_id:
                delivery_id = delivery_obj.create({
                    'code': delivery_code,
                    'name': delivery_code
                })
                deliveryes.update({delivery_id.code: delivery_id})
            items = items_cleaned.get(order['id'], [])
            order_lines = self.env['retailcrm.order.line']
            for i in items:
                order_line = order_lines_exists.get(i['retailcrm_id'])
                if not order_line:
                    order_lines += order_line_obj.create(i)
                else:
                    order_line.write(i)
                    order_lines += order_line

            order_vals = {
                'company_id': 1,  # TODO:
                'status': order['status'],
                'owner_id': shop.id,
                'client_id': 1,
                'retailcrm_id': order['id'],
                'external_id': order['number'],
                'status_updated': order['statusUpdatedAt'],
                'sum': order['summ'],
                'total_sum': order['totalSumm'],
                'prepaysum': order['prepaySum'],
                'order_type': order['orderType'],
                'delivery': delivery_id.id,
                'order_line_ids': [(6, 0, order_lines.ids)]
            }
            order = orders_exists.get(order['id'])
            if not order:
                to_create.append(order_vals)
            else:
                order.write(order_vals)
                updated += 1
        order_obj.create(to_create)
        print(f'Orders: {len(to_create)} for {shop.name} created')
        print(f'Orders: {updated} for {shop.name} updated')

    def create_crm_orders(self, shop, orders):
        self.create_objects_by_orders(shop, orders)
        print('FINISH')
        self.env.cr.commit()

    def parce_orders(self, shop):
        path = '/api/v5/orders'
        url, apikey = self.integration_url, self.integration_apikey
        page = 1
        while True:
            params = {
                'apiKey': apikey,
                'filter[sites][]': f'{shop.code}',
                'limit': 100,
                'page': page
            }
            responce = requests.get(
                f'{url}{path}', params=params
            )
            if responce.status_code == 200:
                products = responce.json()['orders']
                self.create_crm_orders(
                    shop, products
                )
            else:
                raise UserError(_(
                    f' Import orders Field',
                ))
            if not responce.json()['orders']:
                break
            page += 1
        print('FINISH PRODUCTS')

    def sync_retail_srm_orders(self):
        rsrms = self.search([])
        for rs in rsrms:
            for shop in rs.get_all_shops():
                rs.parce_orders(shop)
        return True
