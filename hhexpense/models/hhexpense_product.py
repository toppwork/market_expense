# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HHexpenseProductTemplate(models.Model):
    _inherit = "product.template"

    can_be_hhexpensed = fields.Boolean(help="Specify whether the product can be selected in an HR expense.", string="Can be Expensed")

    @api.model
    def create(self, vals):
        # When creating an expense product on the fly, you don't expect to
        # have taxes on it
        if vals.get('can_be_hhexpensed', False):
            vals.update({'supplier_taxes_id': False})
        return super(HHexpenseProductTemplate, self).create(vals)
