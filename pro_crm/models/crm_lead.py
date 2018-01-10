# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _, tools
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from werkzeug import url_encode


class crm_lead_extension(models.Model):
    _inherit = 'crm.lead'
    _order = "id desc"
    
    
    # ---------------------Sets default country India-----------------------#
    
    @api.model
    def default_get(self, vals):
        res = super(crm_lead_extension, self).default_get(vals)
        country_ids = self.env['res.country'].search([('code','=','IN')])

        if country_ids:
            res.update({
                        'country_id':country_ids[0].id, # Many2one field
                       })
        return res
        
    
    
    # cust_code = fields.Char(string="Customer Code")
    existing_customer = fields.Selection([('yes','Yes'),('no','No')], string = "Customer Existing?",default='no')
    cust_from = fields.Date(string="From")
    hospital_name = fields.Char(string="Hospital Name", store= True)
    zone = fields.Many2one(related="user_id.partner_id.zone" , string="Zone", placeholder="Zone", store= True)
    pan_no = fields.Char(string="PAN No.", store= True)
    # zone = fields.Many2one('crm.configuration', string="Zone", store= True, default=default_zone)
    enquiry_no = fields.Char(string="Enquiry No.")
    enquiry_type = fields.Selection([('private', 'Private'),('corporate', 'Corporate'),('dealer', 'Dealer')], string='Type of Enquiry')
    sales = fields.Selection([('sales','Sales'),('aftersales','After Sales')])
    product_enquiry_one2many  = fields.One2many('product.enquiry', 'name', string = "Product Details")
    demo_required = fields.Selection([('yes','Yes'),('no','No')], string = "Demo Required?",default='no')
    indent_form = fields.Integer(string="Indent Form", compute='open_indent_form')
    crm_indent_id = fields.Many2one('crm.indent', string="Indent Form")
    crm_name = fields.Char(string="", related="crm_indent_id.ind_no")
    demo_details_one2many  = fields.One2many('demo.details', 'name', string = "Demo Details")
    manager_id = fields.Many2one(related="user_id.partner_id.manager_id", string="Zonal Sales Manager", store=True)
    is_won = fields.Boolean(string='won')
    is_lost = fields.Boolean(string='lost')
    cust_faculty = fields.Many2one('customer.faculty', string="Customer Faculty")
    zonal_sales_manager = fields.Many2one(related="user_id.partner_id.manager_id", string="Zonal Sales Manager")
    lead_lost_reason = fields.Many2one('lost.reason', string= "Lost Reason")
    dealer_name = fields.Many2one('res.partner', string="Dealer Name")

    # @api.multi
    # @api.onchange('user_id')
    # def onchange_zone(self):
    #     print "HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH"
    #     self.zone = self.user_id.partner_id.zone
    #     self.manager_id = self.user_id.partner_id.manager_id
    
    
    # @api.multi
    # @api.onchange('partner_id')
    # def on_change_partner_id(self):
    #     res = super(crm_lead_extension, self).on_change_partner_id(self)
    #     self.hospital_name = res.partner_id.hosp_name
    #     return res
    
    def on_change_partner_id(self, cr, uid, ids, partner_id, context=None):
        values = {}
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            partner_name = (partner.parent_id and partner.parent_id.name) or (partner.is_company and partner.name) or False
            values = {
                'partner_name': partner_name,
                'contact_name': (not partner.is_company and partner.name) or False,
                'title': partner.title and partner.title.id or False,
                'street': partner.street,
                'street2': partner.street2,
                'city': partner.city,
                'state_id': partner.state_id and partner.state_id.id or False,
                'country_id': partner.country_id and partner.country_id.id or False,
                'email_from': partner.email,
                'hospital_name': partner.hosp_name,
                'pan_no': partner.pan_no,
                'phone': partner.phone,
                'mobile': partner.mobile,
                'fax': partner.fax,
                'zip': partner.zip,
                'function': partner.function,
            }
        return {'value': values}
    
    
    @api.multi
    @api.onchange('existing_customer')
    def onchange_existing_customer(self):
        
        if self.existing_customer == 'no':
            self.partner_id = False
            # self.on_change_partner_id(self.partner_id)
            self.street = False
            self.street2 = False
            self.city = False
            self.state_id = False
            self.zip = False
            self.country_id = False
            self.title = False
            self.contact_name = False
            self.email_from = False
            self.phone = False
            self.mobile = False
            self.fax = False
            self.hospital_name = False
       
       
    @api.multi
    def sale_action_quotations_new(self):
        imd = self.env['ir.model.data']
        product_uom_obj = imd.xmlid_to_object('product.product_uom_categ_unit')
        
        order_lines = []

        for product in self.demo_details_one2many:
             
            product_desc = product.product
            order_lines.append([0,0,{
                'sequence':10,
                'customer_lead':0,
                'product_uom_qty':product.qty,
                'product_uom':product_desc.product_tmpl_id.uom_id.id,
                # 'order_id':self.id,
                'name': self.name,
                # 'account_id': product_account.id,
                'price_unit': product.prod_cost or 0,
                'product_id': product_desc.id or False,
                # 'account_analytic_id': self.order_id.project_id.id
                'invoice_status':'upselling',
            }])
        
        ctx = self._context.copy()
        ctx.update({
            'default_partner_id': self.partner_id.id,
            # 'default_payment_term_id': self.payment_term_id.id,
            'default_opportunity_id': self.id,
            'default_user_id': self.user_id.id,
            'default_team_id': self.team_id.id,
            'default_source_id': self.source_id.id,
            'default_zone': self.zone.id,
            'default_hospital_name': self.hospital_name,
            'default_pan_no': self.pan_no,
            'default_enquiry_type': self.enquiry_type,
            'default_dealer_name': self.dealer_name.id,
            'default_cust_faculty': self.cust_faculty.id,
            # 'default_account_id': self.customer_id.property_account_receivable_id.id,
            # 'default_currency_id': self.customer_id.currency_id.id,
            'default_origin': self.name,
            'default_order_line': order_lines,
            'default_invoice_status':'upselling',
        })
        # order_ids = crm_obj.search([('origin','ilike',self.name)])
        
        action = imd.xmlid_to_object('sale.action_quotations')
        # list_view_id = imd.xmlid_to_res_id('sale.view_quotation_tree')
        form_view_id = imd.xmlid_to_res_id('sale.view_order_form')
        
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[form_view_id, 'form']],
            'target': action.target,
            'context': ctx,
            'res_model': action.res_model,
        }
        # if len(order_ids) > 1:
        # 	result['domain'] = "[('id','in',%s)]" % order_ids.ids
        # elif len(order_ids) == 1:
        # 	# result['target'] = 'new'
        # 	result['views'] = [(form_view_id, 'form')]
        # 	result['res_id'] = order_ids.ids[0]
        # else:
        # 	result['views'] = [(form_view_id, 'form')]
        # 	result['view_id'] = form_view_id
        # 	result['view_mode'] = 'form'
        return result


    @api.multi
    def action_set_won(self, fields_list):
        self.write({'is_won':True})
        res = super(crm_lead_extension, self).action_set_won()
        return res
    
    @api.multi
    def action_set_lost(self):
        self.write({'is_lost':True})
        res = super(crm_lead_extension, self).action_set_lost()
        return res
    
    @api.multi
    def open_indent_form(self):
        result2 = []
        for rec in self:
            for record in rec.demo_details_one2many:
                if record.product:
                    result2.append([0,0,{
                        'model':record.product.id,
                        'qty':record.qty,
                        'prod_cost':record.prod_cost,
                        'description':record.description,
                    }])
                    
        ctx = self._context.copy()
        # print"=======self===", self, self.id, self.mobile
        ctx.update({
            'default_demo_indent_id': self.id,
            'default_deal_done_by': self.user_id.id,
            'default_enquiry': self.source_id.id,
            'default_cust_name': self.partner_id.id,
            'default_hospital_name': self.hospital_name,
            'default_street': self.street,
            'default_street2': self.street2,
            'default_city': self.city,
            'default_zip1': self.zip,
            'default_state_id': self.state_id.id,
            'default_country_id': self.country_id.id,
            'default_zone': self.zone.id,
            'default_contact_no': self.mobile,
            'default_cust_faculty': self.cust_faculty.id,
            'default_email': self.email_from,
            'default_existing_customer': self.existing_customer,
            'default_contact_name': self.contact_name,
            'default_enquiry_type': self.enquiry_type,
            'default_dealer_name': self.dealer_name.id,
            'default_product_details_one2many': result2 or '',
            # 'default_model': self.demo_details_one2many.product.id,
            # 'default_qty': self.demo_details_one2many.qty,
            })
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('pro_crm.action_indent_form')
        form_view_id = imd.xmlid_to_res_id('pro_crm.crm_indent_form')
        
        result = {
            'name' : action.name,
            'help' : action.help,
            'type' : action.type,
            'views' : [[form_view_id, 'form']],
            'view_mode' : 'form',
            'target' : action.target,
            'context' : ctx,
            'res_model' : action.res_model,
        }
        if self.crm_indent_id:
            result['res_id'] = self.crm_indent_id.id
        # print "dfdsffffffffffffff",result
        
                            
        return result
   

    @api.model
    def create(self, vals):
        zone_code = ''
        seq_srch=self.env['ir.sequence'].search([('code','=','crm.enquiry')])
        if seq_srch:
            
            sales_user = self.env['res.users'].search([('id','=',self.env.user.id)])
        zone_code = sales_user.partner_id.zone.zone_code
        year = datetime.today().year
        month = datetime.today().month
        vals['enquiry_no'] = self.env['ir.sequence'].next_by_code('crm.enquiry')
        if month <= 3:
            pre_year = year - 1
            pre_year1 = str(pre_year)[2:]
            pre_year_1 = str(year)[2:]
            enquiry_no = zone_code + "/" + vals['enquiry_no'] + "/" + str(pre_year1) + '-' + str(pre_year_1) 
        if month > 3:
            next_year = year + 1
            year1 = str(year)[2:]
            next_year_2 = str(next_year)[2:]
            enquiry_no = zone_code + "/" + vals['enquiry_no'] + "/" + str(year1) + '-' + str(next_year_2) 
        
        # enquiry_no = "EN" + "/" + zone_code + "/" + vals['enquiry_no'] + "/" + year 
        print "LLLLLLLLLLLLLLLLLLLLLLLL" , enquiry_no
        # # print error
        vals['enquiry_no'] = enquiry_no


        # vals['cust_code'] = self.env['ir.sequence'].next_by_code('crm.lead')
        # vals['enquiry_no'] = self.env['ir.sequence'].next_by_code('crm.enquiry')
        result = super(crm_lead_extension, self).create(vals)
        return result
    
    
    def _lead_create_contact(self, cr, uid, lead, name, is_company, parent_id=False, context=None):
        # valsdef _lead_create_contact(self, cr, uid, lead, name, is_company, parent_id=False, context=None):
        partner = self.pool.get('res.partner')
        vals = {'name': name,
            'user_id': lead.user_id.id,
            'comment': lead.description,
            'team_id': lead.team_id.id or False,
            'parent_id': parent_id,
            'phone': lead.phone,
            'mobile': lead.mobile,
            'email': tools.email_split(lead.email_from) and tools.email_split(lead.email_from)[0] or False,
            'fax': lead.fax,
            'title': lead.title and lead.title.id or False,
            'function': lead.function,
            'street': lead.street,
            'street2': lead.street2,
            'zip': lead.zip,
            'pan_no': lead.pan_no,
            'city': lead.city,
            'country_id': lead.country_id and lead.country_id.id or False,
            'state_id': lead.state_id and lead.state_id.id or False,
            'is_company': is_company,
            'type': 'contact',
            'zone': lead.zone and lead.zone.id or False,
            'manager_id': lead.manager_id.id,
            'customer' : True
        }
        partner = partner.create(cr, uid, vals, context=context)
        return partner
    
    # @api.model
    # def default_get(self, fields_list):
    #     print "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII"
    #     res = super(crm_lead_extension, self).default_get(fields_list)
    #     # res.update({'type': 'opportunity'})
    #     res['type'] = 'opportunity'
    #     return res
                
# class product_type(models.Model):
# 	_name = 'product.type'
# 	
# 	name = fields.Char(string="Type Of Product")

class product_enquiry(models.Model):
    _name = 'product.enquiry'
    
    name = fields.Many2one('crm.lead', string='Product Details', invisible="1")
    product_type = fields.Many2one('product.category', related="model.product_tmpl_id.categ_id", string="Type of Product")
    model = fields.Many2one('product.product',string="Model")
    product_no = fields.Integer(string="No. of Products")

class demo_details(models.Model):
    _name = 'demo.details'
    
    name = fields.Many2one('crm.lead', string='Demo Details', invisible="1")
    product = fields.Many2one('product.product',string="Product")
    description = fields.Text(string="Description", store=True)
    prod_cost = fields.Float(string="Estimated Cost")
    qty = fields.Integer(string="Quantity")
    demo_date =fields.Date(string="Date")
    remark = fields.Char(string="Remark")
    
    @api.multi
    @api.onchange('product')
    def product_id_change(self):
        if self.product:
            self.description = self.product.description_sale
    
    
class crm_lead2opportunity_partner_extension(models.Model):
    _inherit = 'crm.lead2opportunity.partner'
    
    name = fields.Selection([('convert', 'Convert to opportunity'),], 'Conversion Action', required=True)
    
    # def action_apply(self, cr, uid, ids, context=None):
    #     """
    #     Convert lead to opportunity or merge lead and opportunity and open
    #     the freshly created opportunity view.
    #     """
    #     if context is None:
    #         context = {}
    # 
    #     lead_obj = self.pool['crm.lead']
    #     partner_obj = self.pool['res.partner']
    # 
    #     w = self.browse(cr, uid, ids, context=context)[0]
    #     opp_ids = [o.id for o in w.opportunity_ids]
    #     vals = {
    #         'team_id': w.team_id.id,
    #     }
    #     if w.partner_id:
    #         vals['partner_id'] = w.partner_id.id
    #     if w.name == 'merge':
    #         lead_id = lead_obj.merge_opportunity(cr, uid, opp_ids, context=context)
    #         lead_ids = [lead_id]
    #         lead = lead_obj.read(cr, uid, lead_id, ['type', 'user_id'], context=context)
    #         if lead['type'] == "lead":
    #             context = dict(context, active_ids=lead_ids)
    #             vals.update({'lead_ids': lead_ids, 'user_ids': [w.user_id.id]})
    #             self._convert_opportunity(cr, uid, ids, vals, context=context)
    #         elif not context.get('no_force_assignation') or not lead['user_id']:
    #             vals.update({'user_id': w.user_id.id})
    #             lead_obj.write(cr, uid, lead_id, vals, context=context)
    #     else:
    #         lead_ids = context.get('active_ids', [])
    #         vals.update({'lead_ids': lead_ids, 'user_ids': [w.user_id.id]})
    #         self._convert_opportunity(cr, uid, ids, vals, context=context)
    #         for lead in lead_obj.browse(cr, uid, lead_ids, context=context):
    #             if lead.partner_id and lead.partner_id.user_id != lead.user_id:
    #                 partner_obj.write(cr, uid, [lead.partner_id.id], {'user_id': lead.user_id.id}, context=context)
    #                 
    #     if not lead.pan_no:
    #         raise UserError(_("Kindly Fill the PAN No."))
    # 
    #     return self.pool.get('crm.lead').redirect_opportunity_view(cr, uid, lead_ids[0], context=context)
    
class SaleAdvancePaymentInv_extension(models.Model):
    _inherit = "sale.advance.payment.inv"
    
    advance_payment_method = fields.Selection([
        ('delivered', 'Invoiceable lines'),
        ], string='What do you want to invoice?', default= 'delivered' , required=True)
    
class crm_lead2opportunity_partner_mass_extension(models.Model):
    _inherit = 'crm.lead2opportunity.partner.mass'
    
    name = fields.Selection([('convert', 'Convert to opportunity'),], 'Conversion Action', required=True)
