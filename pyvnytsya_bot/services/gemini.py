import asyncio
from goodbye_quota import GoodbyeQuota
from ..config import config

class AIService:
    def __init__(self):
        keys = [config.GEMINI_API_KEY.get_secret_value()]
        self.client = GoodbyeQuota(keys)
        self.model = self.client.create_model('gemini-2.5-flash-lite') 

    async def generate_scenario(self, custom_prompt: str = None) -> str:
        base_instruction = (
            "Ти - ведучий гри 'Бункер'. Придумай сценарій катастрофи. "
            "Будь лаконічним. Максимум 150 слів.\n"
            "Твоя відповідь має містити такі пункти:\n"
            "1. **Катастрофа**: Коротко, що сталося.\n"
            "2. **Бункер**: Площа (м²), що працює, що зламано.\n"
            "3. **Умови**: Час перебування.\n"
            "Відповідь українською мовою. Без зайвої води."
        )
        
        if custom_prompt:
            prompt = f"{base_instruction}\n\nВрахуй наступні побажання або сеттінг: {custom_prompt}"
        else:
            prompt = base_instruction

        response = await asyncio.to_thread(self.model.generate_content, prompt)
        return response.text

    async def generate_ending(self, survivors_info: str, scenario: str, custom_prompt: str = None) -> str:
        base_instruction = (
            f"Ти - ведучий гри 'Бункер'. Гра закінчилася.\n\n"
            f"📜 **Початковий сценарій:**\n{scenario}\n\n"
            f"👥 **Список тих, хто залишився в бункері:**\n{survivors_info}\n\n"
            "Напиши коротку кінцівку історії (максимум 200 слів). Твоє завдання:\n"
            "1. Проаналізувати склад групи (професії, хвороби).\n"
            "2. Коротко описати, як пройшов час у бункері.\n"
            "3. **Зробити чіткий висновок**: ЧИ ВИЖИЛА ГРУПА? (Так/Ні/Частково).\n"
            "Відповідь українською мовою. Пиши стисло."
        )

        if custom_prompt:
            prompt = f"{base_instruction}\n\nВрахуй наступні побажання або сеттінг для кінцівки: {custom_prompt}"
        else:
            prompt = base_instruction
        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            if response and response.text:
                return response.text
            else:
                return "Історія завершилася мовчанням..."
        except Exception as e:
            raise Exception(f"Failed to generate ending: {e}")

ai_service = AIService()
