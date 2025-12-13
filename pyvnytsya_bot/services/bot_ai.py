import json
import asyncio
import logging
from ..services.gemini import ai_service
from ..utils.game_utils import format_player_card

logger = logging.getLogger(__name__)

class BotAI:
    async def decide_vote(self, bot_player, room, survivors):
        """
        Decides which player to vote against based on the scenario and revealed traits.
        Returns (target_id, reason).
        """
        try:
            # 1. Prepare Context
            scenario = room.scenario
            
            # Bot's own info
            my_card = format_player_card(bot_player, show_hidden=True)
            
            # Others info (only revealed traits)
            others_info = []
            candidates = []
            
            for p in survivors:
                if p.id == bot_player.id:
                    continue
                
                # Format card with only revealed info
                card_text = format_player_card(p, show_hidden=False)
                others_info.append(f"ID: {p.id}\n{card_text}")
                candidates.append(p.id)
            
            if not candidates:
                return {"target_id": None, "reason": "No one left to vote against."}

            # 2. Construct Prompt
            prompt = (
                f"Ти граєш у гру 'Бункер'. Твоя мета - вижити і потрапити в бункер.\n"
                f"Сценарій катастрофи:\n{scenario}\n\n"
                f"Твоя картка:\n{my_card}\n\n"
                f"Інші гравці (відома інформація):\n" + "\n---\n".join(others_info) + "\n\n"
                f"Тобі потрібно проголосувати проти одного гравця, щоб вигнати його.\n"
                f"Обери того, хто найменш корисний для виживання групи або становить загрозу.\n"
                f"Відповіж у форматі JSON: {{'target_id': <ID гравця>, 'reason': '<Коротке пояснення (1 речення)>'}}"
            )

            # 3. Ask AI
            # We use a lower temperature for more logical decisions if possible, but Gemini config is global.
            # Just ask.
            response = await asyncio.to_thread(ai_service.model.generate_content, prompt)
            response_text = response.text.strip()
            
            # Clean up json markdown
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "")
            
            data = json.loads(response_text)
            target_id = int(data.get("target_id"))
            reason = data.get("reason", "Мені він не подобається.")
            
            # Validate target
            if target_id not in candidates:
                logger.warning(f"Bot {bot_player.id} chose invalid target {target_id}. Picking random.")
                import random
                return {"target_id": random.choice(candidates), "reason": "Я розгубився, тому тицьнув навмання."}
                
            return {"target_id": target_id, "reason": reason}

        except Exception as e:
            logger.error(f"Bot AI Error: {e}")
            # Fallback to random
            import random
            candidates = [p.id for p in survivors if p.id != bot_player.id]
            if candidates:
                return {"target_id": random.choice(candidates), "reason": "Мій нейропроцесор перегрівся."}
            return {"target_id": None, "reason": "Error"}

bot_ai = BotAI()
