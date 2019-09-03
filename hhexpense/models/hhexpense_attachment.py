# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import os


# for get user_agent
#     from odoo import http
#     import httpagentparser


# class HHExpenseAttachment(models.Model):
#     # _name = 'hhexpense.attachment'
#     _inherit = 'ir.attachment'
#
#     hhexpense = fields.Many2one('hhexpense.hhexpense', ondelete='cascade')
#     state = fields.Char(compute='_compute_state')
#     is_guser = fields.Char(compute='_compute_is_guser')
#
#     @api.onchange('datas')
#     def auto_fill_name(self):
#         file_type = isinstance(self.datas_fname, bool)
#         # print("attachment type: ", file_type)
#         if file_type:
#             # print("user haven't select file yet")
#             pass
#         else:
#             self.name = os.path.splitext(self.datas_fname)[0]
#
#     @api.depends('res_model', 'res_id')
#     def _compute_state(self):
#         # # print("Triggered")
#         # # print(self.hhexpense.id)
#         for attachment in self:
#             if attachment.res_model and attachment.res_id:
#                 record = attachment.env[attachment.res_model].browse(attachment.res_id)
#                 attachment.state = record.state
#
#     @api.depends('res_model', 'res_id')
#     def _compute_is_guser(self):
#         for attachment in self:
#             if attachment.res_model and attachment.res_id:
#                 record = attachment.env[attachment.res_model].browse(attachment.res_id)
#                 attachment.is_guser = record.is_guser
#
#     @api.model
#     def create(self, values):
#         # # print(self.state)
#         # remove computed field depending of datas
#         for field in ('file_size', 'checksum'):
#             values.pop(field, False)
#         values = self._check_contents(values)
#         self.browse().check('write', values=values)
#         simple_type = values['mimetype'].split('/')[0]
#         # # print(type(values))
#         if ('res_model' in values) and (values['res_model'] != 'hhexpense.hhexpense'):
#             pass
#         else:
#             if values['datas'] is False:
#                 raise UserError(_("You must forget to upload your file!"))
#             elif(values['mimetype'] == 'application/pdf') or (simple_type == 'image'):
#                 # print('File type validated')
#                 pass
#             else:
#                 # print(self)
#                 raise UserError(_("You can only upload PDF or Image!"))
#         return super(HHExpenseAttachment, self).create(values)
#
#     @api.multi
#     def preview_file(self):
#         # print('preview la')
#         url = f'http://localhost:8069/web/content/{self.id}'
#         return {
#             'type': 'ir.actions.act_url',
#             'name': 'Preview attachment',
#             'url': url,
#             'target': 'new',
#         }
#
#         # get user_agent
#         # user_agent = http.request.httprequest.environ.get('HTTP_USER_AGENT', '')
#         # # print(user_agent)
#         # # split browser name from user_agents
#         # parse_result = httpagentparser.simple_detect(user_agent)
#         # # print(parse_result)
#         # browser = (parse_result[1].split())[0].lower()
#         # # print(browser)
#
#         # get base_url from odoo system
#         # base_url = http.request.env['ir.config_parameter'].get_param('web.base.url')
#         # webbrowser.open_new_tab('%s/web/content/%s' % (base_url, self.id))
#
#     @api.multi
#     def download_file(self):
#         # print('download la')
#         url = f'http://localhost:8069/web/content/{self.id}?download=1'
#         return {
#             'type': 'ir.actions.act_url',
#             'name': 'Download attachment',
#             'url': url,
#             'target': 'current',
#         }
class HHExpenseAttachment(models.Model):
    # _name = 'hhexpense.attachment'
    _inherit = 'ir.attachment'
    _order = 'create_date asc'

    hhexpense = fields.Many2one('hhexpense.hhexpense', ondelete='cascade', string='E-Expense')
    state = fields.Char(compute='_compute_state')
    is_guser = fields.Char(compute='_compute_is_guser')
    general_type = fields.Char(compute='_compute_general_type', store=True)

    # name = fields.Char('Name')
    # travel_doc = fields.Binary("Document", attachment=True)
    #

    # @api.onchange('datas')
    # def auto_fill_name(self):
    #     file_type = isinstance(self.datas_fname, bool)
    #     # print("attachment type: ", file_type)
    #     if file_type:
    #         # print("user haven't select file yet")
    #         pass
    #     else:
    #         self.name = os.path.splitext(self.datas_fname)[0]

    @api.depends('res_model', 'res_id')
    def _compute_state(self):
        # # print("Triggered")
        # # print(self.hhexpense.id)
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
        # # print(self.state)
        # remove computed field depending of datas
        for field in ('file_size', 'checksum'):
            values.pop(field, False)
        values = self._check_contents(values)
        self.browse().check('write', values=values)
        simple_type = values['mimetype'].split('/')[0]
        # # print(type(values))
        # if ('res_model' in values) and (values['res_model'] != 'hhexpense.hhexpense'):
        #     pass
        # else:
        #     if values['datas'] is False:
        #         raise UserError(_("You must forget to upload your file!"))
        #     elif(values['mimetype'] == 'application/pdf') or (simple_type == 'image'):
        #         # print('File type validated')
        #         pass
        #     else:
        #         # print(self)
        #         raise UserError(_("You can only upload PDF or Image!"))
        return super(HHExpenseAttachment, self).create(values)

    #
    @api.multi
    def preview_file(self):
        # print('preview la')
        url = f'http://localhost:8069/web/content/{self.id}'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Preview attachment',
            'url': url,
            'target': 'new',
        }

    #
    #     # get user_agent
    #     # user_agent = http.request.httprequest.environ.get('HTTP_USER_AGENT', '')
    #     # # print(user_agent)
    #     # # split browser name from user_agents
    #     # parse_result = httpagentparser.simple_detect(user_agent)
    #     # # print(parse_result)
    #     # browser = (parse_result[1].split())[0].lower()
    #     # # print(browser)
    #
    #     # get base_url from odoo system
    #     # base_url = http.request.env['ir.config_parameter'].get_param('web.base.url')
    #     # webbrowser.open_new_tab('%s/web/content/%s' % (base_url, self.id))
    #
    @api.multi
    def download_file(self):
        # print('download la')
        url = f'http://localhost:8069/web/content/{self.id}?download=1'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Download attachment',
            'url': url,
            'target': 'current',
        }

    @api.multi
    def keep_data_integrity(self, v):
        """
        Purpose: This function is used for making sure 'ir.attachment' table's data integrity. When we creating
        expense's attachment, 'res_name', 'res_model' and 'res_id' field's value are missing. But we may need these
        value somewhere else even it seems that it doesn't has any impact for now, thus, we use this function
        to manually update these fields.
        """
        v['res_name'] = self.env['hhexpense.hhexpense'].search([(['id', '=', v['hhexpense']])]).name
        v['res_model'] = 'hhexpense.hhexpense'
        v['res_id'] = v['hhexpense']
        return v
