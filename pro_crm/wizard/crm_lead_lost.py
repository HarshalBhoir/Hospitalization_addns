# -*- coding: utf-8 -*-
from openerp import api, fields, models


class CrmLeadLost_Extension(models.TransientModel):
    _name = 'crm.lead.lost.extension'
    _description = 'Get Lost Reason'

    lead_id = fields.Many2one('crm.lead', 'Lead')
    lost_reason_id = fields.Many2one('lost.reason', 'Lost Reason')

    @api.multi
    def action_lost_reason_apply(self):
        res = False
        for wizard in self:
            self.lead_id.lead_lost_reason = self.lost_reason_id
            res = self.lead_id.action_set_lost()
        return res


class lost_reason(models.Model):
    _name = 'lost.reason'
    
    name = fields.Char(string="Lost Reason")
