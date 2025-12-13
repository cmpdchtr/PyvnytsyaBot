import json
import asyncio
import logging
import random
from ..utils.game_utils import format_player_card

logger = logging.getLogger(__name__)

class BotAI:
    def __init__(self):
        # Keywords for scoring (heuristic logic)
        self.bad_health_keywords = [
            "ВІЛ", "Рак", "Коронавірус", "Шизофренія", "Туберкульоз", "Гепатит", 
            "Сифіліс", "Сліпота", "Німота", "Параліч", "Відсутність", "Наркоманія", 
            "Алкоголізм", "Ігроманія", "Депресія", "Епілепсія", "Інсульт", "Інфаркт"
        ]
        self.good_health_keywords = ["Ідеальне", "Здоровий", "Спортсмен"]
        
        self.bad_professions = [
            "Блогер", "Тіктокер", "Астролог", "Таролог", "Клоун", "Стриптизерша", 
            "Безробітний", "Майнер", "Порноактор", "Бомж", "Дегустатор", "Випробувач"
        ]
        self.good_professions = [
            "Лікар", "Хірург", "Військовий", "Інженер", "Фермер", "Механік", 
            "Електрик", "Будівельник", "Біолог", "Хімік", "Пожежник", "Поліцейський"
        ]
        
        self.useful_inventory = [
            "Аптечка", "Ніж", "Сокира", "Зброя", "Їжа", "Вода", "Ліки", "Намет", 
            "Спальний мішок", "Рація", "Генератор", "Паливо", "Інструменти"
        ]

    async def decide_votes_batch(self, bots, room, survivors):
        """
        Decides votes for multiple bots using heuristic logic (no AI API).
        Returns a dict: {bot_id: {'target_id': int, 'reason': str}}
        """
        try:
            results = {}
            
            # Pre-calculate scores for all survivors
            scores = {} # target_id -> {score: int, reasons: [str]}
            
            for p in survivors:
                score = 0
                reasons = []
                
                # Parse traits from revealed info
                # Note: We only use revealed traits to be fair
                revealed = p.revealed_traits.split(",") if p.revealed_traits else []
                
                # 1. Health Analysis
                if "health" in revealed:
                    health_val = p.health
                    if any(k in health_val for k in self.bad_health_keywords):
                        score += 50
                        reasons.append(f"хворий ({health_val})")
                    elif any(k in health_val for k in self.good_health_keywords):
                        score -= 20
                        
                # 2. Profession Analysis
                if "profession" in revealed:
                    prof_val = p.profession
                    if any(k in prof_val for k in self.bad_professions):
                        score += 30
                        reasons.append(f"марна професія ({prof_val})")
                    elif any(k in prof_val for k in self.good_professions):
                        score -= 30
                
                # 3. Age Analysis
                if "age" in revealed:
                    try:
                        age = int(p.age)
                        if age > 70:
                            score += 20
                            reasons.append(f"старий ({age})")
                        elif age < 12:
                            score += 15
                            reasons.append(f"дитина ({age})")
                        elif 20 <= age <= 40:
                            score -= 10
                    except: pass

                # 4. Inventory Analysis
                if "inventory" in revealed:
                    inv_val = p.inventory
                    if any(k in inv_val for k in self.useful_inventory):
                        score -= 15
                    if "Зброя" in inv_val or "Пістолет" in inv_val:
                        score += 10 # Potential threat
                        reasons.append("має зброю")

                scores[p.id] = {"score": score, "reasons": reasons}

            # Decide for each bot
            for bot in bots:
                # Filter candidates (exclude self)
                candidates = [pid for pid in scores.keys() if pid != bot.id]
                
                if not candidates:
                    continue
                    
                # Add some randomness to scores to avoid all bots voting same
                bot_candidates = []
                for cid in candidates:
                    base_score = scores[cid]["score"]
                    # Random variance +/- 15
                    final_score = base_score + random.randint(-15, 15)
                    bot_candidates.append((cid, final_score))
                
                # Sort by score descending (highest score = worst player)
                bot_candidates.sort(key=lambda x: x[1], reverse=True)
                
                # Pick top candidate
                target_id = bot_candidates[0][0]
                target_reasons = scores[target_id]["reasons"]
                
                reason_text = "Мені він не подобається."
                if target_reasons:
                    reason_text = f"Він {random.choice(target_reasons)}."
                elif scores[target_id]["score"] > 20:
                    reason_text = "Він виглядає підозріло."
                else:
                    reason_text = "Інтуїція підказує."

                results[bot.id] = {
                    "target_id": target_id,
                    "reason": reason_text
                }
            
            return results

        except Exception as e:
            logger.error(f"Bot Heuristic Error: {e}")
            return {}

    async def decide_vote(self, bot_player, room, survivors):
        # Legacy wrapper for single vote if needed
        res = await self.decide_votes_batch([bot_player], room, survivors)
        return res.get(bot_player.id, {"target_id": None, "reason": "Error"})
            candidates = [p.id for p in survivors if p.id != bot_player.id]
            if candidates:
                return {"target_id": random.choice(candidates), "reason": "Мій нейропроцесор перегрівся."}
            return {"target_id": None, "reason": "Error"}

bot_ai = BotAI()
