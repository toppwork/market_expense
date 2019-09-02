# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api, _, registry

# remove 'hhexpense.debit.category' --- HHExpenseDebitCategory
# remove 'hhexpense.convert.deptoexp' --- HHExpenseConvertDepartmentToExpenseType
# remove 'hhexpense.currency.rate' --- HHExpenseGetCurrencyExchangeRate
# remove 'hhexpense.holiday.date' --- HHExpenseHolidayDate
# remove 'hhexpense.team' --- HHExpenseTeam
# remove 'hhexpense.convert.deptoexp' --- HHExpenseConvertDepartmentToExpenseType
# remove 'hhexpense.extra.emp.info' --- HHExpenseExtraEmpInfo
# remove 'hhexpense.payment.method' --- HHExpensePaymentMethod
# remove 'hhexpense.extra.company.info' --- HHExpenseExtraCompanyInfo

#
# # class HHExpenseExpenseCategory(models.Model):  # Corresponds to odoo's expense category info (product.product)
# #     _name = 'hhexpense.expense.category'
# #
# #     category = fields.Char()
# #     ref_code = fields.Char()
# #     expense_line_id = fields.One2many('hhexpense.line', inverse_name='expense_cate_id')
# #
# #     # -------------------------------------------- Define methods here -------------------------------------------------
# #     @api.multi
# #     def name_get(self):
# #         res = []
# #         for rec in self:
# #             res.append((rec.id, "%s" % rec.category))
# #         return res
# #
# #     @api.model
# #     def name_search(self, name='', args=None, operator='ilike', limit=100):
# #         """ name_search(name='', args=None, operator='ilike', limit=100) -> records
# #         Search for records that have a display name matching the given
# #         ``name`` pattern when compared with the given ``operator``, while also
# #         matching the optional search domain (``args``).
# #         This is used for example to provide suggestions based on a partial
# #         value for a relational field. Sometimes be seen as the inverse
# #         function of :meth:`~.name_get`, but it is not guaranteed to be.
# #         This method is equivalent to calling :meth:`~.search` with a search
# #         domain based on ``display_name`` and then :meth:`~.name_get` on the
# #         result of the search.
# #         :param str name: the name pattern to match
# #         :param list args: optional search domain (see :meth:`~.search` for
# #                           syntax), specifying further restrictions
# #         :param str operator: domain operator for matching ``name``, such as
# #                              ``'like'`` or ``'='``.
# #         :param int limit: optional max number of records to return
# #         :rtype: list
# #         :return: list of pairs ``(id, text_repr)`` for all matching records.
# #         """
# #         if not args:
# #             args = []
# #         if name:
# #             positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
# #             categories = self.env['hhexpense.expense.category']
# #             if operator in positive_operators:
# #                 categories = self.search([('category', '=', name)] + args, limit=limit)
# #                 # print("did you running this one? so what is category now? ", categories)
# #             if not categories and operator not in expression.NEGATIVE_TERM_OPERATORS:
# #                 categories = self.search(args + [('category', operator, name)], limit=limit)
# #                 # print("this is operator: ", operator)
# #                 # print("you are running this one, what about now? category is....? ", categories)
# #                 # print("OK, fine, give me your args value now. ", args)
# #             elif not categories and operator in expression.NEGATIVE_TERM_OPERATORS:
# #                 categories = self.search(args + [('category', operator, name)], limit=limit)
# #                 # print("you are running that one")
# #             if not categories and operator in positive_operators:
# #                 ptrn = re.compile('(\[(.*?)\])')
# #                 res = ptrn.search(name)
# #                 # print("oops")
# #                 if res:
# #                     categories = self.search([('category', '=', res.group(2))] + args, limit=limit)
# #                     # print("You are not supposed to see this message")
# #         else:
# #             categories = self.search(args, limit=limit)
# #             # print("Didn't detect any input/change yet")
# #         return categories.name_get()


class HHExpenseAgentReimbursement(models.Model):
    _name = "hhexpense.agent.reimbursement"

    name = fields.Many2one('hr.employee', string='Delegator', help='The person who cannot claim expense by themselves',
                           required=True)
    agent = fields.Many2one('hr.employee', string='Agent', help='The representative that has authorized to do claiming process',
                            required=True)  # Authorized Person / Representative / Agent


