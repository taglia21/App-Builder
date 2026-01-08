"""AI Service wrapper."""

import openai
from typing import Optional, List, Dict, Any
from app.core.config import settings

class AIService:
    def __init__(self):
        # self.api_key = settings.OPENAI_API_KEY
        # self.client = openai.OpenAI(api_key=self.api_key)
        self.default_model = "gpt-3.5-turbo"

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text using OpenAI."""
        # messages = []
        # if system_prompt:
        #     messages.append({"role": "system", "content": system_prompt})
        # messages.append({"role": "user", "content": prompt})

        try:
            # response = self.client.chat.completions.create(
            #     model=self.default_model,
            #     messages=messages,
            #     temperature=0.7,
            # )
            # return response.choices[0].message.content
            return "This is a mock AI response. Configure OPENAI_API_KEY to enable real responses."
        except Exception as e:
            print(f"Error calling OpenAI: {e}")
            return ""

    def generate_json(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate JSON response (simplified wrapper)."""
        system_prompt = "You are a JSON generator. Respond with valid JSON only."
        text = self.generate_text(prompt + "\n\nRespond with JSON matching this schema: " + str(schema), system_prompt)
        import json
        try:
            return json.loads(text)
        except:
            return {}

ai_service = AIService()
