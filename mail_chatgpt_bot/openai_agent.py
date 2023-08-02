import openai


class OpenAIAgent:

    def __init__(self, api_key, temperature=0.8, max_tokens=150, model="gpt-3.5-turbo"):
        openai.api_key = api_key
        self.max_tokens = max_tokens
        self.model = model
        self.temperature = temperature

    def process_message(self, message, context=None):
        if not context:
            context = [{
                "role": "system",
                "content": "The assistant is helpful, creative, smart and very friendly.",
            }]
        context.append({"role": "user", "content": message})

        # Retrieve AI's response from OpenAI API
        response = self.get_ai_response(context)

        # Add AI's response to the conversation history
        context.append({"role": "assistant", "content": response})

        # Return AI's response and context
        return response, context

    def get_ai_response(self, messages):
        # Generate AI's response using OpenAI API
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stop=["assistant", "user"]
        )

        # TODO: check text instead of message
        # Extract AI's response from the API response
        return response.choices[0].message.content.strip()
