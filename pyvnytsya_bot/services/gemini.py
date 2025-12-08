import google.generativeai as genai
from ..config import config

class AIService:
    def __init__(self):
        genai.configure(api_key=config.GEMINI_API_KEY.get_secret_value())
        self.model = genai.GenerativeModel('gemini-2.5-flash') 

    async def generate_scenario(self) -> str:
        prompt = (
            "Ти - ведучий гри 'Бункер'. Придумай короткий, але цікавий сценарій катастрофи. "
            "Опиши, що сталося у світі, чому люди ховаються в бункері, і скільки часу їм там треба просидіти. "
            "Відповідь має бути українською мовою, до 150 слів."
        )
        response = await self.model.generate_content_async(prompt)
        return response.text

    async def generate_ending(self, survivors_info: str) -> str:
        prompt = (
            f"Ти - ведучий гри 'Бункер'. Гра закінчилася. Ось список тих, хто вижив і потрапив у бункер:\n{survivors_info}\n\n"
            "Напиши кінцівку історії. Чи виживуть вони в бункері з такими характеристиками? Що з ними станеться? "
            "Відповідь українською мовою."
        )
        response = await self.model.generate_content_async(prompt)
        return response.text

ai_service = AIService()
