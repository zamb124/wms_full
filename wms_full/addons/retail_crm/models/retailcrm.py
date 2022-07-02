# -*- coding: utf-8 -*-
import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

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
            ('retailcrm', '=', self.id)
        ])

    def get_or_create_crm_bank(self,contragent, contragent_data):
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
                'parent_id': self.get_or_create_crm_main_partner(site['contragent']) if site.get('contragent') else False,
                'retailcrm_id': site['id'],
                'retailcrm': self.id,
                'retailcrm_catalog_id': site['catalogId'],
                'name': site['name'],
                'ymlurl': site['ymlUrl'] if site.get('ymlUrl') else '',
                'code': site['code'],
                'email': site.get('senderEmail') if site.get('senderEmail') else site.get('senderName'),
                'type': 'delivery'
            }
            if not partner:
                try:
                    partner_obj.create(partner_values)
                except Exception as ex:
                    raise UserError(_(
                        f'{partner_values} {ex}',
                    ))
            else:
                partner.write(partner_values)

    def sync_retail_srm_partners(self):
        path = '/api/v5/reference/sites'
        rsrms = self.search([])
        for rs in rsrms:
            url, apikey = rs.integration_url, rs.integration_apikey
            responce = requests.get(f'{url}{path}', params={'apiKey': apikey})
            if responce:
                if responce.status_code == 200:
                    rs.parce_sites(responce.json())
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
        """
        	"parentId": 4489,
			"site": "www-sweethelp-ru",
			"id": 6816,
			"name": "Забавные подарки",
			"externalId": "5941890",
			"active": true
        """
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

    def create_or_update_products(self, shop, products):
        to_create = []
        shop_products = {i.retailcrm_id: i for i in self.env['product.template'].search([
            ('owner_id', '=', shop.id)
        ])}
        shop_groups = {i.retailcrm_id: i.id for i in self.env['product.category'].search([
            ('owner_id', '=', shop.id)
        ])}
        for product in products:
            cat_id = False
            cats = product.get('groups')
            if cats:
                cat_id = shop_groups.get(cats[0]['id'], False)
            vals = {
                'name': product['name'],
                'owner_id': shop.id,
                'categ_id': cat_id,
                'article': product.get('article'),
                'url': product.get('url'),
                'url_image': product.get('imageUrl'),
                'description': product.get('description'),
                'external_id': product.get('externalId'),
                'quantity': product.get('quantity'),
                'retailcrm_id': product['id'],
                'detailed_type': 'product'
            }
            if not shop_products.get(product['id']):
                to_create.append(vals)
                print(f"product created for shop {shop.name}")
            else:
                shop_products.get(product['id']).write(vals)
                print(f"product  writed for shop {shop.name}")
        self.env['product.template'].create(to_create)
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
        partner_obj = self.env['res.partner']
        path = '/api/v5/store/products'
        rsrms = self.search([])
        for rs in rsrms:
            for shop in rs.get_all_shops():
                rs.get_shop_groups(shop)
                rs.parce_products(shop)
        return True



