# -*- coding: utf-8 -*-
from odoo.api import Environment
from odoo import models, fields, api, _, registry
from odoo.exceptions import UserError
import datetime
from pytz import timezone
import threading
from time import sleep
import psycopg2
import os
from functools import partial
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell
from operator import itemgetter
import collections
import csv
import re
import socket
# using python to handle email sending function, not Odoo
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from odoo.addons import decimal_precision as dp


class HHExpense(models.Model):
    _name = 'hhexpense.hhexpense'
    _order = "create_date desc"
    _inherit = ['mail.thread']

    # --------------------------------------------- Local attributes ---------------------------------------------------
    # ------ Expense info ------
    name = fields.Char(string='Expense Summary', states={'draft': [('readonly', False)], 'rejected': [('readonly', False)]}, readonly=True, required=True)
    expense_num = fields.Char(string='Expense Track No.', compute="_compute_generate_expense_num", store=True)
    expense_create_date = fields.Date(string="Create Date", default=lambda self: fields.datetime.now(), readonly=True)
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('posted', 'Posted'),
        ('rejected', 'Rejected'),
        ('done', 'Done')
    ], string='Status', default='draft', copy=False, index=True, readonly=True, store=True, help="Expense Status")

    expense_line = fields.One2many('hhexpense.line', string='Expenses Details', inverse_name='expense_id', states={'draft': [('readonly', False)], 'rejected': [('readonly', False)], 'approved': [('readonly', False)]}, readonly=True, help="Expense's detail information")
    reject_reason = fields.Char(string='Reject Reason', readonly=True)

    # ------ Logging info ------
    rec_approver_name = fields.Char(string="Approved By", readonly=True)
    approval_time = fields.Char()  # use 'Char' type for ez operation purpose

    # ------ Attachments info ------
    expense_attachment = fields.One2many('hhexpense.attachment', inverse_name='hhexpense',
                                         states={'draft': [('readonly', False)], 'rejected': [('readonly', False)]}, readonly=True)
    # expense_attachment = fields.One2many('ir.attachment', inverse_name='hhexpense')
    confirm_invoice = fields.Boolean(string='Receipt', compute='_compute_invoice', readonly=True, store=True)
    attachment_num = fields.Integer(string='Number of Attachments', compute='_calculate_attachment_num')

    # ------ Company info ------
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id)

    # ------ Employee info ------
    employee_id = fields.Many2one('hr.employee', default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1), required=True, readonly=True)
    department_id = fields.Many2one('hr.department', default=lambda self: self.env.user.employee_ids.department_id)
    employee_name = fields.Char(default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1).name, readonly=True)
    # Following code line is not the best coding practice to obtain department information, should be using default
    employee_department = fields.Char(compute='_compute_dep_from_employee_info', store=True)
    is_guser = fields.Boolean(compute='_check_user_in_guser_group', readonly=True)

    # ------ Current login user's ID info ------
    current_uid = fields.Many2one('res.users', readonly=True, compute='_get_current_uid')
    # Checking whether create user is current user, which can then hide the expense in the approval view if true.
    match_uid = fields.Boolean(compute='_check_uid', default=True)

    # ------ amount related ------
    calculate_total_amount = fields.Float(string='Total Payout Amount', compute='_compute_total_amount', digits=(12, 2), store=True)

    # ------ Email related ------
    current_menu_id = fields.Char()  # was used in 'cron_job_send_reminder_email()' function
    current_action_id = fields.Char()  # was used in 'cron_job_send_reminder_email()' function
    # URL needed for email
    to_approve_url = fields.Char()
    approved_url = fields.Char()

    # ------ Claim for others ------
    claim_as_agent = fields.Boolean(default=False, string='Claim for others', states={'draft': [('readonly', False)], 'rejected': [('readonly', False)]}, readonly=True)
    agent_reimb_id = fields.Many2one('hhexpense.agent.reimbursement', string='Select Staff',
                                     states={'draft': [('readonly', False)], 'rejected': [('readonly', False)]}, readonly=True)
    expense_belongs_to_employee = fields.Char(string="Belongs to", compute='_compute_expense_belongs_to_employee', store=True)

    # accounting_related
    journal_id = fields.Many2one('account.journal', string='Expense Journal',
                                 states={'done': [('readonly', True)], 'post': [('readonly', True)]},
                                 default=lambda self: self.env['ir.model.data'].xmlid_to_object(
                                     'hr_expense.hr_expense_account_journal') or self.env['account.journal'].search(
                                     [('type', '=', 'purchase')], limit=1),
                                 help="The journal used when the expense is done.")
    bank_journal_id = fields.Many2one('account.journal', string='Bank Journal',
                                      states={'done': [('readonly', True)], 'post': [('readonly', True)]},
                                      default=lambda self: self.env['account.journal'].search(
                                          [('type', 'in', ['cash', 'bank'])], limit=1),
                                      help="The payment method used when the expense is paid by the company.")
    accounting_date = fields.Date(string="Date")
    account_move_id = fields.Many2one('account.move', string='Journal Entry', ondelete='restrict', copy=False)
    payment_mode = fields.Selection([("own_account", "Employee (to reimburse)"), ("company_account", "Company")],
                                    states={'rejected': [('readonly', False)], 'draft': [('readonly', False)]},
                                    default='own_account', readonly=True, string="Payment By")
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  states={'draft': [('readonly', False)], 'refused': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id)
    address_id = fields.Many2one('res.partner', string="Employee Home Address")

    # -------------------------------------------- Define methods here -------------------------------------------------
    @api.onchange('name')
    def testing_only(self):
        resource = self.env['resource.resource'].search([('user_id', '=', self.env.user.id)])
        employee = self.env['hr.employee'].search([('resource_id', '=', resource.id)])

    @api.depends('claim_as_agent', 'agent_reimb_id')
    def _compute_expense_belongs_to_employee(self):
        for rec in self:
            if rec.claim_as_agent:
                rec.expense_belongs_to_employee = rec.agent_reimb_id.name.name
            else:
                rec.expense_belongs_to_employee = rec.employee_name

    def _get_current_uid(self):
        # write uid to the dummy column. Used to hide Approve button when a manager submits own expense.
        # TODO: This function and _check_uid should be one function instead of two.
        for rec in self:
            rec.update({'current_uid': self.env.uid})
        return

    def _check_uid(self):
        """
        If the managers has submitted expenses, they will see their own expense in the approval page. But the expense
        master view will include a "Manager Approve" button which is not desired. Until now (Ver. 11), uid is still not
        recognised in button node attributes like that in domain. For this reason, we need to create our own uid field
        for checking current user ID.
        """
        for rec in self:
            rec.update({'match_uid': False if rec.current_uid != rec.create_uid else True})
        return

    @api.depends('employee_name')
    def _compute_generate_expense_num(self):
        expense_list = []
        expense_num_list = []
        mst_rec = self.env['hhexpense.hhexpense'].search([])
        for rec in mst_rec:
            expense_list.append(rec.id)
            expense_num_list.append(int(rec.expense_num))

        if len(expense_list) > 1:
            for rec in self:
                rec.expense_num = max(expense_num_list) + 1
        else:
            self.update({'expense_num': 1000})

    @api.depends('employee_name')
    def _compute_dep_from_employee_info(self):
        emp_info = self.env['hr.employee'].sudo().search([])
        for rec in self:
            for emp in emp_info:
                if emp.name == self.env.user.name:
                    rec.employee_department = emp.department_id.name

    @api.multi
    def _check_user_in_guser_group(self):
        self.is_guser = True if self.env.user.has_group('hhexpense.group_hhexpense_user') else False

    @api.multi
    def _calculate_attachment_num(self):
        attachment_data = self.env['hhexpense.attachment'].search([])
        for rec in self:
            rec.attachment_num = 0
            for attachment in attachment_data:
                if attachment.hhexpense.id == rec.id:
                    rec.attachment_num += 1

    # ---------------------------- Calculate summary data of expense line ----------------------------
    @api.one
    @api.depends('expense_line', 'expense_line.expense_line_cost', 'expense_line.currency_id')
    def _compute_total_amount(self):
        total_amount = 0.0
        for expense in self.expense_line:
            total_amount += expense.currency_id.with_context(
                date=expense.date,
                company_id=expense.company_id.id
            ).compute(expense.expense_line_cost, self.currency_id)
        self.update({'calculate_total_amount': total_amount})

    @api.depends('expense_line')
    def _compute_invoice(self):
        invoice = False
        for expense_rec in self:
            for expense_line_rec in expense_rec.expense_line:
                # if any of sub-record choose "Yes", confirm_invoice will be set to True
                if expense_line_rec.confirm_item_invoice == 1:
                    invoice = True
        self.update({'confirm_invoice': invoice})

    # -------------------------------------- Email --------------------------------------
    @api.multi
    def submit_email(self):
        template = self.env.ref('hhexpense.mail_template_submitted_expense')
        self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)

    @api.multi
    def approve_email(self):
        template = self.env.ref('hhexpense.mail_template_approved_expense')
        self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)

    @api.multi
    def reject_email(self):
        template = self.env.ref('hhexpense.mail_template_reject_expense')
        self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)

    @api.multi
    def get_url_email_link(self):
        record_id = self.id
        menu_id = self.env['ir.ui.menu'].search([('name', '=', 'E-Expense(HH)')]).id
        act_window = self.env['ir.actions.act_window'].search([])
        web_base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for page in act_window:
            if page.name == 'Expenses to Approve':
                self.to_approve_url = f"{web_base_url}/web#id={record_id}" \
                                      f"&view_type=form&model=hhexpense.hhexpense&action={page.id}&menu_id={menu_id}"
            elif page.name == 'My Expenses':
                self.approved_url = f"{web_base_url}/web#id={record_id}" \
                                    f"&view_type=form&model=hhexpense.hhexpense&action={page.id}&menu_id={menu_id}"
            else:
                pass

    # -------------------------------------- Email --------------------------------------
    def hhexpense_post_message(self, state):
        if state == 'submit':
            # send message to dept manager to approve submitted expense
            manager_user_id = self.employee_id.parent_id.resource_id.user_id
            if not manager_user_id:
                # raise error
                raise UserError(_('Please define your department manager in Employee module first'))
            else:
                partner_id = manager_user_id.partner_id.id
                notification = _(
                    '<div class="o_mail_notification">Expense <strong>SUBMITTED</strong>, waiting approval</div>')
                subject = 'Expense submitted.'

        elif state == 'approve':
            partner_id = self.employee_id.resource_id.user_id.partner_id.id
            notification = _(
                '<div class="o_mail_notification">Expense <strong>APPROVED</strong>, waiting post</div>')
            subject = 'Expense approved.'

        elif state == 'reject':
            partner_id = self.employee_id.resource_id.user_id.partner_id.id
            notification = _(
                '<div class="o_mail_notification">Expense <strong>REJECTED</strong>, please check</div>')
            subject = 'Expense rejected.'

        elif state == 'post':
            partner_id = self.employee_id.resource_id.user_id.partner_id.id
            notification = _(
                '<div class="o_mail_notification">Expense <strong>POSTED</strong>, waiting payment</div>')
            subject = 'Expense rejected.'

        elif state == 'done':
            partner_id = self.employee_id.resource_id.user_id.partner_id.id
            notification = _(
                '<div class="o_mail_notification">Expense <strong>PAID</strong></div>')
            subject = 'Expense rejected.'

        else:
            partner_id = self.env.user.partner_id.id
            notification = _(
                '<div class="o_mail_notification"><strong>Test</strong></div>')
            subject = 'Test.'
        self.env['mail.message'].create({'message_type': "notification",
                                         "subtype": self.env.ref("mail.mt_comment").id,
                                         'body': notification,
                                         'subject': subject,
                                         'needaction_partner_ids': [(4, partner_id)],
                                         'model': self._name,
                                         'res_id': self.id,
                                         'author_id': self.env.user.partner_id.id,
                                         })

    # ------------------------------------- Header Button Action -------------------------------------
    @api.multi
    def submit_expense(self):
        em_no_attachment = 'Please attach the corresponding receipts for your expense!'
        em_no_line_item = 'Please provide at least one expense detail to submit expense!'
        em_need_select_delegator = 'Please select a employee you want to help with reimbursement!'

        if (self.confirm_invoice is True) and (self.attachment_num == 0):
            raise UserError(_(em_no_attachment))
        if self.claim_as_agent:
            if not self.agent_reimb_id:
                raise UserError(_(em_need_select_delegator))
        if len(self.expense_line) == 0:
            raise UserError(_(em_no_line_item))

        self.with_context(tracking_disable=False).state = 'submitted'
        self.get_url_email_link()
        self.submit_email()
        self.hhexpense_post_message('submit')

    @api.multi
    def approve_expense(self):
        self.with_context(tracking_disable=False).state = 'approved'  # this also work --> self.write({'state': 'approved'})
        self.rec_approver_name = self.env.user.name
        self.approval_time = datetime.datetime.now().strftime('%Y/%m/%d - %H:%M:%S:%f')
        self.approve_email()
        self.hhexpense_post_message('approve')

    @api.multi
    def reject_expense(self, reason):
        self.reject_reason = reason
        self.state = 'rejected'
        self.reject_email()
        self.hhexpense_post_message('reject')
        return

    # --------------------------------------- Overwrite method ---------------------------------------
    @api.multi
    def unlink(self):
        for expense in self:
            if expense.state not in ['draft', 'rejected']:
                raise UserError(_('Sorry! ' + expense.state + ' expense record cannot be deleted!'))
        super(HHExpense, self).unlink()

    @api.model
    def create(self, vals):
        sheet = super(HHExpense, self.with_context(tracking_disable=True)).create(vals)
        return sheet

    # --------------------------------------- Discuss Chatter Box ------------------------------------
    @api.model
    def message_new(self, msg_dict, custom_values=None):
        if custom_values is None:
            custom_values = {}

        email_address = email_split(msg_dict.get('email_from', False))[0]

        employee = self.env['hr.employee'].search([
            '|',
            ('work_email', 'ilike', email_address),
            ('user_id.email', 'ilike', email_address)
        ], limit=1)

        expense_description = msg_dict.get('subject', '')

        # Match the first occurence of '[]' in the string and extract the content inside it
        # Example: '[foo] bar (baz)' becomes 'foo'. This is potentially the product code
        # of the product to encode on the expense. If not, take the default product instead
        # which is 'Fixed Cost'
        default_product = self.env.ref('hr_expense.product_product_fixed_cost')
        pattern = '\[([^)]*)\]'
        product_code = re.search(pattern, expense_description)
        if product_code is None:
            product = default_product
        else:
            expense_description = expense_description.replace(product_code.group(), '')
            products = self.env['product.product'].search(
                [('default_code', 'ilike', product_code.group(1))]) or default_product
            product = products.filtered(lambda p: p.default_code == product_code.group(1)) or products[0]

        pattern = '[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?'
        # Match the last occurence of a float in the string
        # Example: '[foo] 50.3 bar 34.5' becomes '34.5'. This is potentially the price
        # to encode on the expense. If not, take 1.0 instead
        expense_price = re.findall(pattern, expense_description)
        if not expense_price:
            price = 1.0
        else:
            price = expense_price[-1][0]
            expense_description = expense_description.replace(price, '')
            try:
                price = float(price)
            except ValueError:
                price = 1.0

        custom_values.update({
            'name': expense_description.strip(),
            'employee_id': employee.id,
            'product_id': product.id,
            'product_uom_id': product.uom_id.id,
            'quantity': 1,
            'unit_amount': price,
            'company_id': employee.company_id.id,
        })
        return super(HHExpense, self).message_new(msg_dict, custom_values)

    # --------------------------------------- Accounting ----------------------------------------------
    @api.multi
    def action_sheet_move_create(self):
        if self.state != 'approved':
            raise UserError(_("You can only generate accounting entry for approved expense(s)."))

        if not self.journal_id:
            raise UserError(_("Expenses must have an expense journal specified to generate accounting entries."))

        expense_line_ids = self.expense_line
        res = expense_line_ids.action_move_create()

        if not self.accounting_date:
            self.accounting_date = self.account_move_id.date

        if self.payment_mode == 'own_account' and expense_line_ids:
            self.write({'state': 'posted'})
            self.hhexpense_post_message('post')

        else:
            self.write({'state': 'done'})
            self.hhexpense_post_message('done')

        return res

    @api.multi
    def set_to_paid(self):
        self.write({'state': 'done'})
        self.hhexpense_post_message('done')

    # --------------------------------------- Product ----------------------------------------------


class HHExpenseLine(models.Model):
    _name = 'hhexpense.line'
    _inherit = ['mail.thread']

    # _order = "create_date desc, batch_number desc"
    _rec_name = 'expense_line_name'

    expense_line_name = fields.Char(string="Description", states={'draft': [('readonly', False)], 'rejected': [('readonly', False)]}, required=True, readonly=True)
    expense_line_cost = fields.Float(string='Amount', states={'draft': [('readonly', False)], 'rejected': [('readonly', False)]}, readonly=True)
    expense_line_date = fields.Date(string="Expense Date", states={'draft': [('readonly', False)], 'rejected': [('readonly', False)]}, required=True, readonly=True)
    expense_line_belongs_to_employee = fields.Char(string="Belongs to", compute='_compute_expense_line_belongs_to_employee', store=True)
    confirm_item_invoice = fields.Selection([(1, 'YES'), (0, 'NO')], string='Receipt', states={'draft': [('readonly', False)], 'rejected': [('readonly', False)]}, readonly=True, required=True, store=True)
    state = fields.Char(string="Status", compute="_compute_state", store=True)
    state_display_name = fields.Char(string="Status", compute="_compute_state_display_name", store=True)
    employee_name = fields.Char(related="expense_id.employee_name", store=True)
    expense_id = fields.Many2one('hhexpense.hhexpense', ondelete='cascade')
    expense_num_copy = fields.Char(related='expense_id.expense_num', store=True)
    payment_mode = fields.Selection([
        ("own_account", "Employee (to reimburse)"),
        ("company_account", "Company")
    ], default='own_account',
        states={'done': [('readonly', True)], 'post': [('readonly', True)], 'submitted': [('readonly', True)]}, string="Payment By")
    accounting_date = fields.Date(string="Date")
    company_id = fields.Many2one('res.company', string='Company', readonly=True, states={'submit': [('readonly', False)]}, default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=False, states={'submit': [('readonly', False)]}, default=lambda self: self.env.user.company_id.currency_id)
    account_id = fields.Many2one('account.account', string='Account',
                                 states={'posted': [('readonly', True)], 'done': [('readonly', True)]},
                                 default=lambda self: self.env['ir.property'].get('property_account_expense_categ_id',
                                                                                  'product.category'),
                                 help="An expense account is expected")
    product_id = fields.Many2one('product.product', string='Product', readonly=True,
                                 states={'draft': [('readonly', False)], 'refused': [('readonly', False)]},
                                 domain=[('can_be_hhexpensed', '=', True)], required=True)
    date = fields.Date(readonly=True, states={'draft': [('readonly', False)], 'refused': [('readonly', False)]}, default=fields.Date.context_today, string="Date")
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, readonly=True, states={'draft': [('readonly', False)], 'refused': [('readonly', False)]}, default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1))
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', states={'posted': [('readonly', True)], 'done': [('readonly', True)]}, oldname='analytic_account')
    tax_ids = fields.Many2many('account.tax', 'hhexpense_tax', 'hhexpense_expense_id', 'tax_id', string='Taxes', states={'done': [('readonly', True)], 'posted': [('readonly', True)]})
    unit_amount = fields.Float(string='Unit Price', readonly=True, required=True,
                               states={'draft': [('readonly', False)], 'refused': [('readonly', False)]},
                               digits=dp.get_precision('Product Price'), default=1)
    quantity = fields.Float(required=True, readonly=True,
                            states={'draft': [('readonly', False)], 'refused': [('readonly', False)]},
                            digits=dp.get_precision('Product Unit of Measure'), related='expense_line_cost')
    product_uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=True, readonly=True, states={'draft': [('readonly', False)], 'refused': [('readonly', False)]}, default=lambda self: self.env['product.uom'].search([], limit=1, order='id'))

    # ---------------------------------------------- Define methods here -----------------------------------------------
    @api.depends('expense_id.state')
    def _compute_state(self):
        for expense in self:
            if expense.expense_id.state == "draft":
                expense.state = "draft"
            elif expense.expense_id.state == "submitted":
                expense.state = "submitted"
            elif expense.expense_id.state == "approved":
                expense.state = "approved"
            elif expense.expense_id.state == "posted":
                expense.state = "posted"
            elif expense.expense_id.state == "rejected":
                expense.state = 'rejected'
            else:
                expense.state = "done"

    @api.depends('state')
    def _compute_state_display_name(self):
        for expense in self:
            if expense.state == "draft":
                expense.state_display_name = "Draft"
            elif expense.state == "submitted":
                expense.state_display_name = "Submitted"
            elif expense.state == "approved":
                expense.state_display_name = "Approved"
            elif expense.state == "posted":
                expense.state_display_name = "Posted"
            else:
                expense.state_display_name = "Rejected"

    @api.depends('expense_id.claim_as_agent', 'expense_id.agent_reimb_id')  # recompute if any of these changed
    def _compute_expense_line_belongs_to_employee(self):
        for rec in self:
            if rec.expense_id.claim_as_agent:
                rec.expense_line_belongs_to_employee = rec.expense_id.agent_reimb_id.name.name
            else:
                rec.expense_line_belongs_to_employee = rec.expense_id.employee_name

    @api.multi
    @api.depends('expense_line_cost', 'exchange_rate')
    def _compute_after_exchange_money(self):
        for rec in self:
            # Use "exchange_rate" rather than "expense_line_currency.exchange_rate" to do calculation can void "HKD RMB" if condition
            rec.expense_line_calculate = rec.expense_line_cost * rec.exchange_rate

    @api.onchange('expense_line_date')
    def _onchange_check_expense_date(self):
        if self.expense_line_date:
            user_input = str(self.expense_line_date)
            # Remove all special characters, punctuation and spaces from string then read it as integer
            user_input_int = int(''.join(char for char in user_input if char.isalnum()))
            today = int(datetime.datetime.now().strftime('%Y%m%d'))
            if user_input_int > today:
                self.expense_line_date = 0
                today_date = datetime.datetime.now().strftime('%Y-%m-%d')
                return {
                    'warning': {
                        'title': "Incorrect input",
                        'message': "Expense date can't be later than today("
                                   + str(today_date)
                                   + "), Please select again",
                    }
                }

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if not self.expense_line_name:
                self.expense_line_name = self.product_id.display_name or ''
            self.unit_amount = self.product_id.price_compute('standard_price')[self.product_id.id]
            self.product_uom_id = self.product_id.uom_id
            self.tax_ids = self.product_id.supplier_taxes_id
            account = self.product_id.product_tmpl_id._get_product_accounts()['expense']
            if account:
                self.account_id = account

    @api.onchange('product_uom_id')
    def _onchange_product_uom_id(self):
        if self.product_id and self.product_uom_id.category_id != self.product_id.uom_id.category_id:
            raise UserError(
                _('Selected Unit of Measure does not belong to the same category as the product Unit of Measure'))

    @api.multi
    def _compute_expense_totals(self, company_currency, account_move_lines, move_date):
        '''
        internal method used for computation of total amount of an expense in the company currency and
        in the expense currency, given the account_move_lines that will be created. It also do some small
        transformations at these account_move_lines (for multi-currency purposes)

        :param account_move_lines: list of dict
        :rtype: tuple of 3 elements (a, b ,c)
            a: total in company currency
            b: total in hr.expense currency
            c: account_move_lines potentially modified
        '''
        self.ensure_one()
        total = 0.0
        total_currency = 0.0
        for line in account_move_lines:
            line['currency_id'] = False
            line['amount_currency'] = False
            if self.currency_id != company_currency:
                line['currency_id'] = self.currency_id.id
                line['amount_currency'] = line['price']
                line['price'] = self.currency_id.with_context(
                    date=move_date or fields.Date.context_today(self)).compute(line['price'], company_currency)
            total -= line['price']
            total_currency -= line['amount_currency'] or line['price']
        return total, total_currency, account_move_lines

    @api.multi
    def action_move_create(self):
        '''
        main function that is called when trying to create the accounting entries related to an expense
        '''
        move_group_by_sheet = {}
        for expense in self:
            journal = expense.expense_id.bank_journal_id if expense.payment_mode == 'company_account' else expense.expense_id.journal_id
            # create the move that will contain the accounting entries
            acc_date = expense.expense_id.accounting_date or expense.date
            if not expense.expense_id.id in move_group_by_sheet:
                move = self.env['account.move'].create({
                    'journal_id': journal.id,
                    'company_id': self.env.user.company_id.id,
                    'date': acc_date,
                    'ref': expense.expense_id.name,
                    # force the name to the default value, to avoid an eventual 'default_name' in the context
                    # to set it to '' which cause no number to be given to the account.move when posted.
                    'name': '/',
                })
                move_group_by_sheet[expense.expense_id.id] = move
            else:
                move = move_group_by_sheet[expense.expense_id.id]
            company_currency = expense.company_id.currency_id
            diff_currency_p = expense.currency_id != company_currency
            # one account.move.line per expense (+taxes..)
            move_lines = expense._move_line_get()

            # create one more move line, a counterline for the total on payable account
            payment_id = False
            total, total_currency, move_lines = expense._compute_expense_totals(company_currency, move_lines, acc_date)
            if expense.payment_mode == 'company_account':
                if not expense.expense_id.bank_journal_id.default_credit_account_id:
                    raise UserError(_("No credit account found for the %s journal, please configure one.") % (
                        expense.expense_id.bank_journal_id.name))
                emp_account = expense.expense_id.bank_journal_id.default_credit_account_id.id
                journal = expense.expense_id.bank_journal_id
                # create payment
                payment_methods = (
                                          total < 0) and journal.outbound_payment_method_ids or journal.inbound_payment_method_ids
                journal_currency = journal.currency_id or journal.company_id.currency_id
                payment = self.env['account.payment'].create({
                    'payment_method_id': payment_methods and payment_methods[0].id or False,
                    'payment_type': total < 0 and 'outbound' or 'inbound',
                    'partner_id': expense.employee_id.address_home_id.commercial_partner_id.id,
                    'partner_type': 'supplier',
                    'journal_id': journal.id,
                    'payment_date': expense.date,
                    'state': 'reconciled',
                    'currency_id': diff_currency_p and expense.currency_id.id or journal_currency.id,
                    'amount': diff_currency_p and abs(total_currency) or abs(total),
                    'name': expense.expense_line_name,
                })
                payment_id = payment.id
            else:
                if not expense.expense_id.employee_id.address_home_id:
                    raise UserError(_("No Home Address found for the employee %s, please configure one.") % (
                        expense.expense_id.employee_id.name))
                emp_account = expense.expense_id.employee_id.address_home_id.property_account_payable_id.id

            aml_name = expense.expense_id.employee_id.name + ': ' + expense.expense_line_name.split('\n')[0][:64]
            move_lines.append({
                'type': 'dest',
                'name': aml_name,
                'price': total,
                'account_id': emp_account,
                'date_maturity': acc_date,
                'amount_currency': diff_currency_p and total_currency or False,
                'currency_id': diff_currency_p and expense.currency_id.id or False,
                'payment_id': payment_id,
                'hhexpense_expense_id': expense.id,
            })

            # convert eml into an osv-valid format
            lines = [(0, 0, expense._prepare_move_line(x)) for x in move_lines]
            move.with_context(dont_create_taxes=True).write({'line_ids': lines})
            expense.expense_id.write({'account_move_id': move.id})
            if expense.payment_mode == 'company_account':
                expense.expense_id.paid_expense_sheets()
        for move in move_group_by_sheet.values():
            move.post()
        return True

    @api.multi
    def _move_line_get(self):
        account_move = []
        for expense in self:
            move_line = expense._prepare_move_line_value()
            account_move.append(move_line)

            # Calculate tax lines and adjust base line
            taxes = expense.tax_ids.with_context(round=True).compute_all(expense.unit_amount, expense.currency_id, expense.quantity, expense.product_id)
            account_move[-1]['price'] = taxes['total_excluded']
            account_move[-1]['tax_ids'] = [(6, 0, expense.tax_ids.ids)]
            for tax in taxes['taxes']:
                account_move.append({
                    'type': 'tax',
                    'name': tax['name'],
                    'price_unit': tax['amount'],
                    'quantity': 1,
                    'price': tax['amount'],
                    'account_id': tax['account_id'] or move_line['account_id'],
                    'tax_line_id': tax['id'],
                    'hhexpense_expense_id': expense.id,
                })
        return account_move

    @api.multi
    def _prepare_move_line_value(self):
        self.ensure_one()
        if self.account_id:
            account = self.account_id
        elif self.product_id:
            account = self.product_id.product_tmpl_id._get_product_accounts()['expense']
            if not account:
                raise UserError(
                    _("No Expense account found for the product %s (or for its category), please configure one.") % (self.product_id.name))
        else:
            a1 = self.env['ir.property'].with_context(force_company=self.company_id.id)
            account= a1.get('property_account_expense_categ_id', 'product.category')
            if not account:
                raise UserError(
                    _('Please configure Default Expense account for Product expense: `property_account_expense_categ_id`.'))
        aml_name = self.expense_id.employee_id.name + ': ' + self.expense_line_name.split('\n')[0][:64]
        move_line = {
            'type': 'src',
            'name': aml_name,
            'price_unit': self.unit_amount,
            'quantity': self.quantity,
            'price': self.expense_line_cost,
            'account_id': account.id,
            'product_id': self.product_id.id,
            'uom_id': self.product_uom_id.id,
            'analytic_account_id': self.analytic_account_id.id,
            'hhexpense_expense_id': self.id,
        }
        return move_line

    def _prepare_move_line(self, line):
        '''
        This function prepares move line of account.move related to an expense
        '''
        partner_id = self.employee_id.address_home_id.commercial_partner_id.id
        return {
            'date_maturity': line.get('date_maturity'),
            'partner_id': partner_id,
            'name': line['name'][:64],
            'debit': line['price'] > 0 and line['price'],
            'credit': line['price'] < 0 and - line['price'],
            'account_id': line['account_id'],
            'analytic_line_ids': line.get('analytic_line_ids'),
            'amount_currency': line['price'] > 0 and abs(line.get('amount_currency')) or - abs(line.get('amount_currency')),
            'currency_id': line.get('currency_id'),
            'tax_line_id': line.get('tax_line_id'),
            'tax_ids': line.get('tax_ids'),
            'quantity': line.get('quantity', 1.00),
            'product_id': line.get('product_id'),
            'product_uom_id': line.get('uom_id'),
            'analytic_account_id': line.get('analytic_account_id'),
            'payment_id': line.get('payment_id'),
            'hhexpense_expense_id': line.get('hhexpense_expense_id'),
        }
