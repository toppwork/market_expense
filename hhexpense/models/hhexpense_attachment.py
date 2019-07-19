# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class HHExpenseAttachment(models.Model):
    _name = 'hhexpense.attachment'
    _inherit = 'ir.attachment'
    _order = 'create_date asc'

    hhexpense = fields.Many2one('hhexpense.hhexpense', ondelete='cascade', string='E-Expense')
    state = fields.Char(compute='_compute_state')
    is_guser = fields.Char(compute='_compute_is_guser')
    general_type = fields.Char(compute='_compute_general_type', store=True)

    @api.depends('res_model', 'res_id')
    def _compute_state(self):
        for attachment in self:
            if attachment.res_model and attachment.res_id:
                record = attachment.env[attachment.res_model].browse(attachment.res_id)
                attachment.state = record.state

    @api.depends('res_model', 'res_id')
    def _compute_is_guser(self):
        for attachment in self:
            if attachment.res_model and attachment.res_id:
                record = attachment.env[attachment.res_model].browse(attachment.res_id)
                attachment.is_guser = record.is_guser

    @api.depends('mimetype')
    def _compute_general_type(self):
        for rec in self:
            general_type, detail = rec.mimetype.split('/')
            if general_type == 'image':
                rec.general_type = general_type
            elif general_type == 'application' and detail == 'pdf':
                rec.general_type = 'pdf'
            else:
                rec.general_type = 'others'

    @api.model
    def create(self, values):
        for field in ('file_size', 'checksum'):
            values.pop(field, False)
        values = self._check_contents(values)
        self.browse().check('write', values=values)
        return super(HHExpenseAttachment, self).create(values)

