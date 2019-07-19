# -*- coding: utf-8 -*-
from odoo import http

# class ExpenseNew(http.Controller):
#     @http.route('/expense_new/expense_new/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/expense_new/expense_new/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('expense_new.listing', {
#             'root': '/expense_new/expense_new',
#             'objects': http.request.env['expense_new.expense_new'].search([]),
#         })

#     @http.route('/expense_new/expense_new/objects/<model("expense_new.expense_new"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('expense_new.object', {
#             'object': obj
#         })