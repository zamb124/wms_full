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




