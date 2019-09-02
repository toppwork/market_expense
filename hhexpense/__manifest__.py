# -*- coding: utf-8 -*-
{
    'name': "E-Expense",
    'sequence': 1,
    'summary': """
        A simple, easy to use online expense tool helping employees and management to efficiently
            process expenditures within an intuitive and robust system.""",
    'description': """
        A simple, easy to use online expense tool helping employees and management to efficiently
            process expenditures within an intuitive and robust system.
    """,
    'author': "Toppwork",
    'license': 'LGPL-3',
    'website': "http://www.toppwork.com",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Human Resources',
    'images': ['images/screenshot.jpg'],
    'version': '1.0',
    'depends': ['base', 'mail', 'hr', 'account_accountant', 'web_tour', 'l10n_generic_coa'],
    'data': [
        'wizard/hhexpense_reject_reason_views.xml',
        'wizard/hhexpense_register_payment.xml',

        'security/hhexpense_security.xml',  # You have to add security.xml file before csv file to avoid potential error
        'security/ir.model.access.csv',

        'views/template.xml',
        # 'views/hhexpense_attachment.xml',

        'views/hhexpense.xml',
        'views/hhexpense_config.xml',
        'views/hhexpense_product.xml',

        'views/hhexpense_email_templates.xml',
        'report/hhexpense_report.xml',

        # 'data/hhexpense_data.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
}