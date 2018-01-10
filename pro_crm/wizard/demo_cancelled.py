# -*- coding: utf-8 -*-
from openerp import api, fields, models


class demo_cancelled(models.TransientModel):
    _name = 'demo.cancelled'
    _description = 'Cancellation Reason'

    demo_id = fields.Many2one('crm.indent', string="Demo")
    demo_reason_id = fields.Char(string="Reason for Cancellation/Rejection")
    # status = fields.Char(string="Status")

    @api.multi
    def action_demo_cancel_reason_apply(self):
        res = False
        print'DDDDDDDDDDDDDDDDDDDDDDDD',self.id,self.demo_id.id , self.demo_id.state
        if self.demo_id.state == 'draft':
            self.demo_id.cancellation_reason = self.demo_reason_id
            self.demo_id.state = 'cancel'
        elif self.demo_id.state == 'zsmaprvl':
            self.demo_id.rejection_reason = self.demo_reason_id
            self.demo_id.state = 'zsmrejctd'
        elif self.demo_id.state == 'logaprvl':
            self.demo_id.rejection_reason = self.demo_reason_id
            self.demo_id.state = 'logrejctd'
        elif self.demo_id.state == 'ceoaprvl':
            self.demo_id.cancellation_reason = self.demo_reason_id
            self.demo_id.state = 'cancel'
        return res
