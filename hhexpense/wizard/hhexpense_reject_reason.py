from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HHExpenseRejectWizard(models.TransientModel):
    _name = "hhexpense.reject.wizard"

    manager_reject_reason = fields.Char(string='Reject Reason')
    expense_id = fields.Many2one('hhexpense.hhexpense')

    @api.model
    def default_get(self, fields):
        res = super(HHExpenseRejectWizard, self).default_get(fields)

        active_model = self.env.context.get('active_model')
        # Use 'active_id'(a int) if it is single record (form view)
        # (ref: https://www.odoo.com/fr_FR/forum/aide-1/question/set-default-value-in-wizard-from-context-137612)
        if active_model == 'hhexpense.hhexpense':
            active_id = self.env.context.get('active_id')  # current record id
        else:
            expense_line_id = self.env.context.get('active_id')  # current record id
            active_id = self.env['hhexpense.line'].search([('id', '=', expense_line_id)]).expense_id.id
        reject_model = self.env.context.get('hhexpense_reject_model')
        if reject_model == 'hhexpense.hhexpense':
            res.update({
                'expense_id': active_id
            })
        return res

    @api.multi
    def reject_expense(self):
        self.ensure_one()
        if self.env.user.has_group('hhexpense.group_hhexpense_manager'):
            if not self.manager_reject_reason:
                raise UserError(_("Reject reason is required"))
            else:
                if self.expense_id:
                    # Pass reject reason to "reject_expense" method in hhexpense model
                    self.expense_id.reject_expense(self.manager_reject_reason)
                return {'type': 'ir.actions.act_window_close'}
