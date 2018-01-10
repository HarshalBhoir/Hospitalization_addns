
from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _, tools
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from werkzeug import url_encode


class crm_configuration(models.Model):
    _name = 'crm.configuration'
    
    name = fields.Char(string="Zone")
    zonal_sales_manager = fields.Many2one('res.users', string='Zonal Sales Manager')
    zone_code = fields.Char(string="Zone Code")
    
