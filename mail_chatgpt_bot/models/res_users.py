from odoo import _, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    allow_chatgpt_bot = fields.Boolean(default=True)

    def _init_messaging(self):
        if self.allow_chatgpt_bot and self._is_internal():
            self._init_chatgptbot()
        return super()._init_messaging()

    def _get_welcome_chatgpt_message(self):
        return _("""
            Hello,<br/>I am <b>ChatGPT Bot</b>, a large language model developed by <b>OpenAI</b>.<br/>
            I am trained to understand and respond to natural language inputs in a human-like manner.<br/>
            I can answer questions, have a conversation, generate text on a topic, and more.<br/>
            I am constantly learning and updating my knowledge base to provide accurate and helpful responses.<br/><br/>
            
            To reset the communication context, simply type <b>/reset_context</b>.
        """)

    def _init_chatgptbot(self):
        self.ensure_one()
        chatgpt_bot_partner_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "mail_chatgpt_bot.chatgpt_bot_partner",
        )
        channel_info = self.env["mail.channel"].channel_get([chatgpt_bot_partner_id, self.partner_id.id])
        channel = self.env["mail.channel"].browse(channel_info["id"])

        message = self._get_welcome_chatgpt_message()
        channel.sudo().message_post(
            body=message,
            author_id=chatgpt_bot_partner_id,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        return channel
