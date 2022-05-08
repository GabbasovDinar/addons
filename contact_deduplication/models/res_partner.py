from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    similarity_threshold = fields.Integer(
        readonly=True,
    )
