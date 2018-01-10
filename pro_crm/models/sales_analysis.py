# from datetime import datetime, timedelta
# from openerp import SUPERUSER_ID
# from openerp import api, fields, models, _, tools
# import openerp.addons.decimal_precision as dp
# from openerp.exceptions import UserError
# from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
# from werkzeug import url_encode

from openerp.exceptions import UserError, MissingError, ValidationError
import csv
import base64
import decimal
import openerp

from openerp import models, fields, api, _, tools
from openerp.exceptions import UserError
from datetime import date, datetime , timedelta
import calendar
import time
import logging
from openerp.tools import float_is_zero,openerp,image_colorize, image_resize_image_big
import re , collections
from openerp import http
from openerp.addons.web.controllers.main import serialize_exception,content_disposition
from openerp.http import request, serialize_exception as _serialize_exception
from cStringIO import StringIO
import xlwt
# from datetime import timedelta
from dateutil import relativedelta
import pytz

# from datetime import date
from collections import Counter
import openerp.addons.decimal_precision as dp


class sale_analysis(models.Model):
    _name = 'sale.analysis'
    _rec_name = 'zone'
    
    target = fields.Char(string="Target")
    state = fields.Selection([('draft','Draft'),('product','Product'),('category','Product Category'),('sale_type','Sale Type')], track_visibility='onchange', string="State", default="draft")
    start_date = fields.Date(string="Start Date", default= lambda *a: time.strftime('%Y-04-01'))
     
    end_date = fields.Date(string="End Date")
    zone = fields.Many2one('crm.configuration', string="Zone")
    zsm = fields.Many2one('res.users', related="zone.zonal_sales_manager", string="ZSM")
    sale_analysis_product_one2many  = fields.One2many('sale.analysis.product', 'name', string = "Sale Analysis Product")
    product_category_one2many  = fields.One2many('sale.analysis.product.category', 'name', string = "Sale Analysis Product Category")
    sale_type_one2many  = fields.One2many('sale.type.analysis', 'name', string = "Sales Analysis")
    report_id = fields.Many2one('sale.analysis.report', string= "Sale Analysis Report")
    
    @api.onchange('start_date')
    def onchange_date_end(self):
        if self.start_date:
            t = str(self.start_date)
            d = datetime(*(int(s) for s in t.split('-')))
            self.end_date = d.replace(d.year+1 ,d.month-1,d.day+30)

    @api.multi
    def view_report(self):
        self.calculate_achievement()
        res = self.env['ir.actions.act_window'].for_xml_id('pro_crm', 'action_sale_analysis_report')
        res['res_id'] = self.report_id.id
        return res
    
    @api.multi
    def load_product(self):
        val_product = {}
        result_product = []
        product_obj = self.env['product.product'].search([('can_be_expensed','=', False)])
        for record in product_obj:
            val_product = {
               'name':self.id,
               'product_id': record,
            }
            result_product.append(val_product)
        self.sale_analysis_product_one2many.unlink()
        self.sale_analysis_product_one2many = result_product
        self.state = 'product'
            
        # for cat_name, value in main_cat_dict.iteritems():
        #     percentage =  100*(value['Achieved']/value['Target'])
        #     val_cat = {
        #        'name':self.id,
        #        'categ_id': cat_name,
        #        'target':value['Target'],
        #        'achieved':value['Achieved'],
        #        'balance':value['Balance'],
        #        'percentage':percentage,
        #        
        #     }
        #     result_cat.append(val_cat)
        # self.product_category_one2many.unlink()
        # self.product_category_one2many = result_cat
    
    @api.multi
    def calculate_achievement(self):
        # main_dict = {}
        # ref_dict = {}
        # for sale_analysis_line in self.sale_analysis_product_one2many:
        #     main_dict[sale_analysis_line.product_id.name] = {
        #         'target':sale_analysis_linetarget or 0,
        #         'achieved':0,
        #         'balance':0,
        #         'achieved_percentage':0
        #     }
        #     ref_dict[sale_analysis_line.product_id.name] = []
        # sale_obj = self.env['sale.order.line'].search([('state','in',('sale','done'))])  #,('create_date','>=',rec.start_date),('create_date','<=',rec.end_date)
        # for record in sale_obj:
        #     category_name = record.product_id.product_tmpl_id.categ_id.name
        #     product_name = record.product_id.name
        #     # if category_name not in main_dict:
        #     #     main_dict[category_name] = {}
        #     if product_name in ref_dict and ref_dict[product_name]:
        #         test = ref_dict[product_name] or []
        #         ref_dict[product_name] = test.append(record)
        #     else:
        #         ref_dict[product_name] = [record]

        # for key, value in ref_dict.iteritems():

        #     target = 0
        #     achieved = 0
        #     balance = 0
        #     achieved_percentage = 0.0

        #     for sale_obj in value:
        #         achieved += sale_obj.product_uom_qty

        


        # for key, value in main_dict.iteritems():
        #     pass

        # html = '<table><tr><th>' + '</th><th>'.join(main_dict.keys()) + '</th></tr>'
        
        # for key, value in main_dict.iteritems():
        #     html += '<tr><td>' + '</td><td>'.join(value) + '</td></tr>'
        
        # html += '</table>'
        
        # res = self.report_id.create({'name': self.id, 'report': html})
        
        # self.report_id = res.id
        
        # 
        # print html
        # raise UserError(html)

        # print "PPPPPPPPP",main_dict
        
        start_date_string = str(self.start_date)
        start_time_string = "00:00:00"
        end_date_string = str(self.end_date)
        end_time_string = "00:00:00"
        
        st_date =  datetime.combine(datetime.strptime(start_date_string, "%Y-%m-%d") ,datetime.strptime(start_time_string,"%H:%M:%S").time())
        
        en_date =  datetime.combine(datetime.strptime(end_date_string, "%Y-%m-%d") ,datetime.strptime(end_time_string,"%H:%M:%S").time())
        
        start_date = str(st_date)
        end_date = str(en_date)
        stylecase_body = """
        <style>
table tr th, table tr th {
	border: 1px solid black;
}
			</style> """

        main_dict = {}
        for rec in self:
            if rec.start_date and rec.end_date:
                for record in rec.sale_analysis_product_one2many:
                    if record.target != 0.0 :
                        sale_obj = self.env['sale.order.line'].search([('product_id','=',record.product_id.id),('zone','=',record.zone.id),('state','in',('sale','done')),('create_date','>=',start_date),('create_date','<=',end_date)])
                        achieved = 0
                        for x in sale_obj:
                            values = {
                                    'product_id': record.product_id.id or False,
                                    'product_id.product_tmpl_id.categ_id': record.product_categ_id.id or False,
                                }
                            achieved += x.product_uom_qty
                        record.achieved = achieved
                        record.balance = record.target - record.achieved
                        record.percentage =  round(100*(record.achieved/record.target) if record.target != 0 else 0 , 2)
                        main_dict[record.product_id.id] = [str(record.target),str(record.achieved),str(record.balance),str(record.percentage)]
                    else:
                      record.unlink()
                
                
                
                
            # for rec in rec.product_category_one2many:
            #     product_obj = self.env['sale.analysis.product'].search([('product_categ_id','=',rec.categ_id.id)])
            #     rec.categ_id = product_obj

        table_rows = {0:'',1:'Target',2:'Achieved',3:'Balance',4:'% Achieved'}

        html_body = """"""
        i = 0
        for key,value in table_rows.iteritems():
            html_body += "<tr style='border: 1px solid black;'>"
            if i == 0:
                html_body += "<th style='border: 1px solid black;'>"+value+"</th>"
            else:
                html_body += "<td style='border: 1px solid black;'>"+value+"</td>"
            for record in rec.sale_analysis_product_one2many:
                if i == 0:
                    html_body += "<th style='border: 1px solid black;'>"+record.product_id.name+"</th>"
                else:
                    html_body += "<td style='border: 1px solid black;'>" + main_dict[record.product_id.id][i-1] + "</td>"
                    # print "VVVVVVVVVVVV",record.product_id.name, main_dict[record.product_id.id]
            html_body += "</tr>"
            i += 1
        
        html = """
<table class="table">
    <tbody>
    %s
    </tbody>
</table>
""" % html_body
        
        # print "HHHHHHHHHHHHHHHH",html

        # res = self.report_id.create({'name': self.id, 'report': html})
        
        # self.report_id = res.id
        
        
        #---------------------- Category Wise ------------------#
        main_cat_dict = {}
        val_cat = {}
        result_cat = []
        for rec_cat in self.sale_analysis_product_one2many:
            main_cat_dict[rec_cat.product_categ_id.id] = {'Target':0,'Achieved':0,'Balance':0}
            
        for rec_cat in self.sale_analysis_product_one2many:
            main_cat_dict[rec_cat.product_categ_id.id]['Target'] += rec_cat.target 
            main_cat_dict[rec_cat.product_categ_id.id]['Achieved'] += rec_cat.achieved
            main_cat_dict[rec_cat.product_categ_id.id]['Balance'] += rec_cat.balance
        
        # print "SSSSSSSSSSSSSSSSSSSS",main_cat_dict
        
        
        for cat_name, value in main_cat_dict.iteritems():
            percentage =  round(100*(value['Achieved']/value['Target']) if value['Target'] != 0 else 0 , 2)
            val_cat = {
               'name':self.id,
               'categ_id': cat_name,
               'target':value['Target'],
               'achieved':value['Achieved'],
               'balance':value['Balance'],
               'percentage':percentage,
               
            }
            result_cat.append(val_cat)
        self.product_category_one2many.unlink()
        self.product_category_one2many = result_cat
        
        table_rows1 = {0:'',1:'Target',2:'Achieved',3:'Balance',4:'% Achieved'}

        html_body1 = """"""
        i = 0
        for key,value in table_rows1.iteritems():
            html_body1 += "<tr style='border: 1px solid black;'>"
            if i == 0:
                html_body1 += "<th style='border: 1px solid black;'>"+value+"</th>"
            else:
                html_body1 += "<td style='border: 1px solid black;'>"+value+"</td>"
            for record in self.product_category_one2many:
                if i == 0:
                    html_body1 += "<th style='border: 1px solid black;'>"+record.categ_id.name+"</th>"
                else:
                    if value == "% Achieved":
                        html_body1 += "<td style='border: 1px solid black;'>%s</td>" % record.percentage
                    else:
                        html_body1 += "<td style='border: 1px solid black;'>%s</td>" % main_cat_dict[record.categ_id.id][value]
                    # print "VVVVVVVVVVVV",record.product_id.name, main_dict[record.product_id.id]
            html_body1 += "</tr>"
            i += 1
        
        html1 = """
<table class="table">
    <tbody>
    %s
    </tbody>
</table>
""" % html_body1
        
        # print "HHHHHHHHHHHHHHHH",html

        res = self.report_id.create({'name': self.id, 'report':  "<h2>Sale Analysis Product Wise</h2><br/>" + html  + stylecase_body + "<br/><br/><h2>Sale Analysis Product Category Wise</h2><br/>" + html1})
        
        self.report_id = res.id
        #---------------------- Category Wise ------------------#
    
    
class sale_analysis_product(models.Model):
    _name = 'sale.analysis.product'
    
    name = fields.Many2one('sale.analysis', string= "Sale Analysis Product")
    zone = fields.Many2one('crm.configuration', related="name.zone",  string="Zone")
    product_id = fields.Many2one('product.product', string="Product")
    product_categ_id = fields.Many2one('product.category', related="product_id.product_tmpl_id.categ_id", string="Product Category")
    target = fields.Float(string="Target")
    achieved = fields.Float(string="Achieved")
    balance = fields.Float(string="Balance")
    percentage = fields.Float(string="Percentage")
    start_date = fields.Date(string="Start Date", related="name.start_date")
    end_date = fields.Date(string="End Date", related="name.end_date")
    

class sale_analysis_report(models.Model):
    _name = 'sale.analysis.report'
    
    name = fields.Many2one('sale.analysis', string= "Sale Analysis Report")
    report = fields.Html(string="Report")
    report_display = fields.Html(string="Report", related="report")
    

    
class sale_type_analysis(models.Model):
    _name = 'sale.type.analysis'
    
    name = fields.Many2one('sale.analysis', string= "Sale Analysis Product Category")
    categ_id = fields.Many2one('product.category', string="Product Category")
    target = fields.Float(string="Target")
    achieved = fields.Float(string="Achieved")
    balance = fields.Float(string="Balance")
    percentage = fields.Float(string="Percentage")
    
class sale_analysis_product_category(models.Model):
    _name = 'sale.analysis.product.category'
    
    name = fields.Many2one('sale.analysis', string= "Sale Analysis Product Category")
    categ_id = fields.Many2one('product.category', string="Product Category")
    target = fields.Float(string="Target")
    achieved = fields.Float(string="Achieved")
    balance = fields.Float(string="Balance")
    percentage = fields.Float(string="Percentage")
    
# class sale_analysis_zone(models.Model):
#     _name = 'sale.analysis.zone'
#     
#     start_date = fields.Datetime(string="Start Date", related="name.start_date")
#     end_date = fields.Datetime(string="End Date", related="name.end_date")
#     sale_analysis_one2many = fields.One2many('sale.analysis', 'zone', string = "Sales Analysis")