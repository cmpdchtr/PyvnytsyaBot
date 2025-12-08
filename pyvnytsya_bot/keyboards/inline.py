from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Створити кімнату", callback_data="create_room")
    builder.button(text="🔑 Приєднатися", callback_data="join_room")
    builder.button(text="📜 Правила", callback_data="rules")
    builder.adjust(1)
    return builder.as_markup()

def room_creator_menu(room_code: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Почати гру", callback_data=f"start_game_{room_code}")
    builder.button(text="🤖 Додати бота", callback_data=f"add_bot_{room_code}")
    builder.button(text="⚙️ Налаштування", callback_data=f"settings_{room_code}")
    builder.button(text="❌ Видалити кімнату", callback_data=f"delete_room_{room_code}")
    builder.adjust(1)
    return builder.as_markup()

def room_player_menu(room_code: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Мій статус", callback_data=f"my_status_{room_code}")
    builder.button(text="🚪 Вийти", callback_data=f"leave_room_{room_code}")
    builder.adjust(1)
    return builder.as_markup()

def back_to_main() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 На головну", callback_data="main_menu")
    return builder.as_markup()

# --- Game Keyboards ---

def game_dashboard(room_code: str, is_alive: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_alive:
        builder.button(text="🃏 Відкрити карту", callback_data=f"reveal_menu_{room_code}")
    builder.button(text="👀 Стіл гравців", callback_data=f"view_table_{room_code}")
    builder.button(text="🔄 Оновити", callback_data=f"refresh_game_{room_code}")
    builder.adjust(1)
    return builder.as_markup()

def reveal_menu(room_code: str, revealed_traits: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    traits = {
        "profession": "🛠 Професія",
        "health": "❤️ Здоров'я",
        "hobby": "🎨 Хобі",
        "phobia": "😱 Фобія",
        "inventory": "🎒 Інвентар",
        "fact": "ℹ️ Факт",
        "bio": "⚧ Стать",
        "age": "🎂 Вік"
    }
    
    for key, label in traits.items():
        if key not in revealed_traits:
            builder.button(text=label, callback_data=f"reveal_{key}_{room_code}")
            
    builder.button(text="🔙 Назад", callback_data=f"back_to_game_{room_code}")
    builder.adjust(2)
    return builder.as_markup()

def voting_menu(room_code: str, players: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for player in players:
        if player.is_alive:
            name = player.user.full_name or player.user.username
            builder.button(text=f"💀 {name}", callback_data=f"vote_{player.id}_{room_code}")
    builder.adjust(1)
    return builder.as_markup()

def admin_game_menu(room_code: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Почати голосування", callback_data=f"force_vote_{room_code}")
    builder.button(text="👀 Стіл гравців", callback_data=f"view_table_{room_code}")
    builder.adjust(1)
    return builder.as_markup()
