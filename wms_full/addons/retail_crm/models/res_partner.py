# -*- coding: utf-8 -*-

from odoo import models, fields, api



class ResPartnerBank(models.Model):
    """"
    Добовим кор счет
    """
    _inherit = 'res.partner.bank'

    corr_account = fields.Char('Corr account Number', required=True)


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
