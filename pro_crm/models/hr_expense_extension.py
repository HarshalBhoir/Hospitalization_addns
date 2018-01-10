# -*- coding: utf-8 -*-
from openerp.exceptions import UserError, MissingError, ValidationError
from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _, tools
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from werkzeug import url_encode


class hr_expense_expense_extension(models.Model):
    _inherit = 'hr.expense.expense'
    
    zone = fields.Many2one(related="employee_id.user_id.partner_id.zone" , string="Zone", placeholder="Zone", store= True)
    advance_amount = fields.Float(string='Advance')
    amount_advance = fields.Monetary(string='Advance', store=True , compute='_compute_amount' , readonly=True,  track_visibility='always')

    @api.depends('line_ids.quantity', 'line_ids.unit_amount', 'line_ids.tax_ids', 'currency_id', 'state', 'advance_amount')
    def _compute_amount(self):
        untaxed_amount = 0
        total_amount = 0
        amount_advance = 0
        for record in self:
            for expense in record.line_ids:
                if expense.state not in ('cancel'):
                    untaxed_amount += expense.unit_amount * expense.quantity
                    amount_advance = record.advance_amount
                    taxes = expense.tax_ids.compute_all(expense.unit_amount, expense.currency_id, expense.quantity, expense.product_id, expense.employee_id.user_id.partner_id)
                    total_amount += taxes.get('total_included')
        self.untaxed_amount = untaxed_amount
        self.amount_advance = amount_advance
        self.total_amount = total_amount - amount_advance
    
class hr_expense_extension(models.Model):
    _inherit = 'hr.expense'
    
    zone = fields.Many2one(related="employee_id.user_id.partner_id.zone" , string="Zone", placeholder="Zone", store= True)