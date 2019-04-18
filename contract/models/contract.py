# -*- coding: utf-8 -*-
import datetime
from openerp import _, api, fields, models


class Contract(models.Model):
    _name = "contract"
    _description = "Contract Management"
    _order = 'create_date desc, id desc'

    state = fields.Selection([
            ('draft', 'Draft'),
            ('published', 'Published'),
            ('rejected', 'Rejected'),
            ('assigned', 'Assigned'),
            ('complete', 'Complete'),
            ('closed', 'Done')
    ], string='Status', index=True, readonly=True, default='draft')
    name = fields.Char(string="Name", readonly=True, states={'draft': [('readonly', False)]})
    description = fields.Text(string="Description", readonly=True, states={'draft': [('readonly', False)]})
    author_id = fields.Many2one("res.users", string="Author", default=lambda self: self.env.user, readonly=True)
    worker_id = fields.Many2one("res.users", readonly=True, states={'published': [('readonly', False)]},
                                string="Worker", domain=lambda self: self._domain_worker())
    create_date = fields.Date(string="Create Date", default=datetime.datetime.now(), readonly=True)
    publish_date = fields.Date(string="Publish Date", readonly=True)
    close_date = fields.Date(string="Close Date", readonly=True)
    reject_date = fields.Date(string="Reject Date", readonly=True)

    def _domain_worker(self):
        worker_group_id = self.env.ref('base.group_contract_worker')
        return [("groups_id", "in", [worker_group_id.id])]

    @api.multi
    def action_publish_contract(self):
        self.ensure_one()
        self.write({
            'state': 'published',
            'publish_date': datetime.datetime.now()
        })

    @api.multi
    def action_approve_contract(self):
        self.ensure_one()
        self.write({
            'state': 'assigned',
            'worker_id': self.env.user.id
        })
        template_id = self.env.ref('contract.contract_email_template_assigned')
        template_id.send_mail(self.id, True)

    @api.multi
    def action_complete_contract(self):
        self.ensure_one()
        self.write({
            'state': 'complete',
        })
        template_id = self.env.ref('contract.contract_email_template_complete')
        template_id.send_mail(self.id, True)

    @api.multi
    def action_reject_contract(self):
        self.ensure_one()
        self.write({
            'state': 'rejected',
            'reject_date': datetime.datetime.now()
        })
        template_id = self.env.ref('contract.contract_email_template_rejected')
        template_id.send_mail(self.id, True)

    @api.multi
    def action_revise_contract(self):
        self.ensure_one()
        self.write({
            'state': 'assigned',
        })
        template_id = self.env.ref('contract.contract_email_template_revised')
        template_id.send_mail(self.id, True)

    @api.multi
    def action_close_contract(self):
        self.ensure_one()
        self.write({
            'state': 'closed',
            'close_date': datetime.datetime.now()
        })
        template_id = self.env.ref('contract.contract_email_template_closed')
        template_id.send_mail(self.id, True)

    @api.multi
    def write(self, vals):
        res = super(Contract, self).write(vals)
        if vals.get('worker_id') and self.state == 'published':
            self.write({
                'state': 'assigned',
                'worker_id': vals.get('worker_id')
            })
            template_id = self.env.ref('contract.contract_email_template_assigned')
            template_id.send_mail(self.id, True)
        return res
