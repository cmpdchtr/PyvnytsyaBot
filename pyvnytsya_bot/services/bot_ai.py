import json
import asyncio
import logging
import random
from ..utils.game_utils import format_player_card

logger = logging.getLogger(__name__)

class BotAI:
    def __init__(self):
        # --- EXTENDED HEURISTIC KEYWORDS FOR CUSTOM PACK SUPPORT ---
        # These lists cover common tropes in survival games (Fantasy, Sci-Fi, Horror, Realism)
        # to support custom packs without AI analysis.

        self.bad_health_keywords = [
            # UA
            "ВІЛ", "Рак", "Коронавірус", "Шизофренія", "Туберкульоз", "Гепатит", 
            "Сифіліс", "Сліпота", "Німота", "Параліч", "Відсутність", "Наркоманія", 
            "Алкоголізм", "Ігроманія", "Депресія", "Епілепсія", "Інсульт", "Інфаркт",
            "Хвор", "Вірус", "Інфекц", "Пухлин", "Перелом", "Травм", "Поранен", "Біль", 
            "Смерть", "Мертв", "Слабк", "Глух", "Божевіл", "Псих", "Втом", "Голод", 
            "Спраг", "Отру", "Токсин", "Радіац", "Зараж"
        ]
        
        self.good_health_keywords = [
            # UA
            "Ідеальне", "Здоровий", "Спортсмен", "Сильн", "Міцн", "Фітнес", "Атлет"
        ]
        
        self.bad_professions = [
            # UA
            "Блогер", "Тіктокер", "Астролог", "Таролог", "Клоун", "Стриптизерша", 
            "Безробітний", "Майнер", "Порноактор", "Бомж", "Дегустатор", "Випробувач",
            "Стример", "Ютубер", "Інфлюенсер", "Модель", "Фотограф", "Дизайнер", "Стиліст", 
            "Візажист", "Перукар", "Барбер", "Манікюр", "Масажист", "Нумеролог", "Ворожк", 
            "Екстрасенс", "Мім", "Актор", "Артист", "Співак", "Музикант", "Діджей", "Танцюрист", 
            "Комік", "Поет", "Письменник", "Художник", "Скульптор", "Жебрак", "Злодій", 
            "Шахрай", "Бандит", "Кілер", "Вбивця", "Маніяк", "Ґвалтівник", "Педофіл", "Наркоман", "Алкаш"
        ]
        
        self.good_professions = [
            # UA
            "Лікар", "Хірург", "Військовий", "Інженер", "Фермер", "Механік", 
            "Електрик", "Будівельник", "Біолог", "Хімік", "Пожежник", "Поліцейський",
            "Доктор", "Медик", "Медсестр", "Фармацевт", "Вчен", "Наук", "Технік", 
            "Архітектор", "Агроном", "Садівник", "Мисливець", "Рибалка", "Кухар", "Повар", 
            "Пекар", "Вчитель", "Викладач", "Тренер", "Солдат", "Офіцер", "Сержант", 
            "Генерал", "Коп", "Охоронець", "Рятувальник"
        ]
        
        self.useful_inventory = [
            # UA
            "Аптечка", "Ніж", "Сокира", "Зброя", "Їжа", "Вода", "Ліки", "Намет", 
            "Спальний мішок", "Рація", "Генератор", "Паливо", "Інструменти",
            "Таблетк", "Бинт", "Спирт", "Йод", "Зеленк", "Антибіотик", "Знеболююч", "Вітамін", 
            "Молоток", "Пил", "Лопат", "Пістолет", "Автомат", "Рушниц", "Набо", "Патрон", 
            "Куля", "Гранат", "Вибухівк", "Хліб", "Консерв", "Ковдр", "Одяг", "Взутт", 
            "Сірник", "Запальничк", "Вогон", "Ліхтар", "Батарейк", "Акумулятор", "Бензин", 
            "Солярк", "Мап", "Компас", "Телефон"
        ]

    def check_keyword(self, text, keywords):
        """Case-insensitive partial match."""
        text = text.lower()
        for k in keywords:
            if k.lower() in text:
                return True
        return False

    def analyze_scenario(self, text):
        """Simple keyword matching to guess scenario type."""
        text = text.lower()
        tags = []
        if any(w in text for w in ["зима", "холод", "сніг", "мороз", "льодовиковий"]):
            tags.append("cold")
        if any(w in text for w in ["вірус", "епідемія", "хвороба", "зараження", "зомбі"]):
            tags.append("bio")
        if any(w in text for w in ["війна", "ядерна", "вибух", "радіація", "бомба"]):
            tags.append("war")
        if any(w in text for w in ["повінь", "вода", "цунамі", "океан"]):
            tags.append("flood")
        if any(w in text for w in ["голод", "посуха", "пустеля"]):
            tags.append("famine")
        return tags

    async def decide_votes_batch(self, bots, room, survivors):
        """
        Decides votes for multiple bots using heuristic logic (no AI API).
        Returns a dict: {bot_id: {'target_id': int, 'reason': str}}
        """
        try:
            results = {}
            scenario_tags = self.analyze_scenario(room.scenario or "")
            
            # Pre-calculate scores for all survivors
            scores = {} # target_id -> {score: int, reasons: [str]}
            
            for p in survivors:
                score = 0
                reasons = []
                
                # Parse traits from revealed info
                revealed = p.revealed_traits.split(",") if p.revealed_traits else []
                
                # --- 1. Health Analysis ---
                if "health" in revealed:
                    health_val = p.health
                    if self.check_keyword(health_val, self.bad_health_keywords):
                        penalty = 50
                        if "bio" in scenario_tags and self.check_keyword(health_val, ["ВІЛ", "Гепатит", "Туберкульоз", "Зараж", "Contagious", "Virus"]):
                            penalty += 30 # Extra penalty for contagious diseases in bio scenario
                            reasons.append(f"заразний ({health_val})")
                        else:
                            reasons.append(f"хворий ({health_val})")
                        score += penalty
                    elif self.check_keyword(health_val, self.good_health_keywords):
                        score -= 20
                        
                # --- 2. Profession Analysis ---
                if "profession" in revealed:
                    prof_val = p.profession
                    if self.check_keyword(prof_val, self.bad_professions):
                        score += 30
                        reasons.append(f"марна професія ({prof_val})")
                    elif self.check_keyword(prof_val, self.good_professions):
                        bonus = 30
                        # Scenario bonuses
                        if "war" in scenario_tags and self.check_keyword(prof_val, ["Військовий", "Soldier", "Military", "Officer"]): bonus += 20
                        if "bio" in scenario_tags and self.check_keyword(prof_val, ["Лікар", "Біолог", "Doctor", "Medic", "Biologist"]): bonus += 20
                        if "cold" in scenario_tags and self.check_keyword(prof_val, ["Інженер", "Будівельник", "Engineer", "Builder"]): bonus += 20
                        score -= bonus
                
                # --- 3. Age Analysis ---
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
                            if "war" in scenario_tags or "cold" in scenario_tags:
                                score -= 10 # Prime age bonus for harsh conditions
                    except: pass

                # --- 4. Inventory Analysis ---
                if "inventory" in revealed:
                    inv_val = p.inventory
                    if self.check_keyword(inv_val, self.useful_inventory):
                        score -= 15
                        if "cold" in scenario_tags and self.check_keyword(inv_val, ["Одяг", "Ковдра", "Вогонь", "Clothes", "Blanket", "Fire"]):
                            score -= 20
                        if "war" in scenario_tags and self.check_keyword(inv_val, ["Зброя", "Рація", "Weapon", "Radio"]):
                            score -= 20
                    
                    if self.check_keyword(inv_val, ["Зброя", "Пістолет", "Weapon", "Gun", "Rifle"]):
                        # Weapon is double-edged: useful in war, threat otherwise
                        if "war" in scenario_tags or "zombie" in scenario_tags:
                            score -= 10
                        else:
                            score += 10 
                            reasons.append("має зброю (небезпечний)")

                # --- 5. Phobia Analysis (Scenario specific) ---
                if "phobia" in revealed:
                    phobia_val = p.phobia
                    if "cold" in scenario_tags and ("Холод" in phobia_val or "Сніг" in phobia_val):
                        score += 40
                        reasons.append(f"боїться холоду")
                    if "flood" in scenario_tags and ("Вода" in phobia_val):
                        score += 40
                        reasons.append(f"боїться води")
                    if "war" in scenario_tags and ("Кров" in phobia_val or "Гучні звуки" in phobia_val):
                        score += 30
                        reasons.append(f"не підходить для війни")

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

bot_ai = BotAI()
