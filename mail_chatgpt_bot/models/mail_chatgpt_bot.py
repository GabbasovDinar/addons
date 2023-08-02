from odoo import _, models

from ..openai_agent import OpenAIAgent


class MailChatgptBot(models.AbstractModel):
    _name = "mail.chatgpt.bot"
    _description = "Mail ChatGPT Bot"

    def _apply_logic(self, record, values, command=None):
        """
        Apply bot logic to generate a response to the user,
        the logic will only be applied if the bot is in a chat with the user.
        """
        bot_id = self.env["ir.model.data"]._xmlid_to_res_id("mail_chatgpt_bot.chatgpt_bot_partner")
        if len(record) != 1 or values.get("author_id") == bot_id or values.get("message_type") != "comment" and not command:
            return
        if self._is_bot_in_private_channel(record):
            body = values.get("body", "").replace(u"\xa0", u" ").strip().lower().strip(".!")
            answer = self._get_answer(record, body, values, command)
            if answer:
                record.with_context(mail_create_nosubscribe=True).sudo().message_post(
                    body=answer,
                    author_id=bot_id,
                    message_type="comment",
                    subtype_id=self.env.ref("mail.mt_note").id,
                )

    def _get_disable_bot_message(self):
        return _("Unfortunately, ChatGPT is no longer available to you.")

    def _get_answer(self, record, body, values, command=False):
        if self._is_bot_in_private_channel(record):
            if not self.env.user.allow_chatgpt_bot:
                return self._get_disable_bot_message()
            if command == "help":
                return self.env["res.users"]._get_welcome_chatgpt_message()
            elif command == "reset_context":
                self._reset_chat_context()
                return _("The chat context has been reset.")
            else:
                return self._get_answer_from_chatgpt(body)
        return False

    def _is_bot_in_private_channel(self, record):
        bot_id = self.env["ir.model.data"]._xmlid_to_res_id("mail_chatgpt_bot.chatgpt_bot_partner")
        if record._name == "mail.channel" and record.channel_type == "chat":
            return bot_id in record.with_context(active_test=False).channel_partner_ids.ids
        return False

    def _reset_conversation_context(self):
        """
        Reset chat context
        """
        # TODO

    def _get_conversation_context(self):
        """
        Get current conversation context
        """
        # TODO

    def _set_conversation_context(self, context):
        """
        Save current chat context
        """

    def _get_answer_from_chatgpt(self, message):
        # TODO: OPENAI_API_KEY, model and etc from settings
        openai_agent = OpenAIAgent(api_key=OPENAI_API_KEY)
        response, context = openai_agent.process_message(message, context=self._get_conversation_context())
        self._set_conversation_context(context)
        return response
