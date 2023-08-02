from odoo import api, models, _


class Channel(models.Model):
    _inherit = "mail.channel"

    def execute_command_help(self, **kwargs):
        super().execute_command_help(**kwargs)
        self.env["mail.chatgpt.bot"]._apply_logic(
            self,
            kwargs,
            command="help",
        )

    # TODO: where we need call this method?
    def execute_command_reset_context(self, **kwargs):
        self.env["mail.chatgpt.bot"]._apply_logic(
            self,
            kwargs,
            command="reset_context",
        )
