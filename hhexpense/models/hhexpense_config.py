# -*- coding: utf-8 -*-
from odoo import models, fields


class HHExpenseAgentReimbursement(models.Model):
    _name = "hhexpense.agent.reimbursement"

    name = fields.Many2one('hr.employee', string='Delegator', help='The person who cannot claim expense by themselves',
                           required=True)
    agent = fields.Many2one('hr.employee', string='Agent', help='The representative that has authorized to do claiming process',
                            required=True)  # Authorized Person / Representative / Agent


