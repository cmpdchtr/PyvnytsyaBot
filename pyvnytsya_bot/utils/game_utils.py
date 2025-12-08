import random

PROFESSIONS = ["Лікар", "Інженер", "Вчитель", "Військовий", "Програміст", "Кухар", "Психолог", "Механік"]
HEALTH = ["Ідеальне", "Астма", "Безпліддя", "Короткозорість", "Діабет", "Алергія на пил", "Хронічна втома"]
HOBBIES = ["Риболовля", "Шахи", "Стрільба", "Садівництво", "В'язання", "Покер", "Альпінізм"]
PHOBIAS = ["Клаустрофобія", "Арахнофобія", "Темрява", "Висота", "Кров", "Змії", "Замкнутий простір"]
INVENTORY = ["Ніж", "Аптечка", "Ліхтарик", "Рація", "Пляшка води", "Сірники", "Карта", "Компас"]
FACTS = ["Вміє водити літак", "Знає азбуку Морзе", "Має чорний пояс з карате", "Колишній в'язень", "Виграв в лотерею"]

def generate_characteristics():
    return {
        "profession": random.choice(PROFESSIONS),
        "health": random.choice(HEALTH),
        "hobby": random.choice(HOBBIES),
        "phobia": random.choice(PHOBIAS),
        "inventory": random.choice(INVENTORY),
        "fact": random.choice(FACTS)
    }
