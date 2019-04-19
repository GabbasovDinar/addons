from odoo import models, fields, api


class Project(models.Model):
    _inherit = "project.project"

    is_template = fields.Boolean(string="Is Template", default=False, copy=False)
    use_template = fields.Boolean(string="Use Template", copy=False)
    template_id = fields.Many2one("project.project", string="Template",
                                  domain="[('is_template', '=', True)]", copy=False)
    template_is_active = fields.Boolean(string="Active", default=True, copy=False)

    @api.model
    def create(self, values):
        if values.get('use_template') and values.get('template_id'):
            template_id = values.get('template_id')
            values.update({
                'is_template': False,
                'use_template': False,
                'template_id': False,
            })
            return self.browse(template_id).copy(values)
        if self._context.get('default_is_template'):
            values.update({
                'is_template': True
            })
        return super(Project, self).create(values)
