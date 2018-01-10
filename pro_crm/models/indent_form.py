from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _, tools
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from werkzeug import url_encode
import lxml
from lxml import etree
from openerp.osv.orm import setup_modifiers


class crm_indent(models.Model):
    _name = 'crm.indent'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _rec_name = 'ind_no'
    _order = 'create_date desc'
    
    demo_indent_id = fields.Many2one('crm.lead',string='Demo indent')
    cust_name = fields.Many2one('res.partner', string="Customer Name")
    state = fields.Selection([('draft','Draft'),('zsmaprvl','ZSM Approval'),('zsmrejctd','ZSM Rejected'),('logaprvl','Logistics Approval'),('logrejctd','Logistics Rejected'),('ceoaprvl','CEO Approval'),('done','Done'),('cancel','Cancelled')], track_visibility='onchange', string="State", default="draft")
    existing_customer = fields.Selection([('yes','Yes'),('no','No')], string = "Customer Existing?")
    ind_no = fields.Char(string="IND No.")
    date = fields.Date(string="Date", default=datetime.now().date())
    hospital_name = fields.Char(string="Hospital Name")
    from_date = fields.Date(string="From")
    deal_done_by = fields.Many2one('res.users', string="Salesperson")
    enquiry = fields.Many2one('utm.source', string="Enquiry Through")
    street = fields.Char(string="Street")
    street2 = fields.Char(string= "Street2")
    city = fields.Char(string="City")
    state_id = fields.Many2one('res.country.state', string="State")
    zip1 = fields.Char(string="Zip")
    country_id = fields.Many2one('res.country', string="Country")
    zone = fields.Many2one('crm.configuration', string="Zone", placeholder="Zone")
    contact_no = fields.Char(string="Contact No.")
    # contact_no = fields.Char(string="Contact No.", related="cust_name.mobile", store= True)
    # email = fields.Char(string="Email", related="cust_name.email)
    email = fields.Char(string="Email")
    cust_faculty = fields.Many2one('customer.faculty', string="Customer Faculty")
    purpose = fields.Selection([('demo_on_approval','Demo on approval'),('demo','Demo')], string="Purpose")
    comment = fields.Text(string="Remarks")
    machine_status = fields.Selection([('out','Out for demo'),('returned','Returned'),('sold','Sold')], string="Machine Status", track_visibility='onchange')
    machine_date = fields.Date(string="Date")
    machine_details = fields.Text(string="Notes")
    cancellation_reason = fields.Char(string="Cancellation Reason")
    rejection_reason = fields.Char(string="Rejection Reason")
    url = fields.Char(string ="Click here", compute="compute_url")
    name = fields.Char(string="Name")
    contact_name = fields.Char(string="Contact Name")
    product_details_one2many  = fields.One2many('product.details', 'name', string ="Product Details")        
    expected_date = fields.Date(string="Expected Date")
    approx_date = fields.Date(string="Approximate Date")
    dispatch = fields.Many2one('dispatch.through', string="Dispatch through")
    transporter_name = fields.Char(string="Transporter Name")
    lr_no = fields.Char(string="LR No.")
    dc_no = fields.Char(string="DC No.")
    payment_term = fields.Many2one('payment.term', string="Payment Term")
    total_deal_value = fields.Char(string="Total Deal Value")
    manager_id = fields.Many2one(related="deal_done_by.partner_id.manager_id", store=True)
    enquiry_type = fields.Selection([('private', 'Private'),('corporate', 'Corporate'),('dealer', 'Dealer')], string='Type of Enquiry')
    
    
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
    
    delivery_street = fields.Char(string="Address")
    delivery_street2 = fields.Char(string= " ")
    delivery_city = fields.Char(string=" ")
    delivery_state_id = fields.Many2one('res.country.state', string=" ")
    delivery_zip1 = fields.Char(string=" ")
    delivery_country_id = fields.Many2one('res.country', string=" ")

    @api.model
    def create(self, vals):
        zone_code = ''
        seq_srch=self.env['ir.sequence'].search([('code','=','demo.indent')])
        
        if seq_srch:
            zone = self.env['crm.configuration'].search([('id','=',vals['zone'])])
            zone_code = zone.zone_code
        year = datetime.today().year
        month = datetime.today().month
        vals['ind_no'] = self.env['ir.sequence'].next_by_code('demo.indent')

        if month <= 3:
            pre_year = year - 1
            pre_year_1 = str(year)[2:]
            ind_no = "DEMO" + "/" + zone_code + "/" + vals['ind_no'] + "/" + str(pre_year) + '-' + str(pre_year_1)
        if month > 3:
            next_year = year + 1
            next_year_2 = str(next_year)[2:]
            ind_no = "DEMO" + "/" + zone_code + "/" + vals['ind_no'] + "/" + str(year) + '-' + str(next_year_2) 
        print "LLLLLLLLLLLLLLLLLLLLLLLL" , ind_no
        # # print error
        vals['ind_no'] = ind_no
        
        # vals['ind_no'] = self.env['ir.sequence'].next_by_code('demo.indent')
        result = super(crm_indent, self).create(vals)
        if result.demo_indent_id:
            print"====result.demo_indent_id.crm_indent_id===",result.demo_indent_id.crm_indent_id
            if not result.demo_indent_id.crm_indent_id:
                result.demo_indent_id.crm_indent_id = result.id
        return result
    
    @api.multi
    def unlink(self):
        for order in self:
            if order.state != 'draft':
                raise UserError(_('You can only delete draft Demo Indent!'))
        return super(crm_indent, self).unlink()
    
    
    @api.multi
    def compute_url(self):
        for record in self:
            if record.deal_done_by:
                base_url = record.env['ir.config_parameter'].sudo().get_param('web.base.url')
                record.url =  base_url + '#%s' % (url_encode({
                            'id': record.id,
                            'view_type': 'form',
                            'model': 'crm.indent',
                        }))
    
    @api.multi
    def send_approval(self):
        template_obj = self.env['mail.template']
        ir_model_data = self.env['ir.model.data']
        template_id= self.env.ref('pro_crm.demo_zsmapproval_template')
        res = template_id.send_mail(self.id, force_send=True, raise_exception=False)
        self.state = 'zsmaprvl'
    
    @api.multi
    def cancel(self):
        self.state = 'cancel'
        
    # @api.multi
    # def zsm_rejected(self):
    #     print "TTTTTTTTTTTTTTTTTTTTTTTTTTtt"
    #     self.state = 'zsmrejctd'
        
    @api.multi
    def zsm_approval(self):
        template_obj = self.env['mail.template']
        ir_model_data = self.env['ir.model.data']
        template_id= self.env.ref('pro_crm.demo_logapproval_template')
        email_list = []
        
        logistic_group = self.env['ir.model.data'].get_object('stock', 'group_stock_manager')
        # print "ASAAAAAAAAAAAAAAAAAAAAAAAA", logistic_group
        if logistic_group and logistic_group.users:
            for user in logistic_group.users:
                email_list.append(user.email)
        else:
            raise UserError("Stock Manager not Defined!")
        
        emails = ",".join([str(x) for x in email_list])
        
        if template_id:
            template_id.email_to = emails
        res = template_id.send_mail(self.id, force_send=True, raise_exception=False)
        self.state = 'logaprvl'
    
   
        
    @api.multi
    def log_approval(self):
        template_obj = self.env['mail.template']
        ir_model_data = self.env['ir.model.data']
        template_id= self.env.ref('pro_crm.demo_ceoapproval_template')
        email_list = []
        
        ceo_group = self.env['ir.model.data'].get_object('pro_crm', 'group_pro_crm_ceo')
        print "ASAAAAAAAAAAAAAAAAAAAAAAAA", ceo_group
        if ceo_group and ceo_group.users:
            for user in ceo_group.users:
                email_list.append(user.email)
        else:
            raise UserError("CEO not Defined!")
        
        emails = ",".join([str(x) for x in email_list])
        
        if template_id:
            template_id.email_to = emails
        res = template_id.send_mail(self.id, force_send=True, raise_exception=False)
        self.state = 'ceoaprvl'
    
    # @api.multi
    # def log_rejected(self):
    #     self.state = 'logrejctd'
    
    @api.multi
    def ceo_approval(self):
        self.state = 'done'
        self.machine_status = 'out'
        
    # @api.multi
    # def ceo_rejected(self):
    #     self.state = 'cancel'
    
    @api.model
    def send_mail(self):
        crm_indent_ids = self.search([])
        template_obj = self.env['mail.template']
        ir_model_data = self.env['ir.model.data']
        template_id= self.env.ref('pro_crm.log_dispatch_notification_template')
        for crm_indent_id in crm_indent_ids:
            if crm_indent_id.approx_date:
                duedate = str(crm_indent_id.approx_date).split( )[0].split('-')[2]
                # print"CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",duedate
                current_date = datetime.now()
                # print"DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD",current_date
                new_cur_date = str(current_date).split( )[0].split('-')[2]
                # print"fffffffffffffffffffffffffffffffffffffffffffff",new_cur_date
                if int(duedate) - int(new_cur_date) == 1:
                    # print "FFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
                    template_id= self.env.ref('pro_crm.log_dispatch_notification_template')
                    email_list = []
                    logistic_group = self.env['ir.model.data'].get_object('stock', 'group_stock_manager')
                    # print "ASAAAAAAAAAAAAAAAAAAAAAAAA", logistic_group
                    if logistic_group and logistic_group.users:
                        for user in logistic_group.users:
                            email_list.append(user.email)
                    else:
                        raise UserError("Stock Manager not Defined!")
                    
                    emails = ",".join([str(x) for x in email_list])
                    
                    if template_id:
                        template_id.email_to = emails
                        
                    res = template_id.send_mail(crm_indent_id.id, raise_exception=False)
    
     
class product_details(models.Model):
    _name = 'product.details'
    
    name = fields.Many2one('crm.indent', string='Product Details', invisible="1")
    model = fields.Many2one('product.product', string="Model")
    description = fields.Text(string="Description")
    sr_no = fields.Char(string="Machine or OTL Sr. No.", readonly="1")
    qty = fields.Integer(string="Qty")
    # prod_cost = fields.Float(string="Estimated Cost")
    # accessories = fields.Many2one('product.product', string="Accessories")
    # instrument = fields.Many2one('product.product', string="Instrument")
    product_type = fields.Selection([('dealer','Dealer'),('direct','Direct')], string="Type" )
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(product_details, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
        
            node = doc.xpath("//field[@name='sr_no']")[0]
            logistic_group = self.env.user.has_group('stock.group_stock_manager')
            if logistic_group:
                node.set('readonly', '0')
                setup_modifiers(node, res['fields']['sr_no'])
            res['arch'] = etree.tostring(doc)
        return res


        
class sale_indent(models.Model):
    _name = 'sale.indent'
    _description = 'Sale Indent'
    
    #SALE INDENT FORM - DEALER
    
    name = fields.Selection([('Dealer','Sale Indent - Dealer'),('Direct','Sale Indent - Direct'),('Tender','Sale Indent - Tender')], string="Type of Sale Indent")
    dealer_ind_no = fields.Char(string="IND No.")
    dealer_date = fields.Date(string="Date")
    dealer_from_date = fields.Date(string="From")
    dealer_deal_done_by = fields.Many2one('res.users', string="Deal done by")
    dealer_enquiry =fields.Many2one('utm.source', string="Enquiry Through")
    dealer_name = fields.Char(string="Dealer Name")
    dealer_street = fields.Char(string="Address")
    dealer_street2 = fields.Char(string= " ")
    dealer_city = fields.Char(string=" ")
    dealer_state_id = fields.Many2one('res.country.state', string=" ")
    dealer_zip1 = fields.Char(string=" ")
    dealer_country_id = fields.Many2one('res.country', string=" ")
    dealer_pan = fields.Integer(string="PAN No.")
    dealer_tin = fields.Integer(string="TIN No.")
    dealer_contact_no = fields.Char(string="Contact No.")
    dealer_email = fields.Char(string="Email")
    dealer_cust_name = fields.Char(string="Customer Name")
    dealer_cust_street = fields.Char(string="Address")
    dealer_cust_street2 = fields.Char(string= " ")
    dealer_cust_city = fields.Char(string=" ")
    dealer_cust_state_id = fields.Many2one('res.country.state', string=" ")
    dealer_cust_zip1 = fields.Char(string=" ")
    dealer_cust_country_id = fields.Many2one('res.country', string=" ")
    dealer_cust_tin = fields.Integer(string="TIN No.")
    dealer_cust_contact_no = fields.Char(string="Contact No.")
    dealer_cust_email = fields.Char(string="Email")
    dealer_cust_faculty = fields.Many2one('customer.faculty', string="Customer Faculty")
    dealer_cust_warranty = fields.Char(string="Warranty")
    dealer_model = fields.Many2one('product.category', string="Model")
    dealer_qty = fields.Integer(string="Qty")
    dealer_accessories = fields.Many2one('product.product', string="Accessories")
    dealer_instrument = fields.Many2one('product.product', string="Instrument")
    dealer_requirement = fields.Char(string="As per Requirement")
    dealer_spl_instructions = fields.Char(string="Special Instruction")
    dealer_comment = fields.Text(string="Remarks")
    
    #SALE INDENT FORM- DIRECT
    
    direct_ind_no = fields.Char(string="IND No.")
    direct_date = fields.Date(string="Date")
    direct_from_date = fields.Date(string="From")
    direct_deal_done_by = fields.Many2one('res.users', string="Deal done by")
    direct_enquiry = fields.Many2one('utm.source', string="Enquiry Through")
    direct_cust_name = fields.Char(string="Customer Name")
    direct_cust_hosp_name = fields.Char(string="Hospital Name")
    direct_cust_street = fields.Char(string="Address")
    direct_cust_street2 = fields.Char(string= " ")
    direct_cust_city = fields.Char(string=" ")
    direct_cust_state_id = fields.Many2one('res.country.state', string=" ")
    direct_cust_zip1 = fields.Char(string=" ")
    direct_cust_country_id = fields.Many2one('res.country', string=" ")
    direct_cust_pan = fields.Integer(string="PAN No.")
    direct_cust_tin = fields.Integer(string="TIN No.")
    direct_cust_contact_no = fields.Char(string="Contact No.")
    direct_cust_email = fields.Char(string="Email")
    direct_cust_faculty = fields.Many2one('customer.faculty', string="Customer Faculty")
    direct_cust_warranty = fields.Char(string="Warranty")
    direct_model = fields.Many2one('product.category', string="Model")
    direct_qty = fields.Integer(string="Qty")
    direct_accessories = fields.Many2one('product.product', string="Accessories")
    direct_instrument = fields.Many2one('product.product', string="Instrument")
    direct_requirement = fields.Char(string="As per Requirement")
    direct_spl_instructions = fields.Char(string="Special Instruction")
    direct_comment = fields.Text(string="Remarks")
    
    #INDENT FORM(TENDER)
    
    tender_ind_no = fields.Char(string="IND No.")
    tender_date = fields.Date(string="Date")
    tender_from_date = fields.Date(string="From")
    tender_deal_done_by = fields.Many2one('res.users', string="Deal done by")
    tender_enquiry = fields.Many2one('utm.source', string="Enquiry Through")
    tender_name = fields.Char(string="Tender Name")
    tender_no = fields.Char(string="Tender No.")
    tender_location = fields.Char(string="Tender Location")
    tender_authority = fields.Char(string="Authority")
    tender_quote_by = fields.Char(string="Tender Quote By")
    tender_comp_name = fields.Char(string="Company Name")
    tender_dealer_name = fields.Char(string="Dealer Name")
    tender_contact_name = fields.Char(string="Contact Person Name")
    tender_email = fields.Char(string="Email")
    tender_designation = fields.Char(string="Designation of person")
    tender_website = fields.Char(string="Website")
    tender_mobile_no = fields.Char(string="Mobile No.")
    tender_landline_no = fields.Char(string="Landline No.")
    tender_emd = fields.Char(string="EMD Details")
    tender_proof = fields.Char(string="Proof")
    tender_model = fields.Many2one('product.category', string="Model")
    tender_qty = fields.Integer(string="Qty")
    tender_accessories = fields.Many2one('product.product', string="Accessories")
    tender_standard = fields.Char(string="Standard")
    tender_instrument = fields.Many2one('product.product', string="Instruments")
    tender_requirement = fields.Char(string="As per Requirement")
    tender_spl_instructions = fields.Char(string="Special Instruction")
    tender_purchase_order = fields.Selection([('yes','Yes'),('no','No')])
    tender_att_documents = fields.Char(string="Attached Tender Documents")
    tender_warranty = fields.Char(string="Warranty Details")
    tender_comment = fields.Text(string="Remarks")
    
    
    @api.model
    def create(self, vals):
        
        vals['dealer_ind_no'] = self.env['ir.sequence'].next_by_code('dealer.indent')
        vals['direct_ind_no'] = self.env['ir.sequence'].next_by_code('direct.indent')
        vals['tender_ind_no'] = self.env['ir.sequence'].next_by_code('tender.indent')
        result = super(sale_indent, self).create(vals)
        return result
    
    
class customer_faculty(models.Model):
	_name = 'customer.faculty'
	
	name = fields.Char(string="Customer Faculty")

class dispatch_through(models.Model):
	_name = 'dispatch.through'
	
	name = fields.Char(string="Dispatch through")

class payment_term(models.Model):
	_name = 'payment.term'
	
	name = fields.Char(string="Payment Term")
