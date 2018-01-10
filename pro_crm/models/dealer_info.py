from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _, tools
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from werkzeug import url_encode

class dealer_info(models.Model):
	_inherit = 'res.partner'
	
	@api.model
	def default_get(self, vals):
		res = super(dealer_info, self).default_get(vals)
		country_ids = self.env['res.country'].search([('code','=','IN')])
	
		if country_ids:
			res.update({
						'country_id':country_ids[0].id, # Many2one field
						})
		return res

	
	
	user_id = fields.Many2one('res.users', string= "Salesperson", default=lambda self: self.env.user, options="{'no_open': True}")
	constitution_firm = fields.Many2one('constitution.firm', string="Constitution of the firm")
	year = fields.Date(string="Year of Establishment")
	financial_turn_over = fields.Selection([('<1cr', '< 1 Cr'),('1cr-5cr', '1Cr. To 5Cr'),('5cr-10cr', '5Cr. To 10Cr'),('>10cr', '>10 Cr')], string='Financial Turnovers')
	manager = fields.Integer(string="Managers Sector")
	sales_marketing = fields.Integer(string="Sales /Marketing")
	technicians = fields.Integer(string="Technicians")
	administration = fields.Integer(string="Administration")
	total = fields.Integer(string="Total" , compute="_total")
	area = fields.Char(string="Areas / Districts covered")
	size = fields.Char(string="Size of Office")
	location = fields.Char(string="Location")
	office_loc = fields.Char(string="Office is in")
	rental = fields.Char(string="Rental")
	accredations = fields.Char(string="Accredations & Certifications")
	# dealing_area = fields.Selection([('private', 'Private'),('government', 'Government'),('institutes', 'Institutes')],string='Dealer Dealing Area')
	dealing_area = fields.Many2many('dealing.area',string='Dealer Dealing Area')
	experience = fields.Char(string="Experience in Medical Field")
	product_range = fields.Char(string="Product Range")
	cautery = fields.Selection([('yes', 'Yes'),('no', 'No')], string='Have you done Cautery Before?')
	installation = fields.Selection([('yes', 'Yes'),('no', 'No')], string='Knowledge about Installation and Servicing?')
	brand = fields.Char(string="Brand")
	years = fields.Char(string="Years")
	led_ot = fields.Selection([('yes', 'Yes'),('no', 'No')], string='Have you done LED OT Light Before?')
	servicing = fields.Selection([('yes', 'Yes'),('no', 'No')], string='Knowledge about Installation and Servicing?')
	brand1 = fields.Char(string="Brand")
	years1 = fields.Char(string="Years")
	details  = fields.One2many('detail.dealership', 'detail_dealer', string = "Details of Dealership")
	pan_no = fields.Char(string="PAN No.")
	tin_no = fields.Char(string="TIN No.")
	service_tax_reg_no = fields.Char(string="Service Tax Reg No.")
	cst_no = fields.Char(string="CST No.")
	sales_tax_no = fields.Char(string="Sales Tax No.")
	hosp_name = fields.Char(string="Hospital Name")
	manager_id =fields.Many2one('res.users', string="Manager")
	dealer = fields.Boolean(string="Is a Dealer")
	company_type = fields.Selection([('person', 'Private'),('company', 'Corporate'),('dealer', 'Dealer')], string='Company Type')
	zone = fields.Many2one('crm.configuration', string="Zone", options="{'no_open': True}")
	cust_code = fields.Char(string="Customer Code")
	enquiry_count = fields.Integer(string='Enquiry', compute='_get_enquiry_number', readonly=True, copy=False)
	sale_count = fields.Integer(string='Sales', compute='_get_enquiry_number', readonly=True, copy=False)
	
	@api.multi
	def _get_enquiry_number(self):
		for record in self:
			enquiry = self.env['crm.lead'].search([('dealer_name', '=', record.id)])
			sales = self.env['sale.order'].search([('dealer_name', '=', record.id)])
			record.update({
				'enquiry_count': len(enquiry),
				'sale_count': len(sales),
			})
	
	
	@api.multi
	@api.onchange('user_id')
	def onchange_zone(self):
		self.zone = self.user_id.partner_id.zone
		self.manager_id = self.user_id.partner_id.manager_id
	
	@api.model
	def create(self, vals):
		if vals.get('customer'):
			zone_code = ''
			seq_srch=self.env['ir.sequence'].search([('code','=','crm.customer')])
			# year = datetime.today().strftime('%Y') 
			if seq_srch:
				zone = self.env['crm.configuration'].search([('id','=',vals['zone'])])
				zone_code = zone.zone_code
			year = datetime.today().year
			month = datetime.today().month
			vals['cust_code'] = self.env['ir.sequence'].next_by_code('crm.customer')
			if month <= 3:
				pre_year = year - 1
				pre_year1 = str(pre_year)[2:]
				pre_year_1 = str(year)[2:]
				cust_code = zone_code + "/" + vals['cust_code'] + "/" + str(pre_year1) + '-' + str(pre_year_1)
			if month > 3:
				next_year = year + 1
				year1 = str(year)[2:]
				next_year_2 = str(next_year)[2:]
				cust_code = zone_code + "/" + vals['cust_code'] + "/" + str(year1) + '-' + str(next_year_2) 
			print "LLLLLLLLLLLLLLLLLLLLLLLL" , cust_code
			vals['cust_code'] = cust_code
		result = super(dealer_info, self).create(vals)
		return result


	
	@api.multi
	def _total(self):
		for order in self:
			total = 0.0
			for record in self:
				total = record.manager + record.sales_marketing + record.technicians + record.administration
		order.total = total

class constitution_firm(models.Model):
	_name = 'constitution.firm'
	
	name = fields.Char(string="Constitution of the firm")
	
class dealing_area(models.Model):
	_name = 'dealing.area'
	
	name = fields.Char(string="Dealing Area")
	
class details_dealership(models.Model):
	_name = 'detail.dealership'
	
	detail_dealer = fields.Many2one('res.partner', string='Details')
	sr_no = fields.Integer(string = "Sr.No.")
	company = fields.Many2one('res.company' , string="Name of Company")
	products = fields.Many2one('product.product', string="Products")
	dealer_since = fields.Date(string = "Dealer Since")
	sales_fig = fields.Char(string="Sales Figures of Last Three Years")
