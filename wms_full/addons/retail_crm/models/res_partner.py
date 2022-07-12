# -*- coding: utf-8 -*-

from odoo import models, fields, api
import xmltodict
import requests
from odoo.tools import mute_logger


class ResPartnerBank(models.Model):
    """"
    Добовим кор счет
    """
    _inherit = 'res.partner.bank'

    corr_account = fields.Char('Corr account Number', required=True)

class ResUser(models.Model):
    """"
    Добовим кор счет
    """
    _inherit = 'res.users'

    barcode = fields.Char('Barcode', required=True, index=True)


class Partner(models.Model):
    _inherit = 'res.partner'


    retailcrm = fields.Many2one(
        'retailcrm', 'RetailCRM', index=True, required=True
    )
    is_company = fields.Boolean(string='Is a Company', default=False,
                                help="Check if the contact is a company, otherwise it is a person")
    company_type = fields.Selection(string='Company Type',
                                    selection=[('person', 'Individual'), ('company', 'Company'), ('shop', 'Shop')],
                                    compute='_compute_company_type', inverse='_write_company_type', store=True)

    orgnip = fields.Char(
        'ORGNIP'
    )
    ogrn = fields.Char(
        'OGRN'
    )
    certificatenumber = fields.Char(
        'Certificate number'
    )
    certificatedate = fields.Date(
        'Certificate date'
    )
    # bik = fields.Char(
    #     'BIK'
    # )
    kpp = fields.Char(
        'KPP'
    )
    ymlurl = fields.Char(
        'ymlUrl'
    )
    retailcrm_id = fields.Integer(
        'retailCrm ID',
        index=True
    )
    code = fields.Char(
        'retailCrm Code',
        index=True
    )
    retailcrm_catalog_id = fields.Integer(
        'retailCrm catalog ID',
        index=True
    )

    @api.depends('is_company')
    def _compute_company_type(self):
        pass

    def _write_company_type(self):
        for partner in self:
            partner.is_company = partner.company_type in ('company', 'shop')

    @api.onchange('company_type')
    def onchange_company_type(self):
        self.is_company = (self.company_type in ('company', 'shop'))


    def _create_groups_recursive(self, categs):
        self.ensure_one()
        to_back = []
        to_create = []
        categ_obj = self.env['product.category']
        categ_owner = {
            i.external_id: i
            for i in categ_obj.search([
                ('owner_id', '=', self.id),
            ])
        }
        for i in categs:
            parent = i['parent_id']
            if parent:
                parent = categ_owner.get(parent)
                if not parent:
                    to_back.append(i)
                    continue
            vals = {
                'external_id': i['id'],
                'owner_id': self.id,
                'name': i['name'],
                'parent_id': parent.id if parent else False,
            }
            exist = categ_owner.get(i['id'])
            if exist:
                exist.write(vals) # Если есть перезаписываем значения
                print(f'Updated: {exist.name} for shop {self.name}')
            else:
                to_create.append(vals) # Если нет добавляем к созданию
        categ_obj.create(to_create)
        print(f'Created: {len(to_create)} groups for shop: {self.name}')
        return to_back

    def _sync_categories(self):
        if not self.ymlurl:
            return False
        self.ensure_one()
        resource = requests.get(self.ymlurl)
        json_body = xmltodict.parse(resource.text)
        category_to_create = []
        yml_categoryes = json_body['yml_catalog']['shop']['categories']['category']
        for i in yml_categoryes:
            category_to_create.append({
                'id': i['@id'],
                'parent_id': i.get('@parentId', False),
                'name': i['#text']
            })
        while category_to_create:
            category_to_create = self._create_groups_recursive(category_to_create)

    def update_product(self, product, vals):
        new_vals = {}
        for key, value in vals.items():
            attr = getattr(product, key)
            if isinstance(attr, models.Model):
                attr = attr.id
            if attr != value:
                new_vals.update({key: value})
        if new_vals:
            print('')
            with mute_logger('odoo.osv.expression'):
                product.write(new_vals)
                print(f'Updated: {product.name}')
        else:
            print(f'NON Updated: {product.name}')

    def _sync_offers(self):
        if not self.ymlurl:
            return False
        self.ensure_one()
        resource = requests.get(self.ymlurl, verify=False)
        json_body = xmltodict.parse(resource.text)
        product_obj = self.env['product.product']
        products_shop = {i.external_id: i for i in self.env['product.product'].search([('owner_id', '=', self.id)])}
        categs_shop = {i.external_id: i.id for i in self.env['product.category'].search([('owner_id', '=', self.id)])}
        products_to_create = []
        yml_offers = json_body['yml_catalog']['shop']['offers']['offer']
        for i in yml_offers:
            default_code = False
            if i.get('params'):
                for param in i['params']:
                    is_art = param.get('@code')
                    if is_art == 'article':
                        default_code = param['#text']
            if not default_code:
                default_code = i['xmlId']

            name = i.get('productName')
            if not name:
                name = i.get('name')
            vals = {
                'name': name,
                'owner_id': self.id,
                'categ_id': categs_shop.get(i['categoryId'], 1),
                'default_code': default_code,
                'url': i.get('url', False),
                'url_image': i['picture'] if len(i['picture']) > 10 else False,
                #'description': product.get('description', False),
                'external_id': i['@id'],
                #'quantity': product.get('quantity', False),
                #'retailcrm_id': product['id'],
                'detailed_type': 'product',
                'barcode': i.get('barcode')
            }
            exist = products_shop.get(i['@id'])
            if exist:
                self.update_product(exist, vals)
            else:
                products_to_create.append(vals)

        product_obj.create(products_to_create)
        print(f'Created: {len(products_to_create)} for shop {self.name}')

