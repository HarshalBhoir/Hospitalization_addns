# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _, tools
from openerp.osv import fields as old_fields
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from werkzeug import url_encode
import lxml
from lxml import etree
from openerp.osv.orm import setup_modifiers

class sale_order_extension(models.Model):
    _inherit = 'sale.order'
    
    sale_type = fields.Selection([('dealer','Dealer'),('direct','Direct'),('tender','Tender')], string="Type of Sale", store=True)
    zone = fields.Many2one('crm.configuration', string="Zone")
    cust_faculty = fields.Many2one('customer.faculty', string="Customer Faculty")
    hospital_name = fields.Char(string="Hospital Name")
    pan_no = fields.Char(string="PAN No.", store= True)
    c_form = fields.Selection([('yes','Yes'),('no','No')], string="C Form Applicable?", default='no')
    manager_id = fields.Many2one(related="user_id.partner_id.manager_id", store=True)
    delivery_term = fields.Many2one('delivery.term', string="Delivery Term")
    delivery_price = fields.Float(string='Estimated Delivery Price', compute=False)
    other_term = fields.Char(string="Other Payment Term")
    payment_term_name = fields.Char(related="payment_term_id.name", string="Payment term name")
    amount_delivery = fields.Monetary(string='Transportation & Installation Charges', store=True , compute='_amount_all' , readonly=True,  track_visibility='always')
    enquiry_type = fields.Selection([('private', 'Private'),('corporate', 'Corporate'),('dealer', 'Dealer')], string='Type of Enquiry')
    dealer_name = fields.Many2one('res.partner', string="Dealer Name")
    
    @api.multi
    def delivery_set(self):

        for order in self:
            carrier = order.carrier_id
            if carrier:
                if order.state not in ('draft', 'sent','sale'):
                    raise UserError(_('The order state have to be draft to add delivery lines.'))
    
                if carrier.delivery_type not in ['fixed', 'base_on_rule']:
                    price_unit = order.carrier_id.get_shipping_price_from_so(order)[0]
                else:
                    carrier = order.carrier_id.verify_carrier(order.partner_shipping_id)
                    if not carrier:
                        raise UserError(_('No carrier matching.'))
                    order.amount_delivery = order.delivery_price
            else:
                raise UserError(_('No carrier set for this order.'))
            
    @api.depends('order_line.price_total','delivery_price')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        
        super(sale_order_extension, self)._amount_all()
        for res in self:
            amount_delivery = 0.0
            if res.carrier_id:
                amount_delivery = res.delivery_price
            
            res.update({
                'amount_delivery': res.pricelist_id.currency_id.round(amount_delivery),
                'amount_total': res.amount_untaxed + res.amount_tax + amount_delivery,
            })

    @api.multi
    def action_confirm(self):
        result = super(sale_order_extension, self).action_confirm()
        # template_obj = self.env['mail.template']
        # ir_model_data = self.env['ir.model.data']
        template_id= self.env.ref('pro_crm.sale_order_confirm_template')
        res = template_id.send_mail(self.id, raise_exception=False)
        if self.picking_ids:
            for record in self.picking_ids:
                record.sale_type = self.sale_type
                record.deal_done_by = self.user_id
                record.delivery_term = self.delivery_term
                record.enquiry = self.source_id
                record.cust_name = self.partner_id
                record.pricelist_id = self.pricelist_id
                record.currency_id = self.currency_id
                record.cust_pan = self.pan_no
                record.cust_hosp_name = self.hospital_name
                # record.amount_untaxed = self.amount_untaxed
                # record.amount_tax = self.amount_tax
                record.amount_delivery = self.amount_delivery
                # record.amount_total = self.amount_total
                record.zone = self.zone
                record.enquiry_type = self.enquiry_type
        if not self.pan_no:
            raise UserError(_("Kindly Fill the PAN No."))
        elif not len(self.pan_no) == 10:
            raise UserError(_("Kindly Fill Proper PAN No."))
        
        
        
        #--------------------Pricing From Sale Order to Stock Picking--------------------------------------
        for record_po in self:
            for rec_po in record_po.order_line:
                for record in record_po.picking_ids:
                    for rec in record.pack_operation_product_ids:
                        if rec.product_id.id == rec_po.product_id.id:
                            rec.price_unit = rec_po.price_unit
                            rec.tax_id = rec_po.tax_id
                            rec.discount = rec_po.discount
                            rec.price_subtotal = rec_po.price_subtotal
                            rec.description = rec_po.name
        #----------------------------------------------------------
        return result
    
    
    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        Update the following fields when the partner is changed:
        - Pricelist
        - Payment term
        - Invoice address
        - Delivery address
        """
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                'payment_term_id': False,
                'fiscal_position_id': False,
            })
            return

        addr = self.partner_id.address_get(['delivery', 'invoice'])
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        }
        if self.env.user.company_id.sale_note:
            values['note'] = self.with_context(lang=self.partner_id.lang).env.user.company_id.sale_note

        # if self.partner_id.user_id:
        #     values['user_id'] = self.partner_id.user_id.id
        if self.partner_id.team_id:
            values['team_id'] = self.partner_id.team_id.id
        self.update(values)
        
        
    @api.multi
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        journal_id = self.env['account.invoice'].default_get(['journal_id'])['journal_id']
        if not journal_id:
            raise UserError(_('Please define an accounting sale journal for this company.'))
        invoice_vals = {
            'name': self.client_order_ref or '',
            'origin': self.name,
            'type': 'out_invoice',
            'reference': self.client_order_ref or self.name,
            'account_id': self.partner_invoice_id.property_account_receivable_id.id,
            'partner_id': self.partner_invoice_id.id,
            'journal_id': journal_id,
            'currency_id': self.pricelist_id.currency_id.id,
            'comment': self.note,
            'payment_term_id': self.payment_term_id.id,
            'fiscal_position_id': self.fiscal_position_id.id or self.partner_invoice_id.property_account_position_id.id,
            'company_id': self.company_id.id,
            'user_id': self.user_id and self.user_id.id,
            'team_id': self.team_id.id,
            'carrier_id': self.carrier_id.id,
            'delivery_price': self.delivery_price,
            'amount_delivery': self.amount_delivery,
            'enquiry_type': self.enquiry_type,
        }
        return invoice_vals
    

class sale_order__line_extension(models.Model):
    _inherit = 'sale.order.line'

    zone = fields.Many2one(related="order_id.zone",  string="Zone",store=True)  
    # sale_type = fields.Selection([('dealer','Dealer'),('direct','Direct'),('tender','Tender')], related="order_id.sale_type", string="Type of Sale")
    
class stock_picking_extension(models.Model):
    _inherit = 'stock.picking'
    
    
    @api.depends('pack_operation_product_ids.price_total','amount_delivery')
    def _amount_all(self):
        """
        Compute the total amounts of the Stock Picking.
        """
        print "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
        for record in self:
            amount_untaxed = amount_tax = 0.0
            for line in record.pack_operation_product_ids:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            record.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax + record.amount_delivery,
            })
    
    
    def _state_get(self, cr, uid, ids, field_name, arg, context=None):
        '''The state of a picking depends on the state of its related stock.move
            draft: the picking has no line or any one of the lines is draft
            done, draft, cancel: all lines are done / draft / cancel
            confirmed, waiting, assigned, partially_available depends on move_type (all at once or partial)
        '''
        # res = super(stock_picking_extension, self)._state_get(cr, uid, ids, field_name, arg, context)
        res = {}
        print "SSSSSSSSSSSSSSSSSSSSSSSs"
        for pick in self.browse(cr, uid, ids, context=context):
            if not pick.move_lines:
                res[pick.id] = pick.launch_pack_operations and 'assigned' or 'draft'
                continue
            if any([x.state == 'draft' for x in pick.move_lines]):
                res[pick.id] = 'draft'
                continue
            if all([x.state == 'cancel' for x in pick.move_lines]):
                res[pick.id] = 'cancel'
                continue
            if all([x.state in ('cancel', 'done') for x in pick.move_lines]):
                res[pick.id] = 'done'
                continue
            if pick.approval_state == 'approved':
                res[pick.id] = 'ceo_approved'
                continue
            elif pick.approval_state == 'rejected':
                res[pick.id] = 'ceo_rejected'
                continue

            order = {'confirmed': 0, 'waiting': 1, 'assigned': 2}
            order_inv = {0: 'confirmed', 1: 'waiting', 2: 'assigned'}
            lst = [order[x.state] for x in pick.move_lines if x.state not in ('cancel', 'done')]
            if pick.move_type == 'one':
                res[pick.id] = order_inv[min(lst)]
            else:
                #we are in the case of partial delivery, so if all move are assigned, picking
                #should be assign too, else if one of the move is assigned, or partially available, picking should be
                #in partially available state, otherwise, picking is in waiting or confirmed state
                res[pick.id] = order_inv[max(lst)]
                if not all(x == 2 for x in lst):
                    if any(x == 2 for x in lst):
                        res[pick.id] = 'partially_available'
                    else:
                        #if all moves aren't assigned, check if we have one product partially available
                        for move in pick.move_lines:
                            if move.partially_available:
                                res[pick.id] = 'partially_available'
                                break
        return res
    
    def _get_pickings(self, cr, uid, ids, context=None):
        res = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.picking_id:
                res.add(move.picking_id.id)
        return list(res)
    
    @api.multi
    def button_dummy(self):
        return True
    
    
    @api.model
    def create(self, vals):
        zone_code = ''
        print "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@" ,self, vals, vals.get('origin')
        
        seq_srch=self.env['ir.sequence'].search([('code','=','sale.indent')])
        # print error
        if seq_srch:
            print "sdaaaaaaaaaaaaaaaaaaaaaaaaa" , vals.get('zone')
            sale_order_id = self.env['sale.order'].search([('name','=',vals.get('origin'))])
            # zone = self.env['crm.configuration'].search([('id','=',vals['zone'])])
            zone_code = sale_order_id.zone.zone_code
        year = datetime.today().year
        month = datetime.today().month
        vals['name'] = self.env['ir.sequence'].next_by_code('sale.indent')
        
        if month <= 3:
            pre_year = year - 1
            pre_year_1 = str(year)[2:]
            name = "SALE" + "/" + zone_code + "/" + vals['name'] + "/" + str(pre_year) + '-' + str(pre_year_1)
        if month > 3:
            next_year = year + 1
            next_year_2 = str(next_year)[2:]
            name = "SALE" + "/" + zone_code + "/" + vals['name'] + "/" + str(year) + '-' + str(next_year_2) 
        print "LLLLLLLLLLLLLLLLLLLLLLLL" , name
        # # print error
        vals['name'] = name
        
        # vals['ind_no'] = self.env['ir.sequence'].next_by_code('demo.indent')
        result = super(stock_picking_extension, self).create(vals)
        return result
    
    
    sale_type = fields.Selection([('dealer','Dealer'),('direct','Direct'),('tender','Tender')], string="Type of Sale")
    enquiry_type = fields.Selection([('private', 'Private'),('corporate', 'Corporate'),('dealer', 'Dealer')], string='Type of Enquiry')
    
    deal_done_by = fields.Many2one('res.users', string="Deal done by")
    enquiry =fields.Many2one('utm.source', string="Enquiry Through")
    dealer_name = fields.Many2one('res.partner', string="Dealer Name")
    dealer_street = fields.Char(string="Address", related="dealer_name.street")
    dealer_street2 = fields.Char(string= " ", related="dealer_name.street2")
    dealer_city = fields.Char(string=" ", related="dealer_name.city")
    dealer_state_id = fields.Many2one('res.country.state', string=" ", related="dealer_name.state_id")
    dealer_zip1 = fields.Char(string=" ", related="dealer_name.zip")
    dealer_country_id = fields.Many2one('res.country', string=" ", related="dealer_name.country_id")
    dealer_pan = fields.Char(string="PAN No.", related="dealer_name.pan_no")
    dealer_tin = fields.Char(string="TIN No.", related="dealer_name.tin_no")
    dealer_phone = fields.Char(string="Phone", related="dealer_name.phone")
    dealer_mobile = fields.Char(string="Mobile", related="dealer_name.mobile")
    dealer_email = fields.Char(string="Email", related="dealer_name.email")
    cust_name = fields.Many2one('res.partner',string="Customer Name")
    cust_hosp_name = fields.Char(string="Hospital Name", related="cust_name.hosp_name")
    # dealer_cust_street = fields.Char(string="Address")
    # dealer_cust_street2 = fields.Char(string= " ")
    # dealer_cust_city = fields.Char(string=" ")
    # dealer_cust_state_id = fields.Many2one('res.country.state', string=" ")
    # dealer_cust_zip1 = fields.Char(string=" ")
    # dealer_cust_country_id = fields.Many2one('res.country', string=" ")
    cust_pan = fields.Char(string="PAN No.", related="cust_name.pan_no")
    cust_tin = fields.Char(string="TIN No.", related="cust_name.tin_no")
    # dealer_cust_contact_no = fields.Char(string="Contact No.")
    # dealer_cust_email = fields.Char(string="Email")s
    cust_faculty = fields.Many2one('customer.faculty', string="Customer Faculty")
    cust_warranty = fields.Char(string="Warranty")
    # dealer_model = fields.Many2one('product.category', string="Model")
    # dealer_qty = fields.Integer(string="Qty")
    # dealer_accessories = fields.Many2one('product.product', string="Accessories")
    # dealer_instruments = fields.Many2one('product.product', string="Instrument")
    # dealer_requirement = fields.Char(string="As per Requirement")
    # dealer_spl_instructions = fields.Char(string="Special Instruction")
    special_instruction = fields.Text(string="Dispatch Details")
    
    tender_name = fields.Char(string="Tender Name")
    tender_no = fields.Char(string="Tender No.")
    tender_location = fields.Char(string="Tender Location")
    tender_authority = fields.Char(string="Authority")
    tender_quote_by = fields.Char(string="Tender Quote By")
    tender_comp_name = fields.Char(string="Company Name")
    tender_dealer_name = fields.Many2one('res.partner', string="Dealer Name")
    tender_contact_name = fields.Char(string="Contact Person Name")
    tender_email = fields.Char(string="Email")
    tender_designation = fields.Char(string="Designation of person")
    tender_website = fields.Char(string="Website")
    tender_mobile_no = fields.Char(string="Mobile No.")
    tender_landline_no = fields.Char(string="Landline No.")
    tender_emd = fields.Char(string="EMD Details")
    tender_proof = fields.Char(string="Proof")
    c_form = fields.Selection([('yes','Yes'),('no','No')], string="C Form")
    road_permit_no = fields.Char(string="Road Permit No.")
    date = fields.Date(string="Date")
    due_date = fields.Date(string="Due Date")
    zone = fields.Many2one('crm.configuration', string="Zone", placeholder="Zone")
    approval_state = fields.Selection([('approved','Approved'),('rejected','Rejected')], string="CEO Approval State")
    manager_id = fields.Many2one(related="deal_done_by.partner_id.manager_id", store=True)
    delivery_term = fields.Many2one('delivery.term', string="Delivery Term")
    expected_date = fields.Date(string="Expected Date")
    approx_date = fields.Date(string="Approximate Date")
    dispatch = fields.Many2one('dispatch.through', string="Dispatch through")
    
    delivery_street = fields.Char(string="Address")
    delivery_street2 = fields.Char(string= " ")
    delivery_city = fields.Char(string=" ")
    delivery_state_id = fields.Many2one('res.country.state', string=" ")
    delivery_zip1 = fields.Char(string=" ")
    delivery_country_id = fields.Many2one('res.country', string=" ")
    
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', help="Pricelist for current sales order.")
    currency_id = fields.Many2one("res.currency", related='pricelist_id.currency_id', string="Currency")
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_delivery = fields.Monetary(string='Transportation & Installation Charges', store=True , track_visibility='always')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    
    
    _columns = {
        'state': old_fields.function(_state_get, type="selection", copy=False,
            store={
                'stock.picking': (lambda self, cr, uid, ids, ctx: ids, ['approval_state','move_type','launch_pack_operations'], 20),
                'stock.move': (_get_pickings, ['state', 'picking_id', 'partially_available'], 20)},
            selection=[
                ('draft', 'Draft'),
                ('cancel', 'Cancelled'),
                ('waiting', 'Waiting Another Operation'),
                ('confirmed', 'Waiting Availability'),
                ('partially_available', 'Partially Available'),
                ('assigned', 'Available'),
                ('ceo_approved', 'CEO Approved'),
                ('ceo_rejected', 'CEO Rejected'),
                ('done', 'Done'),
                ], string='Status', readonly=True, select=True, track_visibility='onchange',
            help="""
                * Draft: not confirmed yet and will not be scheduled until confirmed\n
                * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n
                * Waiting Availability: still waiting for the availability of products\n
                * Partially Available: some products are available and reserved\n
                * Ready to Transfer: products reserved, simply waiting for confirmation.\n
                * Transferred: has been processed, can't be modified or cancelled anymore\n
                * Cancelled: has been cancelled, can't be confirmed anymore"""
        ),
    }
    
    
    @api.multi
    @api.onchange('cust_name')
    def onchange_cust_name(self):
        """
        Update the following fields when the partner is changed:
        - Pricelist
        """
        values = {
            'pricelist_id': self.cust_name.property_product_pricelist and self.cust_name.property_product_pricelist.id or False,
        }
        self.update(values)
        
        
    @api.multi
    def ceo_approval(self):
        self.approval_state = 'approved'
        self.state = 'ceo_approved'
        print "AAAAAAAAAAAAAAAAAAAAa",self.state
        
    @api.multi
    def ceo_rejection(self):
        print "AAAAAAAAAAAAAAAAAAAAa",self.state
        self.approval_state = 'rejected'
    
    
class stock_pack_operation_extension(models.Model):
    _inherit = 'stock.pack.operation'
    
    @api.depends('product_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the PO line.
        """
        print "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.picking_id.currency_id, line.product_qty, product=line.product_id, partner=line.picking_id.cust_name)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
    
    
    sr_no = fields.Char(string="Machine or OTL Sr. No.", readonly=1)
    price_unit = fields.Float(string='Unit Price', store=True)
    tax_id = fields.Many2many('account.tax', string='Taxes')
    discount = fields.Float(string='Discount (%)', default=0.0)
    description = fields.Text(string="Description")
    
    price_subtotal = fields.Float(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Taxes', readonly=True, store=True)
    price_total = fields.Float(compute='_compute_amount', string='Total', readonly=True, store=True)
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(stock_pack_operation_extension, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
        
            node = doc.xpath("//field[@name='sr_no']")[0]
            logistic_group = self.env.user.has_group('stock.group_stock_manager')
            if logistic_group:
                node.set('readonly', '0')
                setup_modifiers(node, res['fields']['sr_no'])
            res['arch'] = etree.tostring(doc)
        return res
    
        
class delivery_term(models.Model):
    _name = 'delivery.term'
    
    name = fields.Char(string="Delivery Term")
    
    # @api.onchange("dealer_name")
    # def onchange_dealer(self):
    #     print " SSSSSSSSSSSSSSSSSSSSSSSsss" ,self.dealer_name
    #     if self.dealer_name:
    #         self.dealer_pan = self.dealer_name.pan_no
    #         self.dealer_tin = self.dealer_name.tin_no
    #         print "DDDDDDDDDDDDDDDDDDDDDDDDDD" ,self.dealer_pan, self.dealer_tin
