from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        res = super().session_info()
        if self.env.user._is_internal():
            res["allow_chatgpt_bot"] = self.env.user.allow_chatgpt_bot
        return res
