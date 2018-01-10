# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _, tools
from openerp.osv import fields as old_fields
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from werkzeug import url_encode


class account_invoice_extension(models.Model):
    _inherit = 'account.invoice'
    
    manager_id = fields.Many2one(related="user_id.partner_id.manager_id", store=True)
    carrier_id = fields.Many2one("delivery.carrier", string="Delivery Method", help="Fill this field if you plan to invoice the shipping based on picking.")
    delivery_price = fields.Float(string='Estimated Delivery Price', compute=False)
    amount_delivery = fields.Monetary(string='Transportation & Installation Charges', store=True, readonly=True,  track_visibility='always')
    enquiry_type = fields.Selection([('private', 'Private'),('corporate', 'Corporate'),('dealer', 'Dealer')], string='Type of Enquiry')

    @api.model
    def send_mail(self):
        account_invoice_ids = self.search([])
        template_obj = self.env['mail.template']
        ir_model_data = self.env['ir.model.data']
        template_id= self.env.ref('pro_crm.due_date_reminder_template')
        for account_invoice_id in account_invoice_ids:
            if account_invoice_id.date_due:
                date = str(account_invoice_id.date_due).split( )[0].split('-')[2]
                current_date = datetime.now()
                new_current_date = str(current_date).split( )[0].split('-')[2]
                if int(date) - int(new_current_date) == 1:
                    res = template_id.send_mail(account_invoice_id.id, raise_exception=False)
    
    
    @api.model
    def invoice_delivery_charge_get(self):
        res = []
        account_id = self.env['account.account'].search([('internal_type','=','other'),('name','ilike','Transportation')])[0]
        move_delivery_charge_dict = {
            'type': 'src',
            'name': 'Transportation & Installation Charges',
            'price': self.amount_delivery,
            'account_id': account_id.id,
            'invoice_id': self.id,
        }
        res.append(move_delivery_charge_dict)
        return res
    
    
    @api.multi
    def action_move_create(self):
        """ Creates invoice related analytics and financial move lines """
        account_move = self.env['account.move']

        for inv in self:
            if not inv.journal_id.sequence_id:
                raise UserError(_('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line_ids:
                raise UserError(_('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)

            if not inv.date_invoice:
                inv.with_context(ctx).write({'date_invoice': fields.Date.context_today(self)})
            date_invoice = inv.date_invoice
            company_currency = inv.company_id.currency_id

            # create move lines (one per invoice line + eventual taxes and analytic lines)
            iml = inv.invoice_line_move_line_get()
            iml += inv.tax_line_move_line_get()
            iml += inv.invoice_delivery_charge_get()

            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, iml)

            name = inv.name or '/'
            if inv.payment_term_id:
                totlines = inv.with_context(ctx).payment_term_id.with_context(currency_id=inv.currency_id.id).compute(total, date_invoice)[0]
                res_amount_currency = total_currency
                ctx['date'] = date_invoice
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'invoice_id': inv.id
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'invoice_id': inv.id
                })
            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
            line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
            line = inv.group_lines(iml, line)

            journal = inv.journal_id.with_context(ctx)
            line = inv.finalize_invoice_move_lines(line)

            date = inv.date or date_invoice
            move_vals = {
                'ref': inv.reference,
                'line_ids': line,
                'journal_id': journal.id,
                'date': date,
                'narration': inv.comment,
            }
            ctx['company_id'] = inv.company_id.id
            ctx['dont_create_taxes'] = True
            ctx['invoice'] = inv
            ctx_nolang = ctx.copy()
            ctx_nolang.pop('lang', None)
            move = account_move.with_context(ctx_nolang).create(move_vals)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move.post()
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'date': date,
                'move_name': move.name,
            }
            inv.with_context(ctx).write(vals)
        return True
    
    
    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'currency_id', 'company_id')
    def _compute_amount(self):
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        self.amount_tax = sum(line.amount for line in self.tax_line_ids)
        print "AAAAAAAAAAAAAAAAAAAAAAA" ,  self.amount_delivery
        self.amount_total = self.amount_untaxed + self.amount_tax + self.amount_delivery or 0.0
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.currency_id != self.company_id.currency_id:
            amount_total_company_signed = self.currency_id.compute(self.amount_total, self.company_id.currency_id)
            amount_untaxed_signed = self.currency_id.compute(self.amount_untaxed, self.company_id.currency_id)
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign
